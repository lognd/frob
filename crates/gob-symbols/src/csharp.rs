//! The C# adapter (fidelity F1 plus attributes and preprocessor conditions): tree-sitter tree to a U term.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`. A namespace is one `unit(namespace)` per dotted component
//!   (`namespace A.B` is `A` containing `B`; a file-scoped `namespace A;` owns every later
//!   declaration of the file). Types are `unit(class | struct | interface | record | enum |
//!   delegate)`, enum members `unit(variant)`.
//! - Members: methods `unit(method)` (a finalizer is the method `~T`), constructors
//!   `unit(constructor)` (named like the type; a static constructor is `$cctor`), properties,
//!   indexers (`this`), events, fields and constants (one unit per declarator, spanning the whole
//!   declaration), operators (`operator+`, conversions `operator-implicit[Type]`). Local
//!   functions are `unit(function)` nested in the member that declares them. Accessors, lambdas
//!   and statements are not units; they are body tokens of their member.
//! - Every unit has children in three groups: one `attr` per attribute (also copied into the
//!   signature group, G7), a `group` marked `ir.facet = "sig"` holding the name, modifier,
//!   parameter, return and base-list tokens, and the body as one `group`. Tokens are `lit`s, so
//!   reformatting and comments never change a digest (G8).
//! - Preprocessor: every `#if`, `#elif` and `#else` branch is scanned. A unit declared under a
//!   branch carries the condition stack in [`UnitFacts::conditions`] (`UNITY_EDITOR`, then
//!   `!(UNITY_EDITOR)` in the `#else`). Other directives (`#region`, `#define`, `#pragma`) are
//!   tokens. A conditional that is not wholly a member list (inside a member body, around an
//!   attribute list) is a `hole(unmodelled)`: the file reads as a partial parse and the enclosing
//!   member's digests are unknown, never silently stable.
//! - Constructs this adapter does not model (top-level statements, unknown member kinds, syntax
//!   errors) carry a `hole`, so rules that need the missing facts answer Unresolved. Subtrees
//!   deeper than [`MAX_DEPTH`] collapse into one `opaque(depth-limit)`.
//! - Not yet modelled (the next story): `using` imports, references and calls; they are tokens.
//! - A `partial` type is one unit per part here; [`crate::SymbolGraph`] merges the parts into one
//!   unit with several spans (`crate::model::merge_partials`).

// frob:ticket 01M44YQSZ3YEXRDW9RKER9HRA2

use std::collections::HashMap;

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, TermError, reserved};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::model::{
    AttributeFact, CallSite, FieldDecl, ImportEdge, LocalBinding, Receiver, RetType, UnitFacts,
    UnitSpan, UseBinding, collapse_ws,
};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{
    self, ATTR_IMPLEMENTS, ATTR_VISIBILITY, HOLE_MISSING, HOLE_PARSE_ERROR, HOLE_UNMODELLED, Naming,
};

/// Deepest term nesting before a subtree collapses into one opaque node.
const MAX_DEPTH: usize = 160;

type R<T> = Result<T, TermError>;

/// The C# adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct CSharpAdapter;

impl Adapter for CSharpAdapter {
    fn language(&self) -> &'static str {
        "csharp"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::CSharp)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::CSharp)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::CSharp)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::CSharp, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "csharp", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "csharp",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a C# source file (`.cs`, any case).
pub fn is_csharp_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("cs"))
}

/// What encloses a declaration, for its default accessibility.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Container {
    /// The file or a namespace: types default to `internal`.
    Namespace,
    /// A class, struct or record: members default to `private`.
    Type,
    /// An interface: members are `public`.
    Interface,
    /// An enum: members are `public`.
    Enum,
}

/// A byte span `(start, end)`.
type Span = (usize, usize);

/// The pieces of one declaration node, split by role.
#[derive(Default)]
struct Parts<'t> {
    attrs: Vec<Node<'t>>,
    sig: Vec<Node<'t>>,
    body: Vec<Node<'t>>,
    modifiers: Vec<String>,
}

/// Everything a unit is built from.
struct UnitSpec {
    span: Span,
    kind: &'static str,
    name: String,
    qualifier: Option<String>,
    vis: &'static str,
    implements: Option<String>,
    attr_ids: Vec<NodeId>,
    sig: Vec<NodeId>,
    body: Vec<NodeId>,
    facts: UnitFacts,
}

struct Fold<'a> {
    cx: Cx<'a>,
    path: &'a str,
    containers: Vec<Container>,
    /// Preprocessor conditions in force, outermost first.
    conds: Vec<String>,
    facts: HashMap<NodeId, UnitFacts>,
    /// The namespace segments enclosing the declaration being folded.
    ns: Vec<String>,
    /// Calls found in each member, in source order.
    raw_calls: Vec<(NodeId, RawCall)>,
    /// Every `using` directive with the namespace it sits in.
    raw_uses: Vec<RawUse>,
    /// The declared type text of each field or property unit.
    raw_fields: Vec<(NodeId, String)>,
}

fn is_comment(n: Node<'_>) -> bool {
    n.kind() == "comment"
}

/// True for the declaration kinds this adapter turns into units.
fn is_unit_kind(kind: &str) -> bool {
    matches!(
        kind,
        "namespace_declaration"
            | "file_scoped_namespace_declaration"
            | "class_declaration"
            | "struct_declaration"
            | "interface_declaration"
            | "record_declaration"
            | "record_struct_declaration"
            | "enum_declaration"
            | "delegate_declaration"
            | "method_declaration"
            | "constructor_declaration"
            | "destructor_declaration"
            | "operator_declaration"
            | "conversion_operator_declaration"
            | "property_declaration"
            | "indexer_declaration"
            | "event_declaration"
            | "event_field_declaration"
            | "field_declaration"
            | "enum_member_declaration"
            | "local_function_statement"
    )
}

/// True when some node under `n` (or `n`) is a unit declaration.
fn declares_units(n: Node<'_>) -> bool {
    let mut stack = vec![n];
    while let Some(x) = stack.pop() {
        if is_unit_kind(x.kind()) {
            return true;
        }
        stack.extend(children(x));
    }
    false
}

/// A `#define`-like directive node that carries no structure (`#region`, `#pragma`, ...).
fn is_plain_directive(kind: &str) -> bool {
    kind.starts_with("preproc_")
        && !kind.starts_with("preproc_if")
        && kind != "preproc_elif"
        && kind != "preproc_else"
}

/// The accessibility of a declaration from its modifier keywords, else `default`.
fn visibility_of(mods: &[String], default: &'static str, explicit_interface: bool) -> &'static str {
    let has = |m: &str| mods.iter().any(|x| x == m);
    if explicit_interface || has("public") {
        "public"
    } else if has("file") {
        "private"
    } else if has("protected") && has("private") {
        "crate"
    } else if has("protected") {
        "public"
    } else if has("internal") {
        "crate"
    } else if has("private") {
        "private"
    } else {
        default
    }
}

/// `text` with every whitespace character removed.
fn squash(text: &str) -> String {
    text.split_whitespace().collect()
}

/// A symref-safe spelling of `text`: no whitespace, no `{`, `}`, `[` or `]`.
fn safe(text: &str) -> String {
    squash(text)
        .chars()
        .map(|c| match c {
            '[' | '{' => '(',
            ']' | '}' => ')',
            c => c,
        })
        .collect()
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut f = Fold {
        cx: Cx::new(input.path, "csharp", text),
        path: input.path,
        containers: vec![Container::Namespace],
        conds: Vec::new(),
        facts: HashMap::new(),
        ns: Vec::new(),
        raw_calls: Vec::new(),
        raw_uses: Vec::new(),
        raw_fields: Vec::new(),
    };
    let nodes = children(root);
    let kids = f.members(&nodes, root.end_byte(), 1)?;
    let spec = file_root_spec(&f.cx, input.size as usize);
    let root_id = f.cx.add(spec, &kids)?;
    let Fold {
        cx,
        facts,
        raw_calls,
        raw_uses,
        raw_fields,
        ..
    } = f;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::CSharp);
    let mut file = base_file(input, "csharp");
    file.fidelity = Fidelity::F1;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    let at: HashMap<Symref, usize> = file
        .extras
        .iter()
        .enumerate()
        .map(|(i, e)| (e.symref.clone(), i))
        .collect();
    for (node, mut unit_facts) in facts {
        let Some(symref) = v.by_node.get(&node) else {
            continue;
        };
        let Some(&i) = at.get(symref) else {
            continue;
        };
        if unit_facts.partial {
            unit_facts.spans = vec![UnitSpan {
                path: input.path.to_owned(),
                span: file.symbols[i].span,
                conditions: unit_facts.conditions.clone(),
            }];
        }
        file.extras[i].facts = unit_facts;
    }
    file_sites(&mut file, &v.by_node, raw_calls, raw_uses, raw_fields);
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        calls = file.calls.len(),
        imports = file.imports.len(),
        status = ?file.parse_status,
        "csharp file folded"
    );
    Ok(Folded { term, scopes, file })
}

impl<'a> Fold<'a> {
    fn t(&self, n: Node<'_>) -> &'a str {
        text_of(self.cx.text, n)
    }

    fn hole(&mut self, n: Node<'_>) -> R<NodeId> {
        let kind = if n.is_missing() {
            HOLE_MISSING
        } else {
            HOLE_PARSE_ERROR
        };
        tracing::debug!(path = self.path, kind, at = n.start_byte(), "csharp hole");
        self.cx.op(Operator::hole(kind), n, &[])
    }

    fn unmodelled(&mut self, n: Node<'_>, what: &str) -> R<NodeId> {
        tracing::debug!(
            path = self.path,
            what,
            at = n.start_byte(),
            "csharp construct unmodelled"
        );
        self.cx.op(Operator::hole(HOLE_UNMODELLED), n, &[])
    }

    fn comment(&mut self, n: Node<'_>) -> R<NodeId> {
        let text = self.t(n).to_owned();
        self.cx.op(Operator::comment(&text), n, &[])
    }

    // ---- generic translation ----

    /// Pushes the token `lit`s of `n` (comments skipped) onto `out`; syntax errors and conditionals
    /// inside become holes.
    fn tokens(&mut self, n: Node<'_>, out: &mut Vec<NodeId>) -> R<()> {
        let mut stack = vec![n];
        while let Some(x) = stack.pop() {
            if is_comment(x) {
                continue;
            }
            if x.is_error() || x.is_missing() {
                out.push(self.hole(x)?);
                continue;
            }
            if x.kind().starts_with("preproc_if") {
                out.push(self.unmodelled(x, "conditional inside a declaration header")?);
            }
            if x.child_count() == 0 {
                out.push(self.cx.lit(x.kind(), self.t(x), x)?);
            } else {
                stack.extend(children(x).into_iter().rev());
            }
        }
        Ok(())
    }

    /// Collapses `n` into one opaque node; a hole is added when units are lost with it.
    fn collapse(&mut self, n: Node<'_>) -> R<NodeId> {
        let mut toks = Vec::new();
        let mut stack = vec![n];
        while let Some(x) = stack.pop() {
            if is_comment(x) {
                continue;
            }
            if x.child_count() == 0 {
                toks.push(self.t(x));
            } else {
                stack.extend(children(x).into_iter().rev());
            }
        }
        tracing::debug!(
            path = self.path,
            at = n.start_byte(),
            "depth limit: subtree collapsed"
        );
        let spec = NodeSpec::new(
            Operator::opaque("depth-limit", toks.join(" ").as_bytes()),
            self.cx.node_loc(n),
        );
        let opaque = self.cx.add(spec, &[])?;
        if !declares_units(n) {
            return Ok(opaque);
        }
        let hole = self.unmodelled(n, "declarations below the depth limit")?;
        self.cx
            .op(Operator::group(GroupOrder::Sequence), n, &[opaque, hole])
    }

    /// Translates a body node: tokens as `lit`s, local functions as units, other nodes as `csharp.<kind>`.
    fn tr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        if depth > MAX_DEPTH {
            return self.collapse(n);
        }
        if is_comment(n) {
            return self.comment(n);
        }
        if n.is_error() || n.is_missing() {
            return self.hole(n);
        }
        match n.kind() {
            "local_function_statement" => self.member_unit(n, depth),
            "string_literal"
            | "verbatim_string_literal"
            | "raw_string_literal"
            | "interpolated_string_expression"
            | "character_literal" => self.cx.lit(n.kind(), self.t(n), n),
            _ if n.child_count() == 0 => self.cx.lit(n.kind(), self.t(n), n),
            kind => {
                let mut kids = Vec::new();
                for c in children(n) {
                    kids.push(self.tr(c, depth + 1)?);
                }
                if kind.starts_with("preproc_if") {
                    kids.push(self.unmodelled(n, "conditional inside a member body")?);
                }
                self.cx.op(
                    Operator::adapter("csharp", kind, gob_ir::Sort::Exp),
                    n,
                    &kids,
                )
            }
        }
    }

    // ---- declaration lists ----

    /// The units, comments and holes of the declarations `nodes` (a file, namespace or type body).
    fn members(&mut self, nodes: &[Node<'_>], end: usize, depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for (i, n) in nodes.iter().copied().enumerate() {
            if !n.is_named() {
                continue;
            }
            if depth > MAX_DEPTH {
                out.push(self.collapse(n)?);
                continue;
            }
            if is_comment(n) {
                out.push(self.comment(n)?);
                continue;
            }
            if n.is_error() || n.is_missing() {
                out.push(self.hole(n)?);
                continue;
            }
            match n.kind() {
                "file_scoped_namespace_declaration" => {
                    let saved = self.ns.len();
                    self.ns.extend(self.ns_parts(n));
                    let inner = self.nested(Container::Namespace, &nodes[i + 1..], end, depth + 1);
                    self.ns.truncate(saved);
                    let inner = inner?;
                    out.push(self.namespace_chain(n, (n.start_byte(), end), inner)?);
                    return Ok(out);
                }
                "namespace_declaration" => out.push(self.namespace_block(n, depth)?),
                "class_declaration" => out.push(self.type_unit(n, "class", depth)?),
                "struct_declaration" => out.push(self.type_unit(n, "struct", depth)?),
                "interface_declaration" => out.push(self.type_unit(n, "interface", depth)?),
                "record_declaration" | "record_struct_declaration" => {
                    out.push(self.type_unit(n, "record", depth)?);
                }
                "enum_declaration" => out.push(self.type_unit(n, "enum", depth)?),
                "delegate_declaration" => out.push(self.delegate_unit(n)?),
                "method_declaration"
                | "constructor_declaration"
                | "destructor_declaration"
                | "operator_declaration"
                | "conversion_operator_declaration"
                | "property_declaration"
                | "indexer_declaration"
                | "event_declaration" => out.push(self.member_unit(n, depth)?),
                "field_declaration" | "event_field_declaration" => {
                    out.extend(self.field_units(n)?);
                }
                "enum_member_declaration" => out.push(self.variant_unit(n)?),
                "preproc_if" => out.extend(self.conditional(n, end, depth)?),
                "using_directive" => {
                    self.using(n);
                    out.push(self.tr(n, depth + 1)?);
                }
                "extern_alias_directive" | "global_attribute" => {
                    out.push(self.tr(n, depth + 1)?);
                }
                k if is_plain_directive(k) => out.push(self.tr(n, depth + 1)?),
                _ => {
                    out.push(self.tr(n, depth + 1)?);
                    out.push(self.unmodelled(n, n.kind())?);
                }
            }
        }
        Ok(out)
    }

    /// [`Self::members`] inside a container of kind `c`.
    fn nested(
        &mut self,
        c: Container,
        nodes: &[Node<'_>],
        end: usize,
        depth: usize,
    ) -> R<Vec<NodeId>> {
        self.containers.push(c);
        let out = self.members(nodes, end, depth);
        self.containers.pop();
        out
    }

    /// The members of every branch of the `#if` chain at `n`, each under its condition.
    fn conditional(&mut self, n: Node<'_>, end: usize, depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        let mut negated: Vec<String> = Vec::new();
        let mut cur = Some(n);
        while let Some(b) = cur {
            let cond_node = b.child_by_field_name("condition");
            let alt = b.child_by_field_name("alternative");
            let cond = cond_node.map(|c| collapse_ws(self.t(c)));
            let saved = self.conds.len();
            self.conds.extend(negated.iter().map(|c| format!("!({c})")));
            self.conds.extend(cond.clone());
            tracing::trace!(path = self.path, conds = ?self.conds, "csharp conditional branch");
            let body: Vec<Node<'_>> = children(b)
                .into_iter()
                .filter(|c| {
                    Some(c.id()) != cond_node.map(|x| x.id()) && Some(c.id()) != alt.map(|x| x.id())
                })
                .collect();
            let r = self.members(&body, end, depth + 1);
            self.conds.truncate(saved);
            out.extend(r?);
            negated.extend(cond);
            cur = alt;
        }
        Ok(out)
    }

    // ---- units ----

    /// Splits declaration `n` into attribute lists, signature, body (the `body_fields`) and modifiers.
    fn split<'t>(&self, n: Node<'t>, body_fields: &[&str]) -> Parts<'t> {
        let mut parts = Parts::default();
        for (i, c) in children(n).into_iter().enumerate() {
            let field = u32::try_from(i)
                .ok()
                .and_then(|i| n.field_name_for_child(i));
            match c.kind() {
                "attribute_list" => parts.attrs.push(c),
                "comment" => {}
                "modifier" => {
                    parts.modifiers.push(squash(self.t(c)));
                    parts.sig.push(c);
                }
                "declaration_list"
                | "enum_member_declaration_list"
                | "accessor_list"
                | "arrow_expression_clause"
                | "block"
                | "constructor_initializer" => {
                    parts.body.push(c);
                }
                _ if field.is_some_and(|f| body_fields.contains(&f)) => parts.body.push(c),
                _ => parts.sig.push(c),
            }
        }
        parts
    }

    /// The `attr` nodes of `lists` and the facts they carry.
    fn attributes(&mut self, lists: &[Node<'_>]) -> R<(Vec<NodeId>, Vec<AttributeFact>)> {
        let mut ids = Vec::new();
        let mut facts = Vec::new();
        for list in lists {
            let target = children(*list)
                .into_iter()
                .find(|c| c.kind() == "attribute_target_specifier")
                .map(|t| squash(self.t(t)).trim_end_matches(':').to_owned());
            for a in children(*list)
                .into_iter()
                .filter(|c| c.kind() == "attribute")
            {
                let name = a
                    .child_by_field_name("name")
                    .map_or_else(String::new, |nm| squash(self.t(nm)));
                let args = children(a)
                    .into_iter()
                    .find(|c| c.kind() == "attribute_argument_list");
                let mut payload = Vec::new();
                if let Some(args) = args {
                    self.tokens(args, &mut payload)?;
                }
                let text = args.map_or_else(String::new, |x| {
                    let raw = collapse_ws(self.t(x));
                    raw.strip_prefix('(')
                        .and_then(|r| r.strip_suffix(')'))
                        .unwrap_or(&raw)
                        .trim()
                        .to_owned()
                });
                ids.push(self.cx.op(Operator::attr(&name), a, &payload)?);
                facts.push(AttributeFact {
                    name,
                    args: text,
                    target: target.clone(),
                });
            }
        }
        Ok((ids, facts))
    }

    /// Builds the unit `u`, records its facts and returns it.
    fn make_unit(&mut self, mut u: UnitSpec) -> R<NodeId> {
        let loc = self.cx.loc(u.span.0, u.span.1);
        let mut kids = std::mem::take(&mut u.attr_ids);
        let sig_spec = NodeSpec::new(Operator::group(GroupOrder::Sequence), loc.clone())
            .attr(reserved::FACET, "sig");
        kids.push(self.cx.add(sig_spec, &u.sig)?);
        let body_spec = NodeSpec::new(Operator::group(GroupOrder::Sequence), loc.clone());
        kids.push(self.cx.add(body_spec, &u.body)?);
        let mut spec = NodeSpec::new(Operator::unit(u.kind, "impl"), loc)
            .named(&u.name)
            .attr(ATTR_VISIBILITY, u.vis);
        if let Some(q) = &u.qualifier {
            spec = spec.attr(reserved::QUALIFIER, q.as_str());
        }
        if let Some(i) = &u.implements {
            spec = spec.attr(ATTR_IMPLEMENTS, i.as_str());
        }
        let id = self.cx.add(spec, &kids)?;
        u.facts.conditions.clone_from(&self.conds);
        self.facts.insert(id, u.facts);
        tracing::trace!(path = self.path, kind = u.kind, name = %u.name, "csharp unit");
        Ok(id)
    }

    /// The default accessibility of a member of the innermost container.
    fn default_vis(&self) -> &'static str {
        match self.containers.last() {
            Some(Container::Interface | Container::Enum) => "public",
            Some(Container::Type) => "private",
            Some(Container::Namespace) | None => "crate",
        }
    }

    /// A unit for declaration `n`: attributes, name token and signature tokens from `parts`, then `body`.
    fn declared(
        &mut self,
        n: Node<'_>,
        parts: &Parts<'_>,
        d: Decl<'_>,
        body: Vec<NodeId>,
    ) -> R<NodeId> {
        let (attr_ids, attributes) = self.attributes(&parts.attrs)?;
        let (mut sig, _) = self.attributes(&parts.attrs)?;
        sig.push(self.cx.lit("name", &d.name, d.name_node)?);
        for s in parts.sig.iter().filter(|s| s.id() != d.name_node.id()) {
            self.tokens(*s, &mut sig)?;
        }
        let facts = UnitFacts {
            attributes,
            bases: d.bases,
            modifiers: parts.modifiers.clone(),
            partial: parts.modifiers.iter().any(|m| m == "partial"),
            ..UnitFacts::default()
        };
        self.make_unit(UnitSpec {
            span: (n.start_byte(), n.end_byte()),
            kind: d.kind,
            name: d.name,
            qualifier: d.qualifier,
            vis: d.vis,
            implements: d.implements,
            attr_ids,
            sig,
            body,
            facts,
        })
    }

    /// The translated `nodes` in the current scope.
    fn body_nodes(&mut self, nodes: &[Node<'_>], depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for n in nodes {
            out.push(self.tr(*n, depth + 1)?);
        }
        Ok(out)
    }

    /// A namespace unit per dotted component of `n`'s name, innermost holding `inner`, all spanning `span`.
    fn namespace_chain(&mut self, n: Node<'_>, span: Span, inner: Vec<NodeId>) -> R<NodeId> {
        let Some(name_node) = n.child_by_field_name("name") else {
            return self.hole(n);
        };
        let full = squash(self.t(name_node));
        let full = full.strip_prefix("global::").unwrap_or(&full).to_owned();
        let mut body = inner;
        for part in full.rsplit('.') {
            let sig = vec![self.cx.lit("name", part, name_node)?];
            let id = self.make_unit(UnitSpec {
                span,
                kind: "namespace",
                name: part.to_owned(),
                qualifier: None,
                vis: "public",
                implements: None,
                attr_ids: Vec::new(),
                sig,
                body,
                facts: UnitFacts::default(),
            })?;
            body = vec![id];
        }
        Ok(body[0])
    }

    fn namespace_block(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(body) = n.child_by_field_name("body") else {
            return self.hole(n);
        };
        let saved = self.ns.len();
        self.ns.extend(self.ns_parts(n));
        let inner = self.nested(
            Container::Namespace,
            &children(body),
            body.end_byte(),
            depth + 1,
        );
        self.ns.truncate(saved);
        let inner = inner?;
        self.namespace_chain(n, (n.start_byte(), n.end_byte()), inner)
    }

    /// The base types of a type declaration's `base_list`, whitespace removed.
    fn bases_of(&self, parts: &Parts<'_>) -> Vec<String> {
        let mut out = Vec::new();
        for list in parts.sig.iter().filter(|c| c.kind() == "base_list") {
            for b in children(*list).into_iter().filter(Node::is_named) {
                match b.kind() {
                    "argument_list" | "comment" => {}
                    "primary_constructor_base_type" => {
                        if let Some(t) = children(b).into_iter().find(Node::is_named) {
                            out.push(squash(self.t(t)));
                        }
                    }
                    _ => out.push(squash(self.t(b))),
                }
            }
        }
        out
    }

    fn type_unit(&mut self, n: Node<'_>, kind: &'static str, depth: usize) -> R<NodeId> {
        let Some(name_node) = n.child_by_field_name("name") else {
            return self.hole(n);
        };
        let parts = self.split(n, &[]);
        let vis = visibility_of(&parts.modifiers, self.default_vis(), false);
        let container = match kind {
            "interface" => Container::Interface,
            "enum" => Container::Enum,
            _ => Container::Type,
        };
        let mut body = Vec::new();
        for list in &parts.body {
            body.extend(self.nested(container, &children(*list), list.end_byte(), depth + 1)?);
        }
        let bases = self.bases_of(&parts);
        let name = self.t(name_node).to_owned();
        self.declared(
            n,
            &parts,
            Decl {
                kind,
                name,
                qualifier: None,
                name_node,
                vis,
                implements: None,
                bases,
            },
            body,
        )
    }

    fn delegate_unit(&mut self, n: Node<'_>) -> R<NodeId> {
        let Some(name_node) = n.child_by_field_name("name") else {
            return self.hole(n);
        };
        let parts = self.split(n, &[]);
        let vis = visibility_of(&parts.modifiers, self.default_vis(), false);
        let name = self.t(name_node).to_owned();
        self.declared(
            n,
            &parts,
            Decl {
                kind: "delegate",
                name,
                qualifier: None,
                name_node,
                vis,
                implements: None,
                bases: Vec::new(),
            },
            Vec::new(),
        )
    }

    /// A method, constructor, finalizer, operator, property, indexer, event or local function.
    fn member_unit(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let named = n.child_by_field_name("name");
        let kids = children(n);
        let token = |k: &str| kids.iter().copied().find(|c| c.kind() == k);
        let parts = self.split(n, &["value"]);
        let is_static = parts.modifiers.iter().any(|m| m == "static");
        let resolved: Option<(&'static str, String, Option<String>, Node<'_>)> = match n.kind() {
            "method_declaration" => named.map(|x| ("method", self.t(x).to_owned(), None, x)),
            "local_function_statement" => {
                named.map(|x| ("function", self.t(x).to_owned(), None, x))
            }
            "constructor_declaration" => named.map(|x| {
                let name = if is_static {
                    "$cctor".to_owned()
                } else {
                    self.t(x).to_owned()
                };
                ("constructor", name, None, x)
            }),
            "destructor_declaration" => {
                named.map(|x| ("method", format!("~{}", self.t(x)), None, x))
            }
            "property_declaration" => named.map(|x| ("property", self.t(x).to_owned(), None, x)),
            "event_declaration" => named.map(|x| ("event", self.t(x).to_owned(), None, x)),
            "indexer_declaration" => token("this").map(|x| ("indexer", "this".to_owned(), None, x)),
            "operator_declaration" => n
                .child_by_field_name("operator")
                .map(|x| ("operator", format!("operator{}", safe(self.t(x))), None, x)),
            "conversion_operator_declaration" => {
                let direction = token("implicit").or_else(|| token("explicit"));
                direction.map(|x| {
                    let ty = n
                        .child_by_field_name("type")
                        .map_or_else(String::new, |t| safe(self.t(t)));
                    (
                        "operator",
                        format!("operator-{}", self.t(x)),
                        Some(ty).filter(|t| !t.is_empty()),
                        x,
                    )
                })
            }
            _ => None,
        };
        let Some((kind, name, qualifier, name_node)) = resolved else {
            return self.hole(n);
        };
        let implements = kids
            .iter()
            .find(|c| c.kind() == "explicit_interface_specifier")
            .map(|c| squash(self.t(*c)).trim_end_matches('.').to_owned());
        let vis = if kind == "function" {
            "private"
        } else {
            visibility_of(&parts.modifiers, self.default_vis(), implements.is_some())
        };
        let body = self.body_nodes(&parts.body, depth)?;
        let id = self.declared(
            n,
            &parts,
            Decl {
                kind,
                name,
                qualifier,
                name_node,
                vis,
                implements,
                bases: Vec::new(),
            },
            body,
        )?;
        self.note_member_sites(id, n, kind);
        Ok(id)
    }

    /// One field, constant or event unit per declarator of `n`, each spanning the whole declaration.
    fn field_units(&mut self, n: Node<'_>) -> R<Vec<NodeId>> {
        let mut parts = self.split(n, &[]);
        let Some(vd) = parts
            .sig
            .iter()
            .copied()
            .find(|c| c.kind() == "variable_declaration")
        else {
            return Ok(vec![self.hole(n)?]);
        };
        parts.sig.retain(|c| c.id() != vd.id());
        let mut declarators = Vec::new();
        for c in children(vd) {
            match c.kind() {
                "variable_declarator" => declarators.push(c),
                "," => {}
                _ => parts.sig.push(c),
            }
        }
        let kind = if n.kind() == "event_field_declaration" {
            "event"
        } else if parts.modifiers.iter().any(|m| m == "const") {
            "const"
        } else {
            "field"
        };
        let vis = visibility_of(&parts.modifiers, self.default_vis(), false);
        let mut out = Vec::new();
        for d in declarators {
            let name_node = d
                .child_by_field_name("name")
                .or_else(|| children(d).into_iter().find(|c| c.kind() == "identifier"));
            let Some(name_node) = name_node else {
                out.push(self.hole(d)?);
                continue;
            };
            let rest: Vec<Node<'_>> = children(d)
                .into_iter()
                .filter(|c| c.id() != name_node.id())
                .collect();
            let body = self.body_nodes(&rest, MAX_DEPTH / 2)?;
            let name = self.t(name_node).to_owned();
            let id = self.declared(
                n,
                &parts,
                Decl {
                    kind,
                    name,
                    qualifier: None,
                    name_node,
                    vis,
                    implements: None,
                    bases: Vec::new(),
                },
                body,
            )?;
            if let Some(ty) = vd.child_by_field_name("type") {
                self.raw_fields.push((id, self.t(ty).to_owned()));
            }
            let mut calls = Vec::new();
            collect_calls(self.cx.text, d, &mut calls);
            self.raw_calls.extend(calls.into_iter().map(|c| (id, c)));
            out.push(id);
        }
        Ok(out)
    }

    fn variant_unit(&mut self, n: Node<'_>) -> R<NodeId> {
        let Some(name_node) = n.child_by_field_name("name") else {
            return self.hole(n);
        };
        let parts = self.split(n, &["value"]);
        let rest: Vec<Node<'_>> = parts
            .sig
            .iter()
            .chain(&parts.body)
            .copied()
            .filter(|c| c.id() != name_node.id())
            .collect();
        let body = self.body_nodes(&rest, MAX_DEPTH / 2)?;
        let name = self.t(name_node).to_owned();
        let mut bare = Parts::default();
        bare.attrs.clone_from(&parts.attrs);
        self.declared(
            n,
            &bare,
            Decl {
                kind: "variant",
                name,
                qualifier: None,
                name_node,
                vis: "public",
                implements: None,
                bases: Vec::new(),
            },
            body,
        )
    }
}

/// The naming, accessibility and heritage of one declaration.
struct Decl<'t> {
    kind: &'static str,
    name: String,
    qualifier: Option<String>,
    name_node: Node<'t>,
    vis: &'static str,
    implements: Option<String>,
    bases: Vec<String>,
}

// frob:ticket 01M44YQTCDPH87ASRMSJEN2C8Q

/// The local name a plain `using Ns;` binds: it brings every type of `Ns` into scope.
pub const USE_NAMESPACE: &str = "*";
/// The local name a `using static T;` binds: it brings every static member of `T` into scope.
pub const USE_STATIC: &str = "*static";
/// The call qualifier of an object creation (`new T(..)`), a call of `T`'s constructor.
pub const Q_NEW: &str = "new";
/// The call qualifier of `base.M(..)`.
pub const Q_BASE: &str = "base";
/// The call qualifier of a `: base(..)` constructor initializer.
pub const Q_BASE_INIT: &str = "base-init";
/// The call qualifier of a `: this(..)` constructor initializer.
pub const Q_THIS_INIT: &str = "this-init";
/// The modifier prefix marking an extension method; the rest is the first parameter's type.
pub const EXTENSION_PREFIX: &str = "extension=";

/// One call or object creation found in a member body.
#[derive(Debug, Clone)]
struct RawCall {
    callee: String,
    qualifier: Option<String>,
    method: bool,
    local: LocalBinding,
    receiver: Option<Receiver>,
    args: Option<usize>,
    qual_path: Vec<String>,
    line: u32,
    text: String,
}

/// One `using` directive and the namespace segments it sits in.
#[derive(Debug, Clone)]
struct RawUse {
    local: String,
    target: String,
    rendered: String,
    global: bool,
    ns: Vec<String>,
}

impl Fold<'_> {
    /// The namespace segments `n` declares (`namespace A.B` is `[A, B]`).
    fn ns_parts(&self, n: Node<'_>) -> Vec<String> {
        let Some(name) = n.child_by_field_name("name") else {
            return Vec::new();
        };
        let full = squash(self.t(name));
        full.strip_prefix("global::")
            .unwrap_or(&full)
            .split('.')
            .map(str::to_owned)
            .collect()
    }

    /// Records the directive `n` (`using`, `using static`, alias, `global using`).
    fn using(&mut self, n: Node<'_>) {
        let alias = n.child_by_field_name("name");
        let kids = children(n);
        let has = |k: &str| kids.iter().any(|c| !c.is_named() && c.kind() == k);
        let (is_static, global) = (has("static"), has("global"));
        let Some(target) = kids
            .iter()
            .rev()
            .find(|c| c.is_named() && !is_comment(**c) && alias.is_none_or(|a| a.id() != c.id()))
        else {
            tracing::debug!(path = self.path, "using directive without a target");
            return;
        };
        let written = squash(self.t(*target));
        let target = strip_generics(written.strip_prefix("global::").unwrap_or(&written));
        let (local, rendered) = match (alias, is_static) {
            (Some(a), _) => {
                let a = self.t(a).to_owned();
                let r = format!("{a} = {target}");
                (a, r)
            }
            (None, true) => (USE_STATIC.to_owned(), format!("static {target}")),
            (None, false) => (USE_NAMESPACE.to_owned(), target.clone()),
        };
        tracing::trace!(path = self.path, %local, %target, global, "csharp using");
        self.raw_uses.push(RawUse {
            local,
            target,
            rendered,
            global,
            ns: self.ns.clone(),
        });
    }

    /// Notes the calls, declared type and extension-ness of the member unit `id` built from `n`.
    fn note_member_sites(&mut self, id: NodeId, n: Node<'_>, kind: &str) {
        let mut calls = Vec::new();
        collect_calls(self.cx.text, n, &mut calls);
        self.raw_calls.extend(calls.into_iter().map(|c| (id, c)));
        if kind == "property"
            && let Some(ty) = n.child_by_field_name("type")
        {
            self.raw_fields.push((id, self.t(ty).to_owned()));
        }
        if kind == "method"
            && let Some(first) = n
                .child_by_field_name("parameters")
                .and_then(|p| children(p).into_iter().find(|c| c.kind() == "parameter"))
            && children(first)
                .iter()
                .any(|c| matches!(c.kind(), "this" | "modifier") && self.t(*c) == "this")
            && let Some(ty) = first
                .child_by_field_name("type")
                .and_then(|t| type_head(self.cx.text, t))
            && let Some(f) = self.facts.get_mut(&id)
        {
            f.modifiers.push(format!("{EXTENSION_PREFIX}{ty}"));
        }
    }
}

/// `text` without any `<..>` generic argument list.
fn strip_generics(text: &str) -> String {
    let mut depth = 0usize;
    let mut out = String::new();
    for c in text.chars() {
        match c {
            '<' => depth += 1,
            '>' => depth = depth.saturating_sub(1),
            c if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}

/// The simple type name of the type node `n` (`List<int>` is `List`, `A.B?` is `B`), `None` for arrays and tuples.
fn type_head(text: &str, n: Node<'_>) -> Option<String> {
    match n.kind() {
        "identifier" | "predefined_type" => Some(text_of(text, n).to_owned()),
        "generic_name" => children(n)
            .into_iter()
            .find(|c| c.kind() == "identifier")
            .map(|c| text_of(text, c).to_owned()),
        "qualified_name" => n
            .child_by_field_name("name")
            .and_then(|c| type_head(text, c)),
        "nullable_type" | "alias_qualified_name" => children(n)
            .into_iter()
            .rev()
            .find(Node::is_named)
            .and_then(|c| type_head(text, c)),
        _ => None,
    }
}

/// The dotted name segments of a name expression (`A.B.C`, `string`), `None` for anything else.
fn name_chain(text: &str, n: Node<'_>) -> Option<Vec<String>> {
    match n.kind() {
        "identifier" | "predefined_type" | "generic_name" => type_head(text, n).map(|h| vec![h]),
        "qualified_name" => {
            let mut q = name_chain(text, n.child_by_field_name("qualifier")?)?;
            q.extend(name_chain(text, n.child_by_field_name("name")?)?);
            Some(q)
        }
        "member_access_expression" => {
            let mut q = name_chain(text, n.child_by_field_name("expression")?)?;
            q.extend(name_chain(text, n.child_by_field_name("name")?)?);
            Some(q)
        }
        "alias_qualified_name" => name_chain(text, n.child_by_field_name("name")?),
        _ => None,
    }
}

/// The names declared in the member `n` with their explicit type head (`None` for `var` and untyped names).
fn collect_locals(text: &str, n: Node<'_>) -> HashMap<String, Option<String>> {
    let mut out: HashMap<String, Option<String>> = HashMap::new();
    let mut put = |name: &str, ty: Option<String>| {
        out.entry(name.to_owned())
            .and_modify(|t| {
                if *t != ty {
                    *t = None;
                }
            })
            .or_insert(ty);
    };
    let mut stack = vec![n];
    while let Some(x) = stack.pop() {
        match x.kind() {
            "parameter" | "catch_declaration" | "foreach_statement" | "declaration_pattern" => {
                let name = x.child_by_field_name("name").or_else(|| {
                    x.child_by_field_name("left")
                        .filter(|l| l.kind() == "identifier")
                });
                if let Some(name) = name {
                    let ty = x
                        .child_by_field_name("type")
                        .and_then(|t| type_head(text, t))
                        .filter(|t| t != "var");
                    put(text_of(text, name), ty);
                }
            }
            "variable_declaration" => {
                let ty = x
                    .child_by_field_name("type")
                    .and_then(|t| type_head(text, t))
                    .filter(|t| t != "var");
                for d in children(x)
                    .into_iter()
                    .filter(|c| c.kind() == "variable_declarator")
                {
                    let Some(name) = d
                        .child_by_field_name("name")
                        .or_else(|| children(d).into_iter().find(|c| c.kind() == "identifier"))
                    else {
                        continue;
                    };
                    let inferred = ty.clone().or_else(|| {
                        children(d)
                            .into_iter()
                            .find(|c| c.kind() == "object_creation_expression")
                            .and_then(|o| o.child_by_field_name("type"))
                            .and_then(|t| type_head(text, t))
                    });
                    put(text_of(text, name), inferred);
                }
            }
            "single_variable_designation" | "implicit_parameter" => {
                put(text_of(text, x), None);
            }
            _ => {}
        }
        stack.extend(children(x));
    }
    out
}

/// The receiver of a call on `expr`: `this`, a typed local, `new T()`, a string literal, else unknown.
fn receiver_of(
    text: &str,
    expr: Node<'_>,
    locals: &HashMap<String, Option<String>>,
) -> (Option<String>, Option<Receiver>, Vec<String>) {
    match expr.kind() {
        "this_expression" | "this" => (None, Some(Receiver::SelfValue), Vec::new()),
        "base_expression" | "base" => (Some(Q_BASE.to_owned()), None, Vec::new()),
        "string_literal" | "interpolated_string_expression" | "verbatim_string_literal" => {
            (None, Some(Receiver::Typed("string".to_owned())), Vec::new())
        }
        "object_creation_expression" => {
            let ty = expr
                .child_by_field_name("type")
                .and_then(|t| type_head(text, t));
            (
                None,
                Some(ty.map_or(Receiver::Expr, Receiver::Typed)),
                Vec::new(),
            )
        }
        _ => match name_chain(text, expr) {
            Some(chain) if chain.len() == 1 && locals.contains_key(&chain[0]) => {
                let r = locals[&chain[0]]
                    .clone()
                    .map_or(Receiver::Expr, Receiver::Typed);
                (None, Some(r), Vec::new())
            }
            Some(chain) if locals.contains_key(&chain[0]) => {
                (None, Some(Receiver::Expr), Vec::new())
            }
            Some(chain) => (None, None, chain),
            None => (None, Some(Receiver::Expr), Vec::new()),
        },
    }
}

/// The number of arguments in `args`, an `argument_list`.
fn arg_count(args: Option<Node<'_>>) -> Option<usize> {
    args.map(|a| {
        children(a)
            .iter()
            .filter(|c| c.kind() == "argument")
            .count()
    })
}

/// The call expression text, whitespace collapsed and capped.
fn site_text(text: &str, n: Node<'_>) -> String {
    let mut t = collapse_ws(text_of(text, n));
    if t.len() > 96 {
        let mut cut = 96;
        while !t.is_char_boundary(cut) {
            cut -= 1;
        }
        t.truncate(cut);
    }
    t
}

/// Every invocation, object creation and constructor initializer under member `n`, local functions excluded.
fn collect_calls(text: &str, n: Node<'_>, out: &mut Vec<RawCall>) {
    let locals = collect_locals(text, n);
    let mut stack: Vec<Node<'_>> = children(n);
    stack.reverse();
    while let Some(x) = stack.pop() {
        if matches!(x.kind(), "attribute_list" | "local_function_statement") {
            continue;
        }
        let line = u32::try_from(x.start_position().row + 1).unwrap_or(u32::MAX);
        let blank = |callee: String| RawCall {
            callee,
            qualifier: None,
            method: false,
            local: LocalBinding::None,
            receiver: None,
            args: None,
            qual_path: Vec::new(),
            line,
            text: site_text(text, x),
        };
        match x.kind() {
            "invocation_expression" => {
                if let Some(f) = x.child_by_field_name("function") {
                    let args = arg_count(x.child_by_field_name("arguments"));
                    if let Some(c) = invocation(text, x, f, args, &locals, blank(String::new())) {
                        out.push(c);
                    }
                }
            }
            "object_creation_expression" => {
                let chain = x
                    .child_by_field_name("type")
                    .and_then(|t| name_chain(text, t))
                    .unwrap_or_default();
                let mut c = blank(chain.last().cloned().unwrap_or_default());
                c.qualifier = Some(Q_NEW.to_owned());
                c.args = arg_count(x.child_by_field_name("arguments"));
                c.qual_path = chain[..chain.len().saturating_sub(1)].to_vec();
                out.push(c);
            }
            "implicit_object_creation_expression" => {
                let mut c = blank(String::new());
                c.qualifier = Some(Q_NEW.to_owned());
                out.push(c);
            }
            "constructor_initializer" => {
                let base = children(x).iter().any(|c| c.kind() == "base");
                let mut c = blank(if base { "base" } else { "this" }.to_owned());
                c.qualifier = Some(if base { Q_BASE_INIT } else { Q_THIS_INIT }.to_owned());
                c.args = arg_count(
                    children(x)
                        .into_iter()
                        .find(|c| c.kind() == "argument_list"),
                );
                out.push(c);
            }
            _ => {}
        }
        let mut kids = children(x);
        kids.reverse();
        stack.extend(kids);
    }
}

/// The call of invocation `x` whose callee expression is `f`, folded onto `site`.
fn invocation(
    text: &str,
    inv: Node<'_>,
    func: Node<'_>,
    args: Option<usize>,
    locals: &HashMap<String, Option<String>>,
    mut site: RawCall,
) -> Option<RawCall> {
    site.args = args;
    match func.kind() {
        "identifier" | "generic_name" => {
            let name = type_head(text, func)?;
            if name == "nameof" {
                return None;
            }
            if locals.contains_key(&name) {
                site.local = LocalBinding::Value;
            }
            site.callee = name;
        }
        "member_access_expression" | "member_binding_expression" => {
            site.callee = func
                .child_by_field_name("name")
                .and_then(|c| type_head(text, c))?;
            let recv_expr = if func.kind() == "member_access_expression" {
                func.child_by_field_name("expression")
            } else {
                inv.parent()
                    .filter(|p| p.kind() == "conditional_access_expression")
                    .and_then(|p| p.child_by_field_name("condition"))
            };
            if let Some(expr) = recv_expr {
                let (qualifier, receiver, path) = receiver_of(text, expr, locals);
                site.qualifier = qualifier;
                site.method = path.is_empty();
                site.receiver = receiver;
                site.qual_path = path;
            } else {
                site.method = true;
                site.receiver = Some(Receiver::Expr);
            }
            if site.qualifier.as_deref() == Some(Q_BASE) {
                site.method = true;
            }
        }
        _ => {
            site.method = true;
            site.receiver = Some(Receiver::Expr);
        }
    }
    Some(site)
}

/// Fills `file` with the calls, imports, use bindings and field declarations the fold gathered.
fn file_sites(
    file: &mut crate::model::FileSymbols,
    by_node: &HashMap<NodeId, Symref>,
    calls: Vec<(NodeId, RawCall)>,
    uses: Vec<RawUse>,
    fields: Vec<(NodeId, String)>,
) {
    for (node, c) in calls {
        let Some(caller) = by_node.get(&node) else {
            continue;
        };
        file.calls.push(CallSite {
            caller: caller.clone(),
            callee: c.callee,
            qualifier: c.qualifier,
            method: c.method,
            local: c.local,
            in_macro: false,
            receiver: c.receiver,
            opaque_qualifier: false,
            macro_exact: None,
            args: c.args,
            qual_path: c.qual_path,
            bound: Vec::new(),
            line: c.line,
            text: c.text,
        });
    }
    for u in uses {
        file.imports.push(ImportEdge {
            from_file: file.path.clone(),
            target: if u.global {
                format!("global {}", u.rendered)
            } else {
                u.rendered
            },
        });
        file.uses.push(UseBinding {
            from_file: file.path.clone(),
            local: u.local,
            target: u.target,
            public: u.global,
            container: (!u.ns.is_empty()).then(|| Symref::symbol(&file.path, u.ns)),
        });
    }
    for (node, ty) in fields {
        let Some(sym) = by_node.get(&node) else {
            continue;
        };
        let owner = sym.segments()[..sym.segments().len() - 1].join(".");
        let head = strip_generics(&squash(&ty))
            .trim_end_matches('?')
            .to_owned();
        let head = head.rsplit('.').next().unwrap_or_default().to_owned();
        if let Some(field) = sym.name() {
            file.fields.push(FieldDecl {
                owner,
                field: field.to_owned(),
                ty: RetType {
                    head,
                    arg: None,
                    arg2: None,
                    tuple: None,
                },
            });
        }
    }
}
