//! The `markup` capability: element trees, and the derived `class_tokens` query
//! (language-engines.md section 2, universal-model.md 5.1, queries Q48 and Q51).
//!
//! # Lowered forms
//!
//! - An element is `apply(element)`; child 0 is the head. An intrinsic tag
//!   (`div`) is `lit(tag, "div")`; a component tag (`Button`, `ui.Card`) is a
//!   `ref` with the spelled name, so a component use is an ordinary reference
//!   edge; any other head makes the tag unknown.
//! - An attribute is the `Sigma_L` operator [`attribute_op`] named after the
//!   attribute, whose optional child 0 is the value expression; a missing value
//!   (`<input disabled>`) means `true`.
//! - A spread (`{...props}`) is [`spread_op`] over the spread expression; it may
//!   contribute any attribute, so it answers at status [`Status::May`].
//! - Text is `lit(text, content)`; every other child is a child element or an
//!   expression container.

use tracing::trace;

use crate::const_value::{
    ConstEval, ConstValue, OP_AND, OP_ARRAY, OP_COND, OP_OBJECT, OP_PROP, Value, op_form,
};
use crate::operator::{Operator, Sort, Universal};
use crate::query::Model;
use crate::scope::Status;
use crate::term::NodeId;

/// Language tag of the markup `Sigma_L` operators.
pub const LANG: &str = "markup";
/// Kind of the `apply` that is an element.
pub const ELEMENT: &str = "element";
/// Kind of the `lit` head of an intrinsic tag.
pub const TAG: &str = "tag";
/// Kind of a text `lit`.
pub const TEXT: &str = "text";
/// Callee names whose arguments are class token sources (matched by name, May).
pub const CLASS_FNS: [&str; 4] = ["clsx", "cn", "classnames", "classNames"];
/// Attribute names that carry class tokens.
pub const CLASS_ATTRS: [&str; 2] = ["class", "className"];

/// The operator of one named attribute.
pub fn attribute_op() -> Operator {
    Operator::adapter(LANG, "attribute", Sort::Exp)
}

/// The operator of one attribute spread.
pub fn spread_op() -> Operator {
    Operator::adapter(LANG, "spread", Sort::Exp)
}

/// The operator of one element.
pub fn element_op() -> Operator {
    Operator::apply(ELEMENT)
}

/// What the head of an element is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TagKind {
    /// A built-in tag such as `div`.
    Intrinsic,
    /// A reference to a component, resolved through the scope graph.
    Component,
    /// The head is not a plain tag or name (a dynamic tag).
    Unknown,
}

/// One attribute or spread of an element.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Attribute {
    /// The attribute node.
    pub node: NodeId,
    /// The attribute name; `None` for a spread.
    pub name: Option<String>,
    /// The value expression, if written.
    pub value: Option<NodeId>,
    /// `Must` for a named attribute, `May` for a spread.
    pub status: Status,
}

impl Attribute {
    /// True for a spread.
    pub fn is_spread(&self) -> bool {
        self.name.is_none()
    }
}

/// A child of an element.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Child {
    /// A nested element.
    Element(NodeId),
    /// Literal text.
    Text(String),
    /// Any other child expression.
    Expr(NodeId),
}

/// One element with its tag, attributes and children.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Element {
    /// The element node.
    pub node: NodeId,
    /// The tag or component name; `None` when [`TagKind::Unknown`].
    pub tag: Option<String>,
    /// What the head is.
    pub kind: TagKind,
    /// Attributes and spreads in source order.
    pub attributes: Vec<Attribute>,
    /// Children in source order.
    pub children: Vec<Child>,
}

impl Element {
    /// The first attribute called `name` (a spread is never matched by name).
    pub fn attribute(&self, name: &str) -> Option<&Attribute> {
        self.attributes
            .iter()
            .find(|a| a.name.as_deref() == Some(name))
    }

    /// True when a spread may add attributes not listed here.
    pub fn has_spread(&self) -> bool {
        self.attributes.iter().any(Attribute::is_spread)
    }
}

/// The element at `node`, or `None` when `node` is not an `apply(element)`.
pub fn element(model: &Model, node: NodeId) -> Option<Element> {
    let term = model.term();
    let n = term.node(node);
    if !matches!(&n.op, Operator::Universal(Universal::Apply { kind }) if kind == ELEMENT) {
        return None;
    }
    let (&head, rest) = n.children.split_first()?;
    let (tag, kind) = match &term.node(head).op {
        Operator::Universal(Universal::Lit { kind, lexeme }) if kind == TAG => {
            (Some(lexeme.clone()), TagKind::Intrinsic)
        }
        Operator::Universal(Universal::Ref { name }) => (Some(name.clone()), TagKind::Component),
        _ => (None, TagKind::Unknown),
    };
    let mut attributes = Vec::new();
    let mut children = Vec::new();
    for &c in rest {
        let cn = term.node(c);
        match &cn.op {
            Operator::Adapter(a) if a.lang == LANG && a.name == "attribute" => {
                attributes.push(Attribute {
                    node: c,
                    name: cn.name().map(str::to_owned),
                    value: cn.children.first().copied(),
                    status: Status::Must,
                });
            }
            Operator::Adapter(a) if a.lang == LANG && a.name == "spread" => {
                attributes.push(Attribute {
                    node: c,
                    name: None,
                    value: cn.children.first().copied(),
                    status: Status::May,
                });
            }
            Operator::Universal(Universal::Lit { kind, lexeme }) if kind == TEXT => {
                children.push(Child::Text(lexeme.clone()));
            }
            Operator::Universal(Universal::Apply { kind }) if kind == ELEMENT => {
                children.push(Child::Element(c));
            }
            _ => children.push(Child::Expr(c)),
        }
    }
    trace!(%node, ?tag, attrs = attributes.len(), "markup element read");
    Some(Element {
        node,
        tag,
        kind,
        attributes,
        children,
    })
}

/// Every element of the term in node order.
pub fn elements(model: &Model) -> Vec<Element> {
    model
        .term()
        .ids()
        .filter_map(|n| element(model, n))
        .collect()
}

/// The `const_value` of an attribute: its value expression, `true` when none, `Unknown` for a spread.
pub fn attribute_value(model: &Model, attr: &Attribute) -> ConstValue {
    match (attr.is_spread(), attr.value) {
        (true, _) => ConstValue::Unknown,
        (false, None) => ConstValue::Known(Value::Bool(true)),
        (false, Some(v)) => crate::const_value::const_value(model, v),
    }
}

/// One class token and how sure it is.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClassToken {
    /// The token text.
    pub token: String,
    /// `Must` when certainly applied, `May` when conditional or reached through a name-matched call.
    pub status: Status,
}

/// The class tokens of one attribute or element.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ClassTokens {
    /// Known tokens, first occurrence order, the strongest status of duplicates.
    pub tokens: Vec<ClassToken>,
    /// Some part is dynamic: more tokens may exist than are listed.
    pub dynamic: bool,
}

impl ClassTokens {
    /// The tokens that are certainly applied.
    pub fn must(&self) -> impl Iterator<Item = &str> {
        self.tokens
            .iter()
            .filter(|t| t.status == Status::Must)
            .map(|t| t.token.as_str())
    }

    /// True when the token list is the complete answer (no dynamic remainder).
    pub fn is_complete(&self) -> bool {
        !self.dynamic
    }

    fn add(&mut self, token: &str, status: Status) {
        match self.tokens.iter_mut().find(|t| t.token == token) {
            Some(t) => t.status = t.status.max(status),
            None => self.tokens.push(ClassToken {
                token: token.to_owned(),
                status,
            }),
        }
    }
}

/// The class tokens of one attribute value; empty and complete for attributes not named `class`/`className`.
///
/// Known tokens come from string literals, template literals and constants, and
/// from the arguments of `clsx`, `cn`, `classnames` and `classNames` (matched by
/// name, so those tokens are `May`); anything dynamic sets `dynamic`.
pub fn class_tokens(model: &Model, attr: &Attribute) -> ClassTokens {
    let mut out = ClassTokens::default();
    if attr.is_spread() {
        out.dynamic = true;
        return out;
    }
    if !attr
        .name
        .as_deref()
        .is_some_and(|n| CLASS_ATTRS.contains(&n))
    {
        return out;
    }
    if let Some(v) = attr.value {
        let mut ev = ConstEval::new(model, crate::const_value::Budget::default());
        walk(model, &mut ev, v, Status::Must, false, &mut out);
    }
    out
}

/// The class tokens of an element: its `class`/`className` attributes; a spread makes it dynamic.
pub fn element_class_tokens(model: &Model, el: &Element) -> ClassTokens {
    let mut out = ClassTokens::default();
    for a in &el.attributes {
        let t = class_tokens(model, a);
        out.dynamic |= t.dynamic;
        for tok in &t.tokens {
            out.add(&tok.token, tok.status);
        }
    }
    out
}

fn walk(
    model: &Model,
    ev: &mut ConstEval<'_>,
    node: NodeId,
    status: Status,
    in_call: bool,
    out: &mut ClassTokens,
) {
    let term = model.term();
    if let Operator::Universal(Universal::Apply { kind }) = &term.node(node).op
        && kind == "call"
        && let Some(&callee) = term.node(node).children.first()
        && matches!(&term.node(callee).op,
            Operator::Universal(Universal::Ref { name }) if CLASS_FNS.contains(&name.as_str()))
    {
        for &arg in &term.node(node).children[1..] {
            walk(model, ev, arg, Status::May, true, out);
        }
        return;
    }
    if let Some((op, args)) = op_form(model, node) {
        match (op.as_str(), in_call) {
            (OP_ARRAY, true) => {
                for a in args {
                    walk(model, ev, a, status, true, out);
                }
                return;
            }
            (OP_OBJECT, true) => {
                for a in args {
                    object_entry(model, ev, a, out);
                }
                return;
            }
            (OP_AND, true) => {
                if let Some(&rhs) = args.last() {
                    walk(model, ev, rhs, Status::May, true, out);
                }
                return;
            }
            (OP_COND, _) if args.len() == 3 => {
                walk(model, ev, args[1], Status::May, in_call, out);
                walk(model, ev, args[2], Status::May, in_call, out);
                return;
            }
            _ => {}
        }
    }
    value_tokens(&ev.eval(node), status, in_call, out);
}

fn object_entry(model: &Model, ev: &mut ConstEval<'_>, entry: NodeId, out: &mut ClassTokens) {
    let key = match op_form(model, entry) {
        Some((op, kv)) if op == OP_PROP && kv.len() == 2 => ev.eval(kv[0]),
        _ => ConstValue::Unknown,
    };
    value_tokens(&key, Status::May, true, out);
}

fn value_tokens(value: &ConstValue, status: Status, in_call: bool, out: &mut ClassTokens) {
    match value {
        ConstValue::Known(Value::Str(s)) => split(s, status, out),
        ConstValue::Known(Value::Bool(_) | Value::Null) if in_call => {}
        ConstValue::OneOf(vs) => {
            for v in vs {
                match v {
                    Value::Str(s) => split(s, Status::May, out),
                    Value::Bool(_) | Value::Null if in_call => {}
                    _ => out.dynamic = true,
                }
            }
        }
        ConstValue::Fragments(frags) => {
            use crate::const_value::Fragment;
            for (i, f) in frags.iter().enumerate() {
                let Fragment::Known(s) = f else {
                    out.dynamic = true;
                    continue;
                };
                let glued_before = i > 0 && !s.starts_with(char::is_whitespace);
                let glued_after = i + 1 < frags.len() && !s.ends_with(char::is_whitespace);
                let words: Vec<&str> = s.split_whitespace().collect();
                for (j, w) in words.iter().enumerate() {
                    let partial = (j == 0 && glued_before) || (j + 1 == words.len() && glued_after);
                    if partial {
                        out.dynamic = true;
                    } else {
                        out.add(w, status);
                    }
                }
            }
        }
        _ => out.dynamic = true,
    }
}

fn split(s: &str, status: Status, out: &mut ClassTokens) {
    for w in s.split_whitespace() {
        out.add(w, status);
    }
}
