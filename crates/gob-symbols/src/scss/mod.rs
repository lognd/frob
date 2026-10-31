//! The SCSS adapter (fidelity F2): tree-sitter tree to the `gob_ir::style` forms plus `phase` terms for the
//! compile-time features, and a lexical scope graph (D96, language-engines.md sections 2 and 3).
//!
//! # Mapping (rho)
//!
//! - Rule sets, at-rules, keyframes, declarations and custom properties fold exactly as in the CSS adapter
//!   (`unit(style-rule)`, `unit(at-rule)`, `style.declaration`, `unit(custom-property)`); nested rules nest
//!   (`&:hover` is a `style-rule` child of its parent rule). Control directives (`@if`, `@else`, `@each`,
//!   `@for`, `@while`) are at-rules with the condition as `prelude`; `@use`, `@forward`, `@import`, `@extend`
//!   and `@return` are ordinary at-rules.
//! - `$x: value;` is `unit(variable)` named `$x` (`raw` holds the value, `scss.default` and `scss.global`
//!   record the flags); `@mixin m($a, $b: 1)` is `unit(mixin)` named `m` and `@function f($a)` is
//!   `unit(function)` named `f`, both with attribute `scss.params` (`$a,$b`) and the body as children.
//! - A use of `$x` in a value is `phase(variable)`: its first child is `ref $x`, its optional second child
//!   is the expansion, the group of component values `$x` was bound to when the file is read in order
//!   (Sass evaluates in source order, so the walk keeps a stack of variable frames). A parameter, a loop
//!   variable, a variable assigned in a branch, or a variable of another module has no known value, so its
//!   phase has one child and the model reports it as unexpanded.
//! - `@include m(args) { content }` is `phase(mixin)`: the first child is a group holding `ref @m`, the
//!   argument values and the content block, the second child is the expansion, a group (attribute
//!   `scss.params`) holding the mixin body folded again at the include site with the parameters bound to the
//!   arguments, so the declarations a mixin emits appear under the including rule. A mixin that is not
//!   defined earlier in the file (another module, `meta.load-css`) or that would recurse is left
//!   unexpanded.
//! - The scope graph is symbolic, not lexical text matching (D96): every rule, at-rule, mixin and function
//!   opens a scope; `$x` definitions and mixin and function names are declarations (`$x`, `@m`, `f()`), each
//!   `ref` resolves up the lexical chain; mixin and function parameters are binders of their scope. A
//!   `!global` variable is declared in the file scope, `!default` makes the declaration May.
//! - Syntax errors are `hole(parse-error)` (or `hole(missing)`); `!default` and `!global` flags the grammar
//!   rejects are forgiven as `!important` is in CSS.
//! - Not modelled: Sass maps and lists as values, arithmetic, `@use` module resolution across files,
//!   `@content` arguments, placeholder selector matching for `@extend`, and Less (no grammar).

// frob:ticket 01M487BKN1FE92BQ72KQWGBG11

use std::collections::{HashMap, HashSet};

use gob_ir::{
    AttrValue, DeclKind, GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, Status, Term,
    TermError, Universal, style,
};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::css::tokens::{Token, tokens};
use crate::css::{class_selector_nodes, error_nodes};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::model::collapse_ws;
use crate::pipeline::EXTRACTOR_VERSION;
use crate::view::{self, Naming};

/// File extensions (lowercase, no dot) the adapter claims.
pub(crate) const EXTENSIONS: &[&str] = &["scss"];

/// Unit kind of a `$x: value;` definition.
pub(crate) const KIND_VARIABLE: &str = "variable";
/// Unit kind of an `@mixin` definition.
pub(crate) const KIND_MIXIN: &str = "mixin";
/// Unit kind of an `@function` definition.
pub(crate) const KIND_FUNCTION: &str = "function";
/// Phase kind of a use of a variable.
pub(crate) const PHASE_VARIABLE: &str = "variable";
/// Phase kind of an `@include`.
pub(crate) const PHASE_MIXIN: &str = "mixin";
/// Attribute holding the comma-joined `$param` names of a mixin, a function or a mixin expansion.
pub(crate) const ATTR_PARAMS: &str = "scss.params";
/// Attribute set to `true` on a `!default` variable definition.
pub(crate) const ATTR_DEFAULT: &str = "scss.default";
/// Attribute set to `true` on a `!global` variable definition.
pub(crate) const ATTR_GLOBAL: &str = "scss.global";

/// How many mixin expansions may nest before the include is left unexpanded.
const MAX_EXPANSION_DEPTH: usize = 8;

type R<T> = Result<T, TermError>;

/// The SCSS adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct ScssAdapter;

impl Adapter for ScssAdapter {
    fn language(&self) -> &'static str {
        "scss"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Scss)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::Css)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Css)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Scss, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "scss", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "scss",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is an SCSS file this adapter folds (`.scss`, any case).
pub fn is_scss_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .and_then(gob_path::exact_text)
        .is_some_and(|e| EXTENSIONS.iter().any(|x| e.eq_ignore_ascii_case(x)))
}

/// One declared parameter of a mixin: its name without `$` and the default value text.
#[derive(Debug, Clone)]
struct Param {
    name: String,
    default: Option<String>,
}

/// A mixin seen so far: its parameters and the body block to fold again at each include.
#[derive(Clone)]
struct Mixin<'a> {
    params: Vec<Param>,
    body: Option<Node<'a>>,
}

/// The variable bindings of one Sass scope: name (no `$`) to the value text, `None` when unknown.
type Frame = HashMap<String, Option<String>>;

struct Scss<'a> {
    cx: Cx<'a>,
    path: &'a str,
    holes: u32,
    /// Byte spans of syntax errors that are valid SCSS the grammar rejects (`!default`, `!global`).
    forgiven: Vec<(usize, usize)>,
    /// Variable frames, the file scope first.
    frames: Vec<Frame>,
    mixins: HashMap<String, Mixin<'a>>,
    functions: HashSet<String>,
    /// Mixins whose expansion is being built, innermost last.
    active: Vec<String>,
}

fn fold_tree<'a>(
    text: &'a str,
    root: Node<'a>,
    input: &FileInput<'a>,
) -> Result<Folded, FoldError> {
    let mut scss = Scss {
        cx: Cx::new(input.path, "scss", text),
        path: input.path,
        holes: 0,
        forgiven: Vec::new(),
        frames: vec![Frame::new()],
        mixins: HashMap::new(),
        functions: HashSet::new(),
        active: Vec::new(),
    };
    let mut kids = scss.items(root)?;
    if scss.holes == 0 && scss.has_unforgiven_error(root) {
        kids.push(scss.hole(root)?);
    }
    let mut cx = scss.cx;
    let root_id = cx.add(file_root_spec(&cx, input.size as usize), &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = lexical_scopes(&term);
    let v = view::build(&term, input.path, Naming::Style);
    let mut file = base_file(input, "scss");
    file.fidelity = Fidelity::F2;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        status = ?file.parse_status,
        "scss file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// True for the tree-sitter kinds of SCSS at-rules and control directives.
fn is_at_rule(kind: &str) -> bool {
    kind == "at_rule"
        || kind == "else_clause"
        || kind == "else_if_clause"
        || kind.ends_with("_statement")
}

/// True for the directives whose block may or may not run (assignments inside are conditional).
fn is_control(name: &str) -> bool {
    matches!(name, "if" | "else" | "each" | "for" | "while")
}

/// True for a byte that can be part of a Sass identifier.
fn is_ident_byte(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'-' || b == b'_'
}

/// The names (no `$`) of the variables written in `text`, in order of appearance.
fn var_names(text: &str) -> Vec<String> {
    let bytes = text.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'$' {
            let start = i + 1;
            let mut end = start;
            while end < bytes.len() && is_ident_byte(bytes[end]) {
                end += 1;
            }
            if end > start {
                out.push(text[start..end].to_owned());
            }
            i = end.max(i + 1);
        } else {
            i += 1;
        }
    }
    out
}

/// Splits `text` at top-level commas (outside parentheses, brackets and quotes), each piece trimmed.
fn split_commas(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let (mut depth, mut quote) = (0usize, None::<char>);
    for c in text.chars() {
        match (quote, c) {
            (Some(q), _) => {
                cur.push(c);
                if c == q {
                    quote = None;
                }
            }
            (None, '"' | '\'') => {
                quote = Some(c);
                cur.push(c);
            }
            (None, '(' | '[') => {
                depth += 1;
                cur.push(c);
            }
            (None, ')' | ']') => {
                depth = depth.saturating_sub(1);
                cur.push(c);
            }
            (None, ',') if depth == 0 => out.push(std::mem::take(&mut cur).trim().to_owned()),
            _ => cur.push(c),
        }
    }
    if !cur.trim().is_empty() {
        out.push(cur.trim().to_owned());
    }
    out
}

/// The text inside the outer parentheses of `text` (`(a, b)` gives `a, b`).
fn inside_parens(text: &str) -> &str {
    let t = text.trim();
    t.strip_prefix('(')
        .and_then(|r| r.strip_suffix(')'))
        .unwrap_or(t)
}

/// The parameters written in a parameter list such as `($a, $b: 1px, $rest...)`.
fn parse_params(list: &str) -> Vec<Param> {
    split_commas(inside_parens(list))
        .into_iter()
        .filter_map(|piece| {
            let piece = piece.trim_end_matches("...").trim().to_owned();
            let (name, default) = match piece.split_once(':') {
                Some((n, d)) => (n.trim(), Some(d.trim().to_owned())),
                None => (piece.as_str(), None),
            };
            let name = name.strip_prefix('$')?;
            (!name.is_empty()).then(|| Param {
                name: name.to_owned(),
                default,
            })
        })
        .collect()
}

/// The `$a,$b` attribute text for `names`.
fn params_attr<'n>(names: impl Iterator<Item = &'n str>) -> String {
    names.map(|n| format!("${n}")).collect::<Vec<_>>().join(",")
}

impl<'a> Scss<'a> {
    fn t(&self, n: Node<'a>) -> &'a str {
        text_of(self.cx.text, n)
    }

    fn lookup(&self, name: &str) -> Option<&Option<String>> {
        self.frames.iter().rev().find_map(|f| f.get(name))
    }

    /// `raw` with every `$x` bound to a known value replaced by that value (values are stored resolved).
    fn substitute(&self, raw: &str) -> String {
        let mut out = String::with_capacity(raw.len());
        let mut rest = raw;
        while let Some(at) = rest.find('$') {
            out.push_str(&rest[..at]);
            let after = &rest[at + 1..];
            let len = after.bytes().take_while(|&b| is_ident_byte(b)).count();
            match self.lookup(&after[..len]) {
                Some(Some(value)) if len > 0 => out.push_str(value),
                _ => out.push_str(&rest[at..at + 1 + len]),
            }
            rest = &after[len..];
        }
        out.push_str(rest);
        out
    }

    fn has_unforgiven_error(&self, n: Node<'a>) -> bool {
        n.has_error()
            && (n.kind() == "ERROR"
                || error_nodes(n)
                    .iter()
                    .any(|e| !self.forgiven.contains(&(e.start_byte(), e.end_byte()))))
    }

    fn hole(&mut self, n: Node<'a>) -> R<NodeId> {
        let kind = if n.is_missing() {
            view::HOLE_MISSING
        } else {
            view::HOLE_PARSE_ERROR
        };
        self.holes += 1;
        tracing::debug!(path = self.path, kind, at = n.start_byte(), "scss hole");
        self.cx.op(Operator::hole(kind), n, &[])
    }

    /// The nodes for the rules, at-rules, definitions and declarations among the children of `parent`.
    fn items(&mut self, parent: Node<'a>) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(parent) {
            let kind = c.kind();
            if c.is_missing() || kind == "ERROR" {
                out.push(self.hole(c)?);
            } else if kind == "rule_set" {
                out.push(self.rule_set(c)?);
            } else if kind == "declaration" {
                out.push(self.declaration(c)?);
            } else if kind == "mixin_statement" {
                out.push(self.mixin_def(c)?);
            } else if kind == "function_statement" {
                out.push(self.function_def(c)?);
            } else if kind == "include_statement" {
                out.push(self.include(c)?);
            } else if is_at_rule(kind) {
                if let Some(id) = self.at_rule(c)? {
                    out.push(id);
                }
            } else if c.is_named() && !matches!(kind, "comment" | "js_comment") {
                tracing::trace!(path = self.path, kind, "scss node not modelled");
            }
        }
        Ok(out)
    }

    /// Folds the items of `block` in a fresh variable frame holding `bindings`; the frame is dropped after.
    ///
    /// For a `conditional` block (control flow), a variable it assigns that is visible outside becomes
    /// unknown there, since the branch may not run.
    fn scoped_items(
        &mut self,
        block: Node<'a>,
        bindings: Frame,
        conditional: bool,
    ) -> R<Vec<NodeId>> {
        self.frames.push(bindings);
        let kids = self.items(block);
        let frame = self.frames.pop().unwrap_or_default();
        if conditional {
            for name in frame.keys() {
                if let Some(slot) = self
                    .frames
                    .iter_mut()
                    .rev()
                    .find_map(|f| f.get_mut(name.as_str()))
                {
                    tracing::debug!(
                        path = self.path,
                        name,
                        "scss variable made unknown by branch"
                    );
                    *slot = None;
                }
            }
        }
        kids
    }

    /// `unit(style-rule)` over the declarations and nested rules of `block`, named `selector`.
    fn rule_unit(&mut self, n: Node<'a>, selector: &str, block: Option<Node<'a>>) -> R<NodeId> {
        let mut kids = class_selector_nodes(&mut self.cx, self.path, n)?;
        if let Some(b) = block {
            kids.extend(self.scoped_items(b, Frame::new(), false)?);
        }
        let spec = NodeSpec::new(
            Operator::unit(style::STYLE_RULE, "impl"),
            self.cx.node_loc(n),
        )
        .named(selector);
        self.cx.add(spec, &kids)
    }

    fn rule_set(&mut self, n: Node<'a>) -> R<NodeId> {
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
    fn at_rule(&mut self, n: Node<'a>) -> R<Option<NodeId>> {
        let text = self.t(n);
        let Some(after) = text.strip_prefix('@') else {
            tracing::debug!(
                path = self.path,
                kind = n.kind(),
                "scss at-rule without @ skipped"
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
        let control = is_control(&name);
        let mut bindings = Frame::new();
        if matches!(name.as_str(), "each" | "for") {
            let head = prelude
                .split_once(" in ")
                .or_else(|| prelude.split_once(" from "))
                .map_or(prelude.as_str(), |(h, _)| h);
            for v in var_names(head) {
                bindings.insert(v, None);
            }
        }
        let mut kids = match body {
            Some(b) if b.kind() == "keyframe_block_list" => self.keyframes(b)?,
            Some(b) => self.scoped_items(b, bindings, control)?,
            None => Vec::new(),
        };
        for clause in cs
            .iter()
            .filter(|c| matches!(c.kind(), "else_clause" | "else_if_clause"))
        {
            kids.extend(self.at_rule(*clause)?);
        }
        let spec = NodeSpec::new(Operator::unit(style::AT_RULE, "impl"), self.cx.node_loc(n))
            .named(&name)
            .attr(style::PRELUDE, prelude.as_str());
        self.cx.add(spec, &kids).map(Some)
    }

    fn keyframes(&mut self, list: Node<'a>) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(list) {
            if c.is_missing() || c.kind() == "ERROR" {
                out.push(self.hole(c)?);
            } else if c.kind() == "keyframe_block" {
                let block = children(c).into_iter().find(|k| k.kind() == "block");
                let end = block.map_or(c.end_byte(), |b| b.start_byte());
                let sel = collapse_ws(&self.cx.text[c.start_byte()..end]);
                out.push(self.rule_unit(c, &sel, block)?);
            }
        }
        Ok(out)
    }

    /// The component values of `raw` as nodes: literals, `phase(variable)` for each `$x`, `ref f()` for
    /// each call of a function defined earlier in the file, and `ref --x` for `var(--x)`.
    fn value_nodes(&mut self, raw: &str, at: Node<'a>) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for t in tokens(raw) {
            match t {
                Token::Var(name) => out.push(self.cx.op(Operator::reference(&name), at, &[])?),
                Token::Lit(_, text) if is_bare_variable(&text) => {
                    out.push(self.variable_use(&text[1..], at)?);
                }
                Token::Lit(kind, text) => {
                    out.push(self.cx.lit(kind, &text, at)?);
                    if let Some(f) = text.split_once('(').map(|(f, _)| f)
                        && self.functions.contains(f)
                    {
                        out.push(
                            self.cx
                                .op(Operator::reference(&format!("{f}()")), at, &[])?,
                        );
                    }
                    for name in var_names(&text) {
                        out.push(self.variable_use(&name, at)?);
                    }
                }
            }
        }
        Ok(out)
    }

    /// `phase(variable)` over `ref $name` and, when the value is known here, its expansion.
    fn variable_use(&mut self, name: &str, at: Node<'a>) -> R<NodeId> {
        let r = self
            .cx
            .op(Operator::reference(&format!("${name}")), at, &[])?;
        let mut kids = vec![r];
        let bound = match self.lookup(name) {
            Some(Some(value)) => Some(value.clone()),
            _ => None,
        };
        tracing::trace!(
            path = self.path,
            name,
            known = bound.is_some(),
            "scss variable use"
        );
        if let Some(value) = bound {
            let mut parts = Vec::new();
            for t in tokens(&value) {
                parts.push(match t {
                    Token::Lit(kind, text) => self.cx.lit(kind, &text, at)?,
                    Token::Var(v) => self.cx.op(Operator::reference(&v), at, &[])?,
                });
            }
            kids.push(
                self.cx
                    .op(Operator::group(GroupOrder::Sequence), at, &parts)?,
            );
        }
        self.cx.op(Operator::phase(PHASE_VARIABLE), at, &kids)
    }

    /// A property declaration, a custom-property definition or a `$x: value` variable definition.
    fn declaration(&mut self, n: Node<'a>) -> R<NodeId> {
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
        let value_text = &self.cx.text[value_start..n.end_byte()];
        let value = value_text.trim().trim_end_matches(';').trim_end();
        let flags = split_flags(value);
        let raw = flags.value;
        let bang_at = value_start + (value_text.len() - value_text.trim_start().len()) + raw.len();
        let mut kids = self.value_nodes(raw, n)?;
        let flagged = flags.important || flags.default || flags.global;
        for e in error_nodes(n) {
            if flagged && e.start_byte() >= bang_at {
                self.forgiven.push((e.start_byte(), e.end_byte()));
            } else if e.parent().is_some_and(|p| p.id() == n.id()) {
                kids.push(self.hole(e)?);
            }
        }
        let loc = self.cx.node_loc(n);
        if let Some(name) = property.strip_prefix('$') {
            self.bind_variable(name, raw, flags.default, flags.global);
            tracing::trace!(path = self.path, property, "scss variable definition");
            let spec = NodeSpec::new(Operator::unit(KIND_VARIABLE, "impl"), loc)
                .named(&property)
                .attr(style::RAW, raw)
                .attr(ATTR_DEFAULT, flags.default)
                .attr(ATTR_GLOBAL, flags.global);
            return self.cx.add(spec, &kids);
        }
        let spec = if property.starts_with("--") {
            NodeSpec::new(Operator::unit(style::CUSTOM_PROPERTY, "impl"), loc)
                .named(&property)
                .attr(style::RAW, raw)
        } else {
            NodeSpec::new(style::declaration_op(), loc)
                .named(&property)
                .attr(style::RAW, raw)
                .attr(style::IMPORTANT, flags.important)
        };
        tracing::trace!(path = self.path, property, "scss declaration");
        self.cx.add(spec, &kids)
    }

    /// Records `$name: raw` in the current frame (the file frame for `!global`; kept if `!default` and set).
    fn bind_variable(&mut self, name: &str, raw: &str, default: bool, global: bool) {
        if default && self.lookup(name).is_some() {
            tracing::debug!(path = self.path, name, "scss !default variable already set");
            return;
        }
        let value = self.substitute(raw);
        let frame = if global { 0 } else { self.frames.len() - 1 };
        self.frames[frame].insert(name.to_owned(), Some(value));
    }

    /// The `name` field of a mixin or function definition.
    fn def_name(&self, n: Node<'a>) -> Option<String> {
        n.child_by_field_name("name").map(|c| self.t(c).to_owned())
    }

    /// The parameters of the definition `n`.
    fn def_params(&self, n: Node<'a>) -> Vec<Param> {
        children(n)
            .into_iter()
            .find(|c| c.kind() == "parameters")
            .map(|p| parse_params(self.t(p)))
            .unwrap_or_default()
    }

    /// The definition `n` as a unit of `kind`, its body folded with the parameters unknown.
    fn definition(
        &mut self,
        n: Node<'a>,
        kind: &str,
        name: &str,
        params: &[Param],
        body: Option<Node<'a>>,
    ) -> R<NodeId> {
        let unknown: Frame = params.iter().map(|p| (p.name.clone(), None)).collect();
        let kids = match body {
            Some(b) => self.scoped_items(b, unknown, false)?,
            None => Vec::new(),
        };
        tracing::debug!(
            path = self.path,
            kind,
            name,
            params = params.len(),
            "scss definition"
        );
        let spec = NodeSpec::new(Operator::unit(kind, "impl"), self.cx.node_loc(n))
            .named(name)
            .attr(
                ATTR_PARAMS,
                params_attr(params.iter().map(|p| p.name.as_str())).as_str(),
            );
        self.cx.add(spec, &kids)
    }

    fn mixin_def(&mut self, n: Node<'a>) -> R<NodeId> {
        let name = self.def_name(n).unwrap_or_default();
        let params = self.def_params(n);
        let body = children(n).into_iter().find(|c| c.kind() == "block");
        self.mixins.insert(
            name.clone(),
            Mixin {
                params: params.clone(),
                body,
            },
        );
        self.definition(n, KIND_MIXIN, &name, &params, body)
    }

    fn function_def(&mut self, n: Node<'a>) -> R<NodeId> {
        let name = self.def_name(n).unwrap_or_default();
        let params = self.def_params(n);
        let body = children(n).into_iter().find(|c| c.kind() == "block");
        self.functions.insert(name.clone());
        self.definition(n, KIND_FUNCTION, &name, &params, body)
    }

    /// `@include name(args) { content }` as `phase(mixin)` with the expansion when the mixin is known.
    fn include(&mut self, n: Node<'a>) -> R<NodeId> {
        let text = self.t(n);
        let name = text
            .strip_prefix("@include")
            .unwrap_or_default()
            .trim_start()
            .split(|c: char| c.is_whitespace() || matches!(c, '(' | '{' | ';'))
            .next()
            .unwrap_or_default()
            .to_owned();
        let cs = children(n);
        let args: Vec<String> = cs
            .iter()
            .find(|c| c.kind() == "arguments")
            .map(|a| split_commas(inside_parens(self.t(*a))))
            .unwrap_or_default();
        let block = cs.iter().find(|c| c.kind() == "block").copied();
        let mut call = vec![
            self.cx
                .op(Operator::reference(&format!("@{name}")), n, &[])?,
        ];
        for a in &args {
            let value = a
                .split_once(':')
                .filter(|(k, _)| k.trim().starts_with('$'))
                .map_or(a.as_str(), |(_, v)| v);
            call.extend(self.value_nodes(value.trim(), n)?);
        }
        if let Some(b) = block {
            call.extend(self.scoped_items(b, Frame::new(), false)?);
        }
        let call = self
            .cx
            .op(Operator::group(GroupOrder::Sequence), n, &call)?;
        let mut kids = vec![call];
        if let Some(e) = self.expansion(n, &name, &args)? {
            kids.push(e);
        } else {
            tracing::debug!(path = self.path, name, "scss include left unexpanded");
        }
        self.cx.op(Operator::phase(PHASE_MIXIN), n, &kids)
    }

    /// The expansion group of including mixin `name` with `args`, or `None` when it cannot be expanded.
    fn expansion(&mut self, n: Node<'a>, name: &str, args: &[String]) -> R<Option<NodeId>> {
        let Some(mixin) = self.mixins.get(name).cloned() else {
            return Ok(None);
        };
        let Some(body) = mixin.body else {
            return Ok(None);
        };
        if self.active.iter().any(|a| a == name) || self.active.len() >= MAX_EXPANSION_DEPTH {
            tracing::debug!(path = self.path, name, "scss mixin recursion not expanded");
            return Ok(None);
        }
        let bindings = self.bind_arguments(&mixin.params, args);
        self.active.push(name.to_owned());
        let kids = self.scoped_items(body, bindings, false);
        self.active.pop();
        let kids = kids?;
        tracing::debug!(
            path = self.path,
            name,
            nodes = kids.len(),
            "scss mixin expanded"
        );
        let spec = NodeSpec::new(Operator::group(GroupOrder::Sequence), self.cx.node_loc(n)).attr(
            ATTR_PARAMS,
            params_attr(mixin.params.iter().map(|p| p.name.as_str())).as_str(),
        );
        self.cx.add(spec, &kids).map(Some)
    }

    /// The parameter frame of a mixin call: positional and keyword arguments, then defaults.
    fn bind_arguments(&self, params: &[Param], args: &[String]) -> Frame {
        let mut frame = Frame::new();
        let mut positional = 0usize;
        for arg in args {
            let keyword = arg
                .split_once(':')
                .and_then(|(k, v)| Some((k.trim().strip_prefix('$')?, v.trim())));
            if let Some((k, v)) = keyword {
                frame.insert(k.to_owned(), Some(self.substitute(v)));
            } else {
                if let Some(p) = params.get(positional) {
                    frame.insert(p.name.clone(), Some(self.substitute(arg)));
                }
                positional += 1;
            }
        }
        for p in params {
            frame
                .entry(p.name.clone())
                .or_insert_with(|| p.default.as_deref().map(|d| self.substitute(d)));
        }
        frame
    }
}

/// A declaration value split from its trailing `!important`, `!default` and `!global` flags.
struct Flags<'v> {
    value: &'v str,
    important: bool,
    default: bool,
    global: bool,
}

/// Strips the trailing `!flag` words from `value` and reports which were present.
fn split_flags(value: &str) -> Flags<'_> {
    let mut f = Flags {
        value,
        important: false,
        default: false,
        global: false,
    };
    loop {
        let t = f.value.trim_end();
        let Some(bang) = t.rfind('!') else { break };
        match t[bang + 1..].trim().to_ascii_lowercase().as_str() {
            "important" => f.important = true,
            "default" => f.default = true,
            "global" => f.global = true,
            _ => break,
        }
        f.value = t[..bang].trim_end();
    }
    f
}

/// True when `text` is exactly one variable, `$name`.
fn is_bare_variable(text: &str) -> bool {
    text.strip_prefix('$')
        .is_some_and(|r| !r.is_empty() && r.bytes().all(is_ident_byte))
}

/// The symbolic scope graph of a stylesheet (D96): rules, at-rules, mixins, functions and mixin expansions
/// open scopes; variables, mixins (`@m`) and functions (`f()`) are declarations; every `ref` is a use.
fn lexical_scopes(term: &Term) -> ScopeGraph {
    let flag = |id: NodeId, key: &str| {
        matches!(term.node(id).attrs().get(key), Some(AttrValue::Bool(true)))
    };
    let mut g = ScopeGraph::new();
    let root = g.add_scope(Some(term.root()));
    let (mut decls, mut uses) = (0usize, 0usize);
    let mut stack = vec![(term.root(), root)];
    while let Some((id, scope)) = stack.pop() {
        let node = term.node(id);
        let name = node.name().unwrap_or_default();
        let mut inner = scope;
        let mut second = scope;
        match term.operator(id) {
            Operator::Universal(Universal::Unit { kind, .. }) => match kind.as_str() {
                KIND_VARIABLE => {
                    let target = if flag(id, ATTR_GLOBAL) { root } else { scope };
                    let status = if flag(id, ATTR_DEFAULT) {
                        Status::May
                    } else {
                        Status::Must
                    };
                    g.declare(target, name, None, DeclKind::Other, status, Some(id));
                    decls += 1;
                }
                KIND_MIXIN | KIND_FUNCTION => {
                    let key = if kind == KIND_MIXIN {
                        format!("@{name}")
                    } else {
                        format!("{name}()")
                    };
                    g.declare(scope, &key, None, DeclKind::Other, Status::Must, Some(id));
                    decls += 1;
                    inner = open_scope(&mut g, id, scope, node.attrs().get_str(ATTR_PARAMS));
                }
                style::STYLE_RULE | style::AT_RULE => {
                    inner = open_scope(&mut g, id, scope, None);
                }
                _ => {}
            },
            Operator::Universal(Universal::Ref { name }) => {
                g.reference(scope, name, Some(id));
                uses += 1;
            }
            Operator::Universal(Universal::Phase { .. }) => {
                if let Some(&expansion) = node.children().get(1) {
                    let params = term.node(expansion).attrs().get_str(ATTR_PARAMS);
                    second = open_scope(&mut g, expansion, scope, params);
                }
            }
            _ => {}
        }
        for (i, &c) in node.children().iter().enumerate().rev() {
            let sub = if matches!(
                term.operator(id),
                Operator::Universal(Universal::Phase { .. })
            ) {
                if i == 1 { second } else { scope }
            } else {
                inner
            };
            stack.push((c, sub));
        }
    }
    tracing::debug!(
        scopes = g.scope_count(),
        declarations = decls,
        references = uses,
        "scss scope graph built"
    );
    g
}

/// Opens a scope for `node` under `parent` with a must-edge up, declaring the `$a,$b` `params` as binders.
fn open_scope(
    g: &mut ScopeGraph,
    node: NodeId,
    parent: gob_ir::ScopeId,
    params: Option<&str>,
) -> gob_ir::ScopeId {
    let s = g.add_scope(Some(node));
    g.add_edge(s, gob_ir::Label::Lexical, parent, Status::Must);
    for p in params
        .unwrap_or_default()
        .split(',')
        .filter(|p| !p.is_empty())
    {
        g.declare(s, p, None, DeclKind::Binder, Status::Must, None);
    }
    s
}
