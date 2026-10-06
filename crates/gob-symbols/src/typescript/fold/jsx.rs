//! JSX and inline style lowering: elements become `markup` terms, `style={{..}}` objects `style`
//! declarations, and `css` tagged templates `region(css)` islands (language-engines.md sections 2
//! and 3, universal-model.md 5.1).
//!
//! - An element is `apply(element)`: head `lit(tag)` (intrinsic) or `ref` (component, also the call edge
//!   of the call graph), then `markup.attribute`, `markup.spread`, text and child terms. A fragment is a
//!   `group` marked `markup.group = fragment`; a conditional or mapped child (`c && <X/>`, `c ? a : b`,
//!   `xs.map(..)`) is a `group` marked `conditional` or `mapped`.
//! - Attribute values and style entries are lowered to the `const_value` forms (`lit`, `ref`,
//!   `apply(op)`); anything not covered by `const_value` is an ordinary expression term, which
//!   evaluates to Unknown.
//! - A `style` attribute whose value is an object literal also carries a `region(css)` child with one
//!   `style.declaration` per entry: Known literals are tokenised, computed values carry one
//!   `lit(unknown)` component value.

// frob:ticket 01M47QKSBYX7YFQHV3VVGKB025

use gob_ir::const_value::{
    OP, OP_ADD, OP_AND, OP_ARRAY, OP_COND, OP_OBJECT, OP_OR, OP_PROP, OP_SPREAD, OP_TEMPLATE,
};
use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, markup, style};
use tree_sitter::Node;

use super::{Fold, R, Root, Site, call_text, children, is_comment, line_of};
use crate::css::tokens::{Token, tokens};
use crate::typescript::style::{css_property, numeric_raw};
use crate::typescript::{ATTR_JSX_ATTRS, ATTR_JSX_KIND, ATTR_JSX_LINE, ATTR_JSX_TAG};

/// Node attribute: what a `group` of the markup lowering stands for (`fragment`, `conditional`, `mapped`).
pub(crate) const ATTR_MARKUP_GROUP: &str = "markup.group";
/// Component value class of a style entry whose value is not statically known.
const UNKNOWN_VALUE: &str = "unknown";
/// Callee names (the final member) of a mapped child.
const MAPPERS: [&str; 2] = ["map", "flatMap"];

/// The named, non-comment children of `n`.
fn named(n: Node<'_>) -> Vec<Node<'_>> {
    children(n)
        .into_iter()
        .filter(|c| c.is_named() && !is_comment(*c))
        .collect()
}

/// The decoded text of the JS string escapes in `s` (unknown escapes keep the escaped character).
fn unescape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match it.next() {
            Some('n') => out.push('\n'),
            Some('t') => out.push('\t'),
            Some('r') => out.push('\r'),
            Some('0') => out.push('\0'),
            Some('\n') | None => {}
            Some(other) => out.push(other),
        }
    }
    out
}

/// The JSX text `raw` with line breaks and indentation collapsed as React does; `None` when nothing is left.
fn jsx_text(raw: &str) -> Option<String> {
    let lines: Vec<&str> = raw
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .collect();
    (!lines.is_empty()).then(|| lines.join(" "))
}

impl Fold<'_> {
    /// The tag, kind (`intrinsic`, `component`, `member`, `fragment`) and head node of a JSX name.
    pub(super) fn jsx_head(
        &mut self,
        name: Option<Node<'_>>,
    ) -> R<(String, &'static str, Option<NodeId>)> {
        let Some(nm) = name else {
            return Ok((String::new(), "fragment", None));
        };
        let tag: String = self.t(nm).split_whitespace().collect();
        let component = match nm.kind() {
            "identifier" => tag
                .chars()
                .next()
                .is_some_and(|c| c.is_uppercase() || c == '_' || c == '$'),
            "member_expression" | "nested_identifier" => true,
            _ => false,
        };
        if component {
            let kind = if nm.kind() == "identifier" {
                "component"
            } else {
                "member"
            };
            let id = self.cx.op(Operator::reference(&tag), nm, &[])?;
            Ok((tag, kind, Some(id)))
        } else {
            let id = self.cx.lit(markup::TAG, &tag, nm)?;
            Ok((tag, "intrinsic", Some(id)))
        }
    }

    /// Records the use of the component `tag` (an `identifier` or dotted name node) as a call of the current unit.
    fn component_site(&mut self, nm: Node<'_>, head: NodeId, line: u32) {
        let target = if nm.kind() == "identifier" {
            self.target_of(Root::Ident(self.t(nm).to_owned()), &[])
        } else {
            self.call_target(nm)
        };
        let caller = self.caller();
        tracing::trace!(path = self.path, component = %target.name, "typescript component use");
        self.sites.push(Site {
            caller,
            value: false,
            name: target.name,
            qualifier: target.qualifier,
            method: target.method,
            receiver: target.receiver,
            node: (!target.dynamic).then_some(head),
            args: 1,
            qual_path: target.path,
            line,
            text: call_text(self.t(nm)),
        });
    }

    /// One attribute or spread of an opening element: its name (`...` for a spread) and node.
    fn jsx_attribute(&mut self, a: Node<'_>, depth: usize) -> R<(String, NodeId)> {
        if a.kind() != "jsx_attribute" {
            // `{...props}`: a spread contributes any attribute (status May).
            let kids = match named(a).first() {
                Some(e) => vec![self.value_expr(*e, depth)?],
                None => Vec::new(),
            };
            let id = self.cx.op(markup::spread_op(), a, &kids)?;
            return Ok(("...".to_owned(), id));
        }
        let kids_src = children(a);
        let name_text = kids_src
            .first()
            .map(|x| self.t(*x).to_owned())
            .unwrap_or_default();
        let mut kids = Vec::new();
        if let Some(v) = kids_src
            .iter()
            .skip(1)
            .find(|c| c.is_named() && !is_comment(**c))
        {
            let value = self.attr_value(*v, depth)?;
            kids.push(value);
            if name_text == "style"
                && let Some(obj) = Self::unwrap_expression(*v).filter(|o| o.kind() == "object")
            {
                kids.push(self.style_region(obj)?);
            }
        }
        let spec = NodeSpec::new(markup::attribute_op(), self.cx.node_loc(a)).named(&name_text);
        Ok((name_text, self.cx.add(spec, &kids)?))
    }

    /// The value of an attribute: a string, a `{expr}` container or an element.
    fn attr_value(&mut self, v: Node<'_>, depth: usize) -> R<NodeId> {
        match v.kind() {
            "jsx_expression" => {
                let Some(inner) = named(v).first().copied() else {
                    return self.cx.lit("null", "null", v);
                };
                if inner.kind() == "identifier" {
                    // A lone identifier is a function or value passed along (a handler, a render prop).
                    self.value_site(inner);
                }
                self.value_expr(inner, depth)
            }
            // JSX attribute strings carry no escapes.
            "string" => {
                let raw = self.t(v);
                let inner = raw.get(1..raw.len().saturating_sub(1)).unwrap_or_default();
                self.cx.lit("str", inner, v)
            }
            _ => self.tr(v, depth + 1),
        }
    }

    /// The expression inside `{..}`, parentheses and `as`/`satisfies`/`!` wrappers removed.
    fn unwrap_expression(v: Node<'_>) -> Option<Node<'_>> {
        let mut cur = v;
        loop {
            cur = match cur.kind() {
                "jsx_expression"
                | "parenthesized_expression"
                | "as_expression"
                | "satisfies_expression"
                | "non_null_expression" => *named(cur).first()?,
                _ => return Some(cur),
            };
        }
    }

    /// `n` as an expression in the `const_value` forms where it has one, else as an ordinary expression term.
    fn value_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        self.with_expr(true, |s| s.const_expr(n, depth))
    }

    /// An `apply(op)` node: head `lit(op, lexeme)` then `args`.
    fn op_node(&mut self, n: Node<'_>, lexeme: &str, args: &[NodeId]) -> R<NodeId> {
        let mut kids = vec![self.cx.lit(OP, lexeme, n)?];
        kids.extend_from_slice(args);
        self.cx.op(Operator::apply(OP), n, &kids)
    }

    pub(super) fn const_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        if depth > super::MAX_DEPTH {
            return self.collapse(&[n]);
        }
        let d = depth + 1;
        match n.kind() {
            "parenthesized_expression"
            | "as_expression"
            | "satisfies_expression"
            | "non_null_expression" => match named(n).first() {
                Some(inner) => self.const_expr(*inner, d),
                None => self.tr(n, d),
            },
            "string" => {
                let raw = self.t(n);
                let inner = raw.get(1..raw.len().saturating_sub(1)).unwrap_or_default();
                self.cx.lit("str", &unescape(inner), n)
            }
            "number" if self.t(n).parse::<i64>().is_ok() => {
                let text = self.t(n).to_owned();
                self.cx.lit("int", &text, n)
            }
            "true" | "false" => {
                let text = self.t(n).to_owned();
                self.cx.lit("bool", &text, n)
            }
            "null" => self.cx.lit("null", "null", n),
            "template_string" => self.const_template(n, d),
            "binary_expression" => {
                let lexeme = n
                    .child_by_field_name("operator")
                    .map(|o| self.t(o).to_owned())
                    .unwrap_or_default();
                let (Some(lhs), Some(rhs)) = (
                    n.child_by_field_name("left"),
                    n.child_by_field_name("right"),
                ) else {
                    return self.tr(n, d);
                };
                match lexeme.as_str() {
                    "+" | "&&" | "||" => {
                        let args = [self.const_expr(lhs, d)?, self.const_expr(rhs, d)?];
                        let op = match lexeme.as_str() {
                            "+" => OP_ADD,
                            "&&" => OP_AND,
                            _ => OP_OR,
                        };
                        self.op_node(n, op, &args)
                    }
                    _ => self.tr(n, d),
                }
            }
            "ternary_expression" => {
                let parts: Vec<Node<'_>> = ["condition", "consequence", "alternative"]
                    .iter()
                    .filter_map(|f| n.child_by_field_name(f))
                    .collect();
                if parts.len() != 3 {
                    return self.tr(n, d);
                }
                let mut args = Vec::new();
                for p in parts {
                    args.push(self.const_expr(p, d)?);
                }
                self.op_node(n, OP_COND, &args)
            }
            "spread_element" => match named(n).first() {
                Some(inner) => {
                    let arg = self.const_expr(*inner, d)?;
                    self.op_node(n, OP_SPREAD, &[arg])
                }
                None => self.tr(n, d),
            },
            // The arguments of a call are lowered to the `const_value` forms (the callee stays a reference).
            "call_expression" => {
                self.const_args = true;
                let lowered = self.tr(n, d);
                self.const_args = false;
                lowered
            }
            "array" => {
                let mut args = Vec::new();
                for e in named(n) {
                    args.push(self.const_expr(e, d)?);
                }
                self.op_node(n, OP_ARRAY, &args)
            }
            "object" => {
                let mut args = Vec::new();
                for e in named(n) {
                    args.push(self.object_entry(e, d)?);
                }
                self.op_node(n, OP_OBJECT, &args)
            }
            _ => self.tr(n, d),
        }
    }

    /// A template literal as `apply(op template)`: its static quasis and substitutions in order.
    fn const_template(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut args = Vec::new();
        for c in children(n) {
            match c.kind() {
                "string_fragment" => args.push(self.cx.lit("str", self.t(c), c)?),
                "escape_sequence" => {
                    args.push(self.cx.lit("str", &unescape(self.t(c)), c)?);
                }
                "template_substitution" => {
                    if let Some(e) = named(c).first() {
                        args.push(self.const_expr(*e, depth)?);
                    }
                }
                _ => {}
            }
        }
        self.op_node(n, OP_TEMPLATE, &args)
    }

    /// One entry of an object literal: `apply(op prop)` over the key and value, or an expression term.
    fn object_entry(&mut self, e: Node<'_>, depth: usize) -> R<NodeId> {
        let key_value = match e.kind() {
            "pair" => e
                .child_by_field_name("key")
                .zip(e.child_by_field_name("value")),
            _ => None,
        };
        if let Some((k, v)) = key_value {
            let key = match k.kind() {
                "computed_property_name" => match named(k).first() {
                    Some(inner) => self.const_expr(*inner, depth + 1)?,
                    None => self.tr(k, depth + 1)?,
                },
                "string" => {
                    let raw = self.t(k);
                    let inner = raw.get(1..raw.len().saturating_sub(1)).unwrap_or_default();
                    self.cx.lit("str", &unescape(inner), k)?
                }
                _ => self.cx.lit("str", self.t(k), k)?,
            };
            let val = self.const_expr(v, depth + 1)?;
            return self.op_node(e, OP_PROP, &[key, val]);
        }
        if e.kind() == "spread_element" {
            return self.const_expr(e, depth + 1);
        }
        if e.kind() == "shorthand_property_identifier" {
            let name = self.t(e).to_owned();
            let key = self.cx.lit("str", &name, e)?;
            let val = self.cx.op(Operator::reference(&name), e, &[])?;
            return self.op_node(e, OP_PROP, &[key, val]);
        }
        self.tr(e, depth + 1)
    }

    /// The `region(css)` island of an inline style object: one `style.declaration` per statically named entry.
    fn style_region(&mut self, obj: Node<'_>) -> R<NodeId> {
        let mut decls = Vec::new();
        for e in named(obj) {
            let (key, value) = match e.kind() {
                "pair" => {
                    let k = e.child_by_field_name("key");
                    (
                        k.filter(|k| k.kind() != "computed_property_name"),
                        e.child_by_field_name("value"),
                    )
                }
                "shorthand_property_identifier" => (Some(e), None),
                _ => (None, None),
            };
            let Some(k) = key else {
                tracing::debug!(
                    path = self.path,
                    "inline style entry without a static name skipped"
                );
                continue;
            };
            let name = match k.kind() {
                "string" => {
                    let raw = self.t(k);
                    raw.get(1..raw.len().saturating_sub(1))
                        .unwrap_or_default()
                        .to_owned()
                }
                _ => self.t(k).to_owned(),
            };
            let property = css_property(&name);
            decls.push(self.style_declaration(e, &property, value)?);
        }
        let spec = NodeSpec::new(Operator::region("css"), self.cx.node_loc(obj))
            .attr(ATTR_MARKUP_GROUP, "inline-style");
        self.cx.add(spec, &decls)
    }

    /// One `style.declaration` named `property`; Known when `value` is a string or integer literal, else Unknown.
    fn style_declaration(
        &mut self,
        e: Node<'_>,
        property: &str,
        value: Option<Node<'_>>,
    ) -> R<NodeId> {
        let literal = value
            .and_then(|v| Self::unwrap_expression(v))
            .and_then(|v| match v.kind() {
                "string" => {
                    let raw = self.t(v);
                    Some(unescape(raw.get(1..raw.len().saturating_sub(1))?))
                }
                "number" => Some(numeric_raw(property, self.t(v))),
                _ => None,
            });
        let (raw, comps) = if let Some(raw) = literal {
            let important = raw.trim_end().ends_with("!important");
            let body = raw
                .trim_end()
                .trim_end_matches("!important")
                .trim()
                .to_owned();
            (body.clone(), (important, tokens(&body)))
        } else {
            let text = value.map_or_else(|| self.t(e), |v| self.t(v)).to_owned();
            tracing::trace!(path = self.path, property, "inline style value is unknown");
            (
                String::new(),
                (false, vec![Token::Lit(UNKNOWN_VALUE, text)]),
            )
        };
        let mut kids = Vec::new();
        for t in comps.1 {
            kids.push(match t {
                Token::Lit(kind, text) => self.cx.lit(kind, &text, e)?,
                Token::Var(name) => self.cx.op(Operator::reference(&name), e, &[])?,
            });
        }
        let spec = NodeSpec::new(style::declaration_op(), self.cx.node_loc(e))
            .named(property)
            .attr(style::RAW, raw.as_str())
            .attr(style::IMPORTANT, comps.0);
        self.cx.add(spec, &kids)
    }

    /// A `css` tagged template: a `region(css)` over the template text and substitutions.
    pub(super) fn css_template(&mut self, tpl: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        for c in children(tpl) {
            match c.kind() {
                "string_fragment" | "escape_sequence" => {
                    kids.push(self.cx.lit("text", self.t(c), c)?);
                }
                "template_substitution" => {
                    if let Some(e) = named(c).first() {
                        kids.push(self.value_expr(*e, depth)?);
                    }
                }
                _ => {}
            }
        }
        let spec = NodeSpec::new(Operator::region("css"), self.cx.node_loc(tpl))
            .attr(ATTR_MARKUP_GROUP, "css-in-js");
        self.cx.add(spec, &kids)
    }

    /// An element, a fragment or a `group`; see the module docs.
    pub(super) fn jsx(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let (open, rest): (Option<Node<'_>>, Vec<Node<'_>>) = match n.kind() {
            "jsx_element" => (
                n.child_by_field_name("open_tag"),
                named(n)
                    .into_iter()
                    .filter(|c| {
                        c.kind() != "jsx_opening_element" && c.kind() != "jsx_closing_element"
                    })
                    .collect(),
            ),
            "jsx_self_closing_element" => (Some(n), Vec::new()),
            _ => (None, named(n)),
        };
        let name = open.and_then(|o| o.child_by_field_name("name"));
        let (tag, kind, head) = self.jsx_head(name)?;
        if matches!(kind, "component" | "member")
            && let (Some(nm), Some(head)) = (name, head)
        {
            self.component_site(nm, head, line_of(n));
        }
        let mut kids: Vec<NodeId> = head.into_iter().collect();
        let mut attr_names = Vec::new();
        if let Some(o) = open {
            let attrs: Vec<Node<'_>> = children(o)
                .into_iter()
                .filter(|c| c.is_named() && Some(c.id()) != name.map(|x| x.id()))
                .filter(|c| !matches!(c.kind(), "type_arguments") && !is_comment(*c))
                .collect();
            for a in attrs {
                let (nm, id) = self.jsx_attribute(a, depth)?;
                attr_names.push(nm);
                kids.push(id);
            }
        }
        for c in rest {
            if let Some(id) = self.jsx_child(c, depth)? {
                kids.push(id);
            }
        }
        let op = if kind == "fragment" {
            Operator::group(GroupOrder::Sequence)
        } else {
            markup::element_op()
        };
        let mut spec = NodeSpec::new(op, self.cx.node_loc(n))
            .attr(ATTR_JSX_TAG, tag.as_str())
            .attr(ATTR_JSX_KIND, kind)
            .attr(ATTR_JSX_ATTRS, attr_names.join(",").as_str())
            .attr(ATTR_JSX_LINE, i64::from(line_of(n)));
        if kind == "fragment" {
            spec = spec.attr(ATTR_MARKUP_GROUP, "fragment");
        }
        self.cx.add(spec, &kids)
    }

    /// One child of an element: text, an element, an expression container or nothing (blank text).
    fn jsx_child(&mut self, c: Node<'_>, depth: usize) -> R<Option<NodeId>> {
        match c.kind() {
            "jsx_text" => match jsx_text(self.t(c)) {
                Some(text) => Ok(Some(self.cx.lit(markup::TEXT, &text, c)?)),
                None => Ok(None),
            },
            "jsx_expression" => self.jsx_expression(c, depth),
            _ => Ok(Some(self.tr(c, depth + 1)?)),
        }
    }

    /// `{expr}`: a conditional or mapped child is a `group`; a lone identifier is a value passed along.
    fn jsx_expression(&mut self, n: Node<'_>, depth: usize) -> R<Option<NodeId>> {
        let Some(only) = named(n).first().copied() else {
            return Ok(None);
        };
        if only.kind() == "identifier" {
            self.value_site(only);
        }
        let inner = Self::unwrap_expression(only).unwrap_or(only);
        let role = match inner.kind() {
            "ternary_expression" => Some("conditional"),
            "binary_expression"
                if inner
                    .child_by_field_name("operator")
                    .is_some_and(|o| matches!(self.t(o), "&&" | "||" | "??")) =>
            {
                Some("conditional")
            }
            "call_expression"
                if inner
                    .child_by_field_name("function")
                    .filter(|f| f.kind() == "member_expression")
                    .and_then(|f| f.child_by_field_name("property"))
                    .is_some_and(|p| MAPPERS.contains(&self.t(p))) =>
            {
                Some("mapped")
            }
            _ => None,
        };
        let kids = vec![self.with_expr(true, |s| s.tr(inner, depth + 1))?];
        let (op, role) = match role {
            Some(r) => (Operator::group(GroupOrder::Sequence), r),
            None => {
                return Ok(Some(self.cx.op(
                    Operator::adapter(super::LANG, "jsx_expression", gob_ir::Sort::Exp),
                    n,
                    &kids,
                )?));
            }
        };
        let spec = NodeSpec::new(op, self.cx.node_loc(n)).attr(ATTR_MARKUP_GROUP, role);
        Ok(Some(self.cx.add(spec, &kids)?))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-symbols/src/typescript/fold/jsx.rs::jsx_text
    #[test]
    fn jsx_text_collapses_lines() {
        assert_eq!(jsx_text("\n   a\n   b  \n"), Some("a b".to_owned()));
        assert_eq!(jsx_text("  \n  "), None);
        assert_eq!(unescape(r"a\nb\'"), "a\nb'");
    }
}
