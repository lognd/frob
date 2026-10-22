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
//! - Each class selector (`.card`) in a rule's selector list is a `style.class_selector` operator named by
//!   the class without its dot, the first children of the rule in source order (not a symbol).
//! - Symrefs nest like the units (`site.css::media.[.card,_.tile]`, see `view::style_segment`).
//! - A declaration `property: value` is the `style.declaration` operator named by the property with the raw
//!   value text in `raw`, `important` set, and the component values (see [`tokens`]) as children; a
//!   `--x: value` definition is `unit(custom-property)` named `--x` with the same `raw` and children. Every
//!   node carries the byte span of the declaration.
//! - A `var(--x)` is a `ref` named `--x`. The scope graph declares every custom property of the file at
//!   status May in one cascade scope and resolves each `var()` there: the cascade decides at runtime which
//!   definition applies (D100), several definitions give a May set, none gives Unknown (no definition edge).
//! - Unity UI Toolkit (D116): `.uss` and `.tss` files are folded by this adapter unchanged (TSS is USS with
//!   `@import`, an ordinary at-rule), so every token and declaration rule applies. A declaration of a USS-only
//!   `-unity-` property carries `style.unity = true`; `--x` and `var(--x, fallback)` behave as in CSS (the
//!   fallback's own `var()` references are references too).
//! - Syntax errors are `hole(parse-error)` (or `hole(missing)`); the file is a partial parse and other files
//!   are unaffected. A tree with no tree at all is the F0 failed-file fold.
//! - `crunk:waive` comments are bound by the directive scanner (gob-directives), not here.
//! - Not modelled: SCSS and Less (variables and mixins are `phase` per D96, a later adapter), `@import`
//!   resolution, selector parsing (a selector is its text).

// frob:ticket 01M43ARY26XF7A4MSRAZ8V73JM
// frob:ticket 01M4CXSBNCE06J78BM0P23V9XV

pub(crate) mod tokens;

use gob_ir::{
    DeclKind, NodeId, NodeSpec, Operator, ScopeGraph, Status, TermError, Universal, style,
};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::model::collapse_ws;
use crate::pipeline::EXTRACTOR_VERSION;
use crate::view::{self, Naming};
use tokens::{Token, tokens};

/// File extensions (lowercase, no dot) the adapter claims.
pub(crate) const EXTENSIONS: &[&str] = &["css", "uss", "tss"];

/// Prefix of the USS-only properties (`-unity-font`, `-unity-text-align`, ...) known to the dialect.
const UNITY_PREFIX: &str = "-unity-";

/// Attribute set to `true` on a declaration of a USS-only (`-unity-`) property.
pub(crate) const ATTR_UNITY: &str = "style.unity";

/// True when `property` is a USS-only property (the `-unity-` vendor prefix, any case).
pub(crate) fn is_unity_property(property: &str) -> bool {
    property
        .get(..UNITY_PREFIX.len())
        .is_some_and(|p| p.eq_ignore_ascii_case(UNITY_PREFIX))
}

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
        gob_caps::lang_fidelity(Lang::Css)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Css)
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

/// True when `path` is a stylesheet this adapter folds (`.css`, or Unity `.uss` and `.tss`, any case).
pub fn is_css_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .and_then(gob_path::exact_text)
        .is_some_and(|e| EXTENSIONS.iter().any(|x| e.eq_ignore_ascii_case(x)))
}

struct Css<'a> {
    cx: Cx<'a>,
    path: &'a str,
    holes: u32,
    /// Byte spans of syntax errors that are valid CSS the grammar rejects (see `forgiven`).
    forgiven: Vec<(usize, usize)>,
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut css = Css {
        cx: Cx::new(input.path, "css", text),
        path: input.path,
        holes: 0,
        forgiven: Vec::new(),
    };
    let kids = css.body(root)?;
    let Css { cx, .. } = css;
    let mut cx = cx;
    let root_id = cx.add(file_root_spec(&cx, input.size as usize), &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = cascade_scopes(&term);
    let v = view::build(&term, input.path, Naming::Style);
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

// frob:ticket 01M48E13W9MYK85YTCWSSRS50S
/// Folds the stylesheet body `text` (parsed to `root`) into the host builder `host` at byte `base`.
///
/// Returns the top-level rule, declaration and hole nodes; every location is a span in the host file.
pub(crate) fn fold_island(
    host: &mut Cx<'_>,
    path: &str,
    text: &str,
    base: usize,
    root: Node<'_>,
) -> R<Vec<NodeId>> {
    let mut css = Css {
        cx: host.nest(text, base),
        path,
        holes: 0,
        forgiven: Vec::new(),
    };
    let kids = css.body(root)?;
    host.unnest(css.cx);
    tracing::debug!(path, base, nodes = kids.len(), "css island folded");
    Ok(kids)
}

impl Css<'_> {
    /// The top-level nodes of the stylesheet `root`, with a hole for an error the walk did not reach.
    fn body(&mut self, root: Node<'_>) -> R<Vec<NodeId>> {
        let mut kids = self.items(root)?;
        if self.holes == 0 && self.has_unforgiven_error(root) {
            // An error the walk did not reach (inside a value or selector): the file is still a partial parse.
            kids.push(self.hole(root)?);
        }
        Ok(kids)
    }
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

/// The `ERROR` and `MISSING` nodes under `n`, not descending into an error node.
// frob:ticket 01M4DPJPDQB79QVGVDVF4PDQKP
fn error_nodes(n: Node<'_>) -> Vec<Node<'_>> {
    let mut out = Vec::new();
    for c in children(n) {
        if c.is_missing() || c.kind() == "ERROR" {
            out.push(c);
        } else if c.has_error() {
            out.extend(error_nodes(c));
        }
    }
    out
}

impl Css<'_> {
    /// True when `n` holds a syntax error that no declaration forgave (`! important`, `!IMPORTANT`, `--x:;`).
    // frob:ticket 01M4DPJPDQB79QVGVDVF4PDQKP
    fn has_unforgiven_error(&self, n: Node<'_>) -> bool {
        n.has_error()
            && (n.kind() == "ERROR"
                || error_nodes(n)
                    .iter()
                    .any(|e| !self.forgiven.contains(&(e.start_byte(), e.end_byte()))))
    }

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
        let mut kids = self.class_selectors(n)?;
        if let Some(b) = block {
            kids.extend(self.items(b)?);
        }
        let spec = NodeSpec::new(
            Operator::unit(style::STYLE_RULE, "impl"),
            self.cx.node_loc(n),
        )
        .named(selector);
        self.cx.add(spec, &kids)
    }

    /// One `style.class_selector` node per `.class` in the rule's own selector list (not its block).
    fn class_selectors(&mut self, rule: Node<'_>) -> R<Vec<NodeId>> {
        let mut found = Vec::new();
        let mut stack: Vec<Node<'_>> = children(rule)
            .into_iter()
            .filter(|c| c.kind() == "selectors")
            .collect();
        while let Some(n) = stack.pop() {
            if n.kind() == "class_selector" {
                found.push(n);
            }
            stack.extend(children(n));
        }
        found.sort_by_key(Node::start_byte);
        let mut out = Vec::new();
        for n in found {
            let name = children(n)
                .into_iter()
                .find(|c| c.kind() == "class_name")
                .map(|c| self.t(c).to_owned());
            let Some(name) = name else { continue };
            tracing::trace!(path = self.path, name, "css class selector");
            let spec = NodeSpec::new(style::class_selector_op(), self.cx.node_loc(n)).named(&name);
            out.push(self.cx.add(spec, &[])?);
        }
        Ok(out)
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
        let custom = property.starts_with("--");
        // frob:ticket 01M4DPJPDQB79QVGVDVF4PDQKP
        let bang_at = value_start
            + (self.cx.text[value_start..n.end_byte()].len()
                - self.cx.text[value_start..n.end_byte()].trim_start().len())
            + raw.len();
        for e in error_nodes(n) {
            if (important && e.start_byte() >= bang_at)
                || (custom && raw.is_empty() && e.is_missing())
            {
                self.forgiven.push((e.start_byte(), e.end_byte()));
            } else if e.parent().is_some_and(|p| p.id() == n.id()) {
                kids.push(self.hole(e)?);
            }
        }
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
                .attr(ATTR_UNITY, is_unity_property(&property))
        };
        self.cx.add(spec, &kids)
    }
}

/// The value text without a trailing `!important`, and whether it was there.
pub(crate) fn split_important(value: &str) -> (&str, bool) {
    let lower = value.to_ascii_lowercase();
    match lower.strip_suffix("important") {
        Some(rest) if rest.trim_end().ends_with('!') => {
            (value[..rest.trim_end().len() - 1].trim_end(), true)
        }
        _ => (value, false),
    }
}
