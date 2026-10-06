//! The CSS adapter (fidelity F2): tree-sitter tree to the `gob_ir::style` forms plus a custom-property
//! scope graph (D96, language-engines.md sections 2 and 3, universal-model.md 4.4 and 5.1, D100).
//!
//! # Mapping (rho)
//!
//! - The stylesheet is a `unit(file, impl)`. A rule set is `unit(style-rule)` named by its selector text
//!   (whitespace collapsed); an at-rule (`@media`, `@supports`, `@layer`, `@keyframes`, `@font-face`,
//!   `@import`, ...) is `unit(at-rule)` named without the `@`, with its prelude text in attribute `prelude`;
//!   a keyframe block is a `unit(style-rule)` named by its selector (`from`, `50%`). Children are the nested
//!   rules, at-rules and declarations, so the selector and at-rule chain of a declaration is its ancestor
//!   chain ([`gob_ir::style::declarations`] reports the nearest owner).
//! - A declaration `property: value` is the `style.declaration` operator named by the property with the raw
//!   value text in `raw`, `important` set, and the component values (see [`tokens`]) as children; a
//!   `--x: value` definition is `unit(custom-property)` named `--x` with the same `raw` and children. Every
//!   node carries the byte span of the declaration.
//! - A `var(--x)` is a `ref` named `--x`. The scope graph declares every custom property of the file at
//!   status May in one cascade scope and resolves each `var()` there: the cascade decides at runtime which
//!   definition applies (D100), several definitions give a May set, none gives Unknown (no definition edge).
//! - Syntax errors are `hole(parse-error)` (or `hole(missing)`); the file is a partial parse and other files
//!   are unaffected. A tree with no tree at all is the F0 failed-file fold.
//! - `crunk:waive` comments are bound by the directive scanner (gob-directives), not here.
//! - Not modelled: SCSS and Less (variables and mixins are `phase` per D96, a later adapter), `@import`
//!   resolution, selector parsing (a selector is its text).

// frob:ticket 01M43ARY26XF7A4MSRAZ8V73JM

pub(crate) mod tokens;

use gob_ir::{
    DeclKind, NodeId, NodeSpec, Operator, ScopeGraph, Status, TermError, Universal, style,
};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
    Precision,
};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::model::collapse_ws;
use crate::pipeline::EXTRACTOR_VERSION;
use crate::view::{self, Naming};
use tokens::{Token, tokens};

/// File extensions (lowercase, no dot) the adapter claims.
pub(crate) const EXTENSIONS: &[&str] = &["css"];

type R<T> = Result<T, TermError>;

/// The CSS adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct CssAdapter;

impl Adapter for CssAdapter {
    fn language(&self) -> &'static str {
        "css"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Css)
        )
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F2
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
            .with(Capability::ResolveRef, Precision::ByNameInCrate)
            .with(Capability::Visibility, Precision::NotApplicable)
            .with(Capability::Effects, Precision::NotApplicable)
            .with(Capability::TestItems, Precision::NotApplicable)
            .with(Capability::Expand, Precision::NotApplicable)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Css, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "css", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "css",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a CSS file (`.css`, any case).
pub fn is_css_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| EXTENSIONS.iter().any(|x| e.eq_ignore_ascii_case(x)))
}

struct Css<'a> {
    cx: Cx<'a>,
    path: &'a str,
    holes: u32,
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut css = Css {
        cx: Cx::new(input.path, "css", text),
        path: input.path,
        holes: 0,
    };
    let mut kids = css.items(root)?;
    if root.has_error() && css.holes == 0 {
        // An error the walk did not reach (inside a value or selector): the file is still a partial parse.
        kids.push(css.hole(root)?);
    }
    let Css { cx, .. } = css;
    let mut cx = cx;
    let root_id = cx.add(file_root_spec(&cx, input.size as usize), &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = cascade_scopes(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "css");
    file.fidelity = Fidelity::F2;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        status = ?file.parse_status,
        "css file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// The scope graph of a stylesheet: one cascade scope holding every custom property at May, every `var()` in it.
fn cascade_scopes(term: &gob_ir::Term) -> ScopeGraph {
    let mut g = ScopeGraph::new();
    let scope = g.add_scope(Some(term.root()));
    let (mut defs, mut uses) = (0usize, 0usize);
    for id in term.ids() {
        match term.operator(id) {
            Operator::Universal(Universal::Unit { kind, .. }) if kind == style::CUSTOM_PROPERTY => {
                if let Some(name) = term.node(id).name() {
                    g.declare(scope, name, None, DeclKind::Other, Status::May, Some(id));
                    defs += 1;
                }
            }
            Operator::Universal(Universal::Ref { name }) => {
                g.reference(scope, name, Some(id));
                uses += 1;
            }
            _ => {}
        }
    }
    tracing::debug!(
        definitions = defs,
        references = uses,
        "css cascade scope built"
    );
    g
}

/// True for the tree-sitter kinds of at-rules.
fn is_at_rule(kind: &str) -> bool {
    kind == "at_rule" || kind.ends_with("_statement")
}

impl Css<'_> {
    fn hole(&mut self, n: Node<'_>) -> R<NodeId> {
        let kind = if n.is_missing() {
            view::HOLE_MISSING
        } else {
            view::HOLE_PARSE_ERROR
        };
        self.holes += 1;
        tracing::debug!(path = self.path, kind, at = n.start_byte(), "css hole");
        self.cx.op(Operator::hole(kind), n, &[])
    }

    /// The nodes for the rules, at-rules and declarations among the children of a stylesheet or block.
    fn items(&mut self, parent: Node<'_>) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(parent) {
            let kind = c.kind();
            if c.is_missing() || kind == "ERROR" {
                out.push(self.hole(c)?);
            } else if kind == "rule_set" {
                out.push(self.rule_set(c)?);
            } else if kind == "declaration" {
                out.push(self.declaration(c)?);
            } else if is_at_rule(kind) {
                if let Some(id) = self.at_rule(c)? {
                    out.push(id);
                }
            } else if c.is_named() && kind != "comment" {
                tracing::trace!(path = self.path, kind, "css node not modelled");
            }
        }
        Ok(out)
    }

    fn t(&self, n: Node<'_>) -> &str {
        text_of(self.cx.text, n)
    }

    /// `unit(style-rule)` over the declarations and nested rules of `block`, named `selector`.
    fn rule_unit(&mut self, n: Node<'_>, selector: &str, block: Option<Node<'_>>) -> R<NodeId> {
        let kids = match block {
            Some(b) => self.items(b)?,
            None => Vec::new(),
        };
        let spec = NodeSpec::new(
            Operator::unit(style::STYLE_RULE, "impl"),
            self.cx.node_loc(n),
        )
        .named(selector);
        self.cx.add(spec, &kids)
    }

    fn rule_set(&mut self, n: Node<'_>) -> R<NodeId> {
        let cs = children(n);
        let selector = cs
            .iter()
            .find(|c| c.kind() == "selectors")
            .map(|s| collapse_ws(self.t(*s)))
            .unwrap_or_default();
        let block = cs.into_iter().find(|c| c.kind() == "block");
        self.rule_unit(n, &selector, block)
    }

    /// The at-rule `n` as `unit(at-rule)`; `None` when its text does not start with `@name`.
    fn at_rule(&mut self, n: Node<'_>) -> R<Option<NodeId>> {
        let text = self.t(n);
        let Some(after) = text.strip_prefix('@') else {
            tracing::debug!(
                path = self.path,
                kind = n.kind(),
                "at-rule without @ skipped"
            );
            return Ok(None);
        };
        let name_len = after
            .find(|c: char| !(c.is_ascii_alphanumeric() || c == '-' || c == '_'))
            .unwrap_or(after.len());
        let name = after[..name_len].to_owned();
        let cs = children(n);
        let body = cs
            .iter()
            .find(|c| matches!(c.kind(), "block" | "keyframe_block_list"))
            .copied();
        let prelude_end = body.map_or(text.len(), |b| b.start_byte() - n.start_byte());
        let prelude = collapse_ws(
            text[1 + name_len..prelude_end]
                .trim()
                .trim_end_matches(';')
                .trim(),
        );
        let kids = match body {
            Some(b) if b.kind() == "keyframe_block_list" => self.keyframes(b)?,
            Some(b) => self.items(b)?,
            None => Vec::new(),
        };
        let spec = NodeSpec::new(Operator::unit(style::AT_RULE, "impl"), self.cx.node_loc(n))
            .named(&name)
            .attr(style::PRELUDE, prelude.as_str());
        self.cx.add(spec, &kids).map(Some)
    }

    fn keyframes(&mut self, list: Node<'_>) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(list) {
            if c.is_missing() || c.kind() == "ERROR" {
                out.push(self.hole(c)?);
            } else if c.kind() == "keyframe_block" {
                let cs = children(c);
                let block = cs.iter().find(|k| k.kind() == "block").copied();
                let end = block.map_or(c.end_byte(), |b| b.start_byte());
                let sel = collapse_ws(&self.cx.text[c.start_byte()..end]);
                out.push(self.rule_unit(c, &sel, block)?);
            }
        }
        Ok(out)
    }

    /// A declaration or a custom-property definition.
    fn declaration(&mut self, n: Node<'_>) -> R<NodeId> {
        let cs = children(n);
        let property = cs
            .iter()
            .find(|c| c.kind() == "property_name")
            .map(|p| self.t(*p).to_owned())
            .unwrap_or_default();
        let value_start = cs
            .iter()
            .find(|c| c.kind() == ":")
            .map_or(n.end_byte(), Node::end_byte);
        let value = self.cx.text[value_start..n.end_byte()]
            .trim()
            .trim_end_matches(';')
            .trim_end();
        let (raw, important) = split_important(value);
        let mut kids = Vec::new();
        for t in tokens(raw) {
            kids.push(match t {
                Token::Lit(kind, text) => self.cx.lit(kind, &text, n)?,
                Token::Var(name) => self.cx.op(Operator::reference(&name), n, &[])?,
            });
        }
        for c in cs {
            if c.is_missing() || c.kind() == "ERROR" {
                kids.push(self.hole(c)?);
            }
        }
        let custom = property.starts_with("--");
        tracing::trace!(path = self.path, property, custom, "css declaration");
        let loc = self.cx.node_loc(n);
        let spec = if custom {
            NodeSpec::new(Operator::unit(style::CUSTOM_PROPERTY, "impl"), loc)
                .named(&property)
                .attr(style::RAW, raw)
        } else {
            NodeSpec::new(style::declaration_op(), loc)
                .named(&property)
                .attr(style::RAW, raw)
                .attr(style::IMPORTANT, important)
        };
        self.cx.add(spec, &kids)
    }
}

/// The value text without a trailing `!important`, and whether it was there.
fn split_important(value: &str) -> (&str, bool) {
    let lower = value.to_ascii_lowercase();
    match lower.strip_suffix("important") {
        Some(rest) if rest.trim_end().ends_with('!') => {
            (value[..rest.trim_end().len() - 1].trim_end(), true)
        }
        _ => (value, false),
    }
}
