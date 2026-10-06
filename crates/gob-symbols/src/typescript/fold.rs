//! The TypeScript and JavaScript folder: a tree-sitter tree to a U term plus the facts of one file.
//!
//! See the module docs of [`super`] for the mapping. This file holds the translation (`rho`); the
//! scoping helpers are in `binders`, the import wire form in `imports`.

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80

use std::collections::{HashMap, HashSet};

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, Sort, TermError, reserved};
use gob_languages::{Language, ParseLimits, ParseResult, UnresolvedReason, parse};
use tree_sitter::Node;

use super::binders::{is_module_binding, param_names, scope_binders};
use super::imports::{ImportMode, encode_edge, encode_use};
use super::{ATTR_JSX_ATTRS, ATTR_JSX_KIND, ATTR_JSX_LINE, ATTR_JSX_TAG};
use super::{ATTR_TEST_FRAMEWORK, ATTR_TEST_LINE, ATTR_TEST_ROLE, ATTR_TEST_TITLE};
use crate::adapter::{FileInput, FoldError, Folded};
use crate::fold::{
    Cx, base_file, call_text, children, failed_file, file_root_spec, leaves, line_of,
    local_binding, text_of,
};
use crate::model::{
    CallSite, FileSymbols, ImportEdge, Receiver, RefKind, RefSite, UseBinding, collapse_ws,
};
use crate::symref::Symref;
use crate::view::{self, ATTR_VISIBILITY, HOLE_MISSING, HOLE_PARSE_ERROR, HOLE_UNMODELLED, Naming};

/// Deepest term nesting before a subtree collapses into one opaque node.
const MAX_DEPTH: usize = 160;

type R<T> = Result<T, TermError>;

/// The adapter operator language tag.
const LANG: &str = "typescript";

/// Longest module-expression text kept in an `Unknown` import edge.
const MAX_SPEC_TEXT: usize = 80;

/// Declaration kinds a `JSDoc` comment may document.
const DOCUMENTABLE: [&str; 15] = [
    "function_declaration",
    "generator_function_declaration",
    "class_declaration",
    "abstract_class_declaration",
    "interface_declaration",
    "type_alias_declaration",
    "enum_declaration",
    "internal_module",
    "export_statement",
    "lexical_declaration",
    "variable_declaration",
    "ambient_declaration",
    "method_definition",
    "public_field_definition",
    "field_definition",
];

/// Function-like expression kinds.
const FN_EXPR: [&str; 4] = [
    "arrow_function",
    "function_expression",
    "function",
    "generator_function",
];

/// Kinds under which a module reference runs only sometimes (a `require` there is May).
const CONDITIONAL: [&str; 10] = [
    "if_statement",
    "try_statement",
    "switch_statement",
    "ternary_expression",
    "binary_expression",
    "for_statement",
    "for_in_statement",
    "while_statement",
    "do_statement",
    "catch_clause",
];

/// Kinds whose identifiers are types and tokens, never value references.
const TYPE_KINDS: [&str; 6] = [
    "type_annotation",
    "type_arguments",
    "type_parameters",
    "type_alias_declaration",
    "interface_declaration",
    "ambient_declaration",
];

/// Modifiers a test-runner call may carry (`test.only`, `describe.serial`).
const TEST_MODIFIERS: [&str; 13] = [
    "only",
    "skip",
    "todo",
    "fails",
    "fixme",
    "slow",
    "concurrent",
    "sequential",
    "serial",
    "parallel",
    "describe",
    "runIf",
    "skipIf",
];

/// Packages whose `describe`, `it` and `test` are test-runner entry points, with the framework they name.
const TEST_PACKAGES: [(&str, &str); 5] = [
    ("vitest", "vitest"),
    ("@jest/globals", "jest"),
    ("@playwright/test", "playwright"),
    ("bun:test", "bun"),
    ("node:test", "node"),
];

/// The grammar for `path`, or `None` for a file the adapter does not claim.
pub(super) fn language_of(path: &str) -> Option<Language> {
    Language::detect(path).filter(|l| {
        matches!(
            l,
            Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
        )
    })
}

/// Parses `text` with the grammar of `input.path` and folds it.
pub(super) fn fold_source(text: &str, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let Some(lang) = language_of(input.path) else {
        return failed_file(input, LANG, UnresolvedReason::GrammarUnavailable);
    };
    match parse(lang, text, &ParseLimits::default()) {
        ParseResult::Parsed(t) => fold_tree(&t.text, t.root(), input),
        ParseResult::Unresolved(u) => failed_file(input, LANG, u.reason),
    }
}

/// One call or value reference found while folding, before it has a `Symref`.
struct Site {
    caller: usize,
    value: bool,
    name: String,
    qualifier: Option<String>,
    method: bool,
    receiver: Option<Receiver>,
    node: Option<NodeId>,
    args: usize,
    qual_path: Vec<String>,
    line: u32,
    text: String,
}

/// An import or export binding waiting for its container's `Symref`.
struct PendingUse {
    container: Option<usize>,
    local: String,
    target: String,
    public: bool,
}

/// What a call's function expression is, read from the syntax alone.
struct CallTarget {
    name: String,
    qualifier: Option<String>,
    method: bool,
    dynamic: bool,
    receiver: Option<Receiver>,
    path: Vec<String>,
}

/// The kind of an enclosing unit, innermost last.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Ctx {
    Class,
    Function,
    Namespace,
    /// The value of a module-level constant: calls are its own, a `require` there still runs at load time.
    Value,
}

/// A `JSDoc` comment waiting for the declaration it documents.
struct PendingDoc {
    text: String,
    start: usize,
    end: usize,
}

/// The names a file exports under another name or through a CJS assignment (found before folding).
#[derive(Default)]
struct ExportScan {
    /// Local names that are exported: their units are public.
    names: HashSet<String>,
    /// `(exported, local)` pairs: the name a file exports and the local name it stands for.
    aliases: Vec<(String, String)>,
}

/// A test-runner call recognised from its callee shape.
struct TestCall {
    role: &'static str,
    framework: String,
    title: String,
}

#[allow(
    clippy::struct_excessive_bools,
    reason = "independent one-shot flags of one fold pass"
)]
struct Fold<'a> {
    cx: Cx<'a>,
    path: &'a str,
    /// Identifiers are references (expression context) rather than tokens.
    expr: bool,
    ord_nodes: Vec<Option<NodeId>>,
    /// Enclosing units, innermost last: (ordinal, kind).
    units: Vec<(usize, Ctx)>,
    /// Binder names of the enclosing scopes (file, functions), innermost last.
    bound: Vec<HashSet<String>>,
    sites: Vec<Site>,
    uses: Vec<PendingUse>,
    edges: Vec<String>,
    exports: ExportScan,
    /// Set by an `export` statement for the declaration it wraps: the statement's span.
    export: Option<(usize, usize)>,
    /// True while the next node is a direct child statement of a module or namespace body.
    direct: bool,
    /// True while translating `export default`: an anonymous unit is named `default`.
    default_export: bool,
    pending_doc: Option<PendingDoc>,
    leftover_doc: Option<PendingDoc>,
    /// Depth of enclosing conditional constructs and function bodies.
    cond_depth: usize,
    /// Test-runner names bound by an import, with the framework.
    test_names: HashMap<String, String>,
    is_test_file: bool,
}

/// Ids of the module-level declarators that become units (a plain identifier name).
fn unit_declarators(stmts: &[Node<'_>], text: &str) -> HashSet<usize> {
    let mut out = HashSet::new();
    for s in stmts {
        let decl = if s.kind() == "export_statement" {
            s.child_by_field_name("declaration")
        } else {
            Some(*s)
        };
        let Some(d) =
            decl.filter(|d| matches!(d.kind(), "lexical_declaration" | "variable_declaration"))
        else {
            continue;
        };
        for c in children(d) {
            if c.kind() == "variable_declarator"
                && !is_module_binding(c, text)
                && c.child_by_field_name("name")
                    .is_some_and(|n| n.kind() == "identifier")
            {
                out.insert(c.id());
            }
        }
    }
    out
}

/// The text of a string literal node (or a template literal without substitutions), unquoted.
fn string_value(text: &str, n: Node<'_>) -> Option<String> {
    let raw = text_of(text, n);
    match n.kind() {
        "string" => {
            let q = raw.chars().next()?;
            let inner = raw.get(1..raw.len().saturating_sub(1))?;
            (matches!(q, '"' | '\'') && raw.len() >= 2 && raw.ends_with(q))
                .then(|| inner.to_owned())
        }
        "template_string" => {
            if children(n)
                .iter()
                .any(|c| c.kind() == "template_substitution")
            {
                return None;
            }
            raw.strip_prefix('`')
                .and_then(|r| r.strip_suffix('`'))
                .map(str::to_owned)
        }
        _ => None,
    }
}

fn is_comment(n: Node<'_>) -> bool {
    n.kind() == "comment"
}

/// True for a `/** ... */` comment.
fn is_jsdoc(text: &str, n: Node<'_>) -> bool {
    is_comment(n) && text_of(text, n).starts_with("/**")
}

/// A `JSDoc` body without its comment markers, lines trimmed.
fn doc_text(raw: &str) -> String {
    let body = raw
        .trim_start_matches("/**")
        .trim_end_matches("*/")
        .lines()
        .map(|l| l.trim().trim_start_matches('*').trim())
        .filter(|l| !l.is_empty())
        .collect::<Vec<_>>();
    body.join("\n")
}

/// A symref-safe unit name for a property name as written.
fn unit_name(raw: &str) -> String {
    let raw = raw.trim().trim_matches(|c| c == '"' || c == '\'');
    let mapped: String = raw
        .chars()
        .map(|c| match c {
            '#' => '$',
            c if c.is_alphanumeric() || matches!(c, '_' | '$' | '-') => c,
            _ => '_',
        })
        .collect();
    if mapped.is_empty() {
        "$anon".to_owned()
    } else {
        mapped
    }
}

/// True when `child` is the declaring (binding) identifier of `parent`, not a reference.
fn is_decl_ident(parent: Node<'_>, child: Node<'_>) -> bool {
    let is = |field: &str| {
        parent
            .child_by_field_name(field)
            .is_some_and(|x| x.id() == child.id())
    };
    match parent.kind() {
        "variable_declarator"
        | "function_declaration"
        | "generator_function_declaration"
        | "function_expression"
        | "function"
        | "generator_function"
        | "class_declaration"
        | "abstract_class_declaration"
        | "class" => is("name"),
        "required_parameter" | "optional_parameter" => is("pattern"),
        "formal_parameters"
        | "array_pattern"
        | "rest_pattern"
        | "object_pattern"
        | "import_specifier"
        | "export_specifier"
        | "namespace_import"
        | "import_clause"
        | "namespace_export"
        | "import_require_clause" => true,
        "assignment_pattern" => is("left"),
        "pair_pattern" => is("value"),
        "arrow_function" | "catch_clause" => is("parameter"),
        "for_in_statement" => parent.child_by_field_name("kind").is_some() && is("left"),
        _ => false,
    }
}

/// The export aliases and exported local names of the program `root`, before folding.
fn scan_exports(root: Node<'_>, text: &str) -> ExportScan {
    let mut scan = ExportScan::default();
    let alias = |scan: &mut ExportScan, exported: &str, local: &str| {
        scan.names.insert(local.to_owned());
        // Kept even when the names agree: `export { v }` may re-export an import of this file.
        scan.aliases.push((exported.to_owned(), local.to_owned()));
    };
    for stmt in children(root) {
        match stmt.kind() {
            "export_statement" if stmt.child_by_field_name("source").is_none() => {
                let clause = children(stmt)
                    .into_iter()
                    .find(|c| c.kind() == "export_clause");
                if let Some(clause) = clause {
                    for sp in children(clause)
                        .into_iter()
                        .filter(|c| c.kind() == "export_specifier")
                    {
                        let Some(name) = sp.child_by_field_name("name") else {
                            continue;
                        };
                        let local = text_of(text, name);
                        let exported = sp
                            .child_by_field_name("alias")
                            .map_or(local, |a| text_of(text, a));
                        alias(&mut scan, exported, local);
                    }
                } else if children(stmt).iter().any(|c| c.kind() == "default") {
                    if let Some(d) = stmt.child_by_field_name("declaration")
                        && let Some(n) = d.child_by_field_name("name")
                    {
                        alias(&mut scan, "default", text_of(text, n));
                    } else if let Some(v) = stmt.child_by_field_name("value")
                        && v.kind() == "identifier"
                    {
                        alias(&mut scan, "default", text_of(text, v));
                    }
                }
            }
            "expression_statement" => {
                let Some(assign) = children(stmt)
                    .into_iter()
                    .find(|c| c.kind() == "assignment_expression")
                else {
                    continue;
                };
                let (Some(lhs), Some(rhs)) = (
                    assign.child_by_field_name("left"),
                    assign.child_by_field_name("right"),
                ) else {
                    continue;
                };
                let lt: String = text_of(text, lhs).split_whitespace().collect();
                if lt == "module.exports" {
                    match rhs.kind() {
                        "identifier" => alias(&mut scan, "default", text_of(text, rhs)),
                        "object" => {
                            for pair in children(rhs) {
                                match pair.kind() {
                                    "shorthand_property_identifier" => {
                                        scan.names.insert(text_of(text, pair).to_owned());
                                    }
                                    "pair" => {
                                        let (Some(key), Some(val)) = (
                                            pair.child_by_field_name("key"),
                                            pair.child_by_field_name("value"),
                                        ) else {
                                            continue;
                                        };
                                        if val.kind() == "identifier" {
                                            let key = text_of(text, key).trim_matches(['"', '\'']);
                                            alias(&mut scan, key, text_of(text, val));
                                        }
                                    }
                                    _ => {}
                                }
                            }
                        }
                        _ => {}
                    }
                } else if lhs.kind() == "member_expression"
                    && let (Some(obj), Some(prop)) = (
                        lhs.child_by_field_name("object"),
                        lhs.child_by_field_name("property"),
                    )
                {
                    let ot: String = text_of(text, obj).split_whitespace().collect();
                    if (ot == "exports" || ot == "module.exports") && rhs.kind() == "identifier" {
                        alias(&mut scan, text_of(text, prop), text_of(text, rhs));
                    }
                }
            }
            _ => {}
        }
    }
    scan
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let exports = scan_exports(root, text);
    let mut f = Fold {
        cx: Cx::new(input.path, LANG, text),
        path: input.path,
        expr: true,
        ord_nodes: vec![None],
        units: Vec::new(),
        bound: Vec::new(),
        sites: Vec::new(),
        uses: Vec::new(),
        edges: Vec::new(),
        exports,
        export: None,
        direct: false,
        default_export: false,
        pending_doc: None,
        leftover_doc: None,
        cond_depth: 0,
        test_names: HashMap::new(),
        is_test_file: super::is_typescript_test_file(input.path),
    };
    let stmts: Vec<Node<'_>> = children(root);
    let skip = unit_declarators(&stmts, text);
    let names = scope_binders(Vec::new(), &stmts, text, &skip);
    f.bound.push(names.iter().cloned().collect());
    let kids = f.seq(&stmts, 1, true)?;
    let refs: Vec<&str> = names.iter().map(String::as_str).collect();
    let spec = file_root_spec(&f.cx, input.size as usize).binders(&refs);
    let root_id = f.cx.add(spec, &kids)?;
    f.ord_nodes[0] = Some(root_id);
    let Fold {
        cx,
        ord_nodes,
        sites,
        uses,
        edges,
        exports,
        ..
    } = f;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::TypeScript);
    let mut file = base_file(input, LANG);
    file.fidelity = super::FIDELITY;
    file.parse_status = view::parse_status_of(&term);
    let symref_of = |ord: usize| -> Option<Symref> {
        ord_nodes
            .get(ord)
            .copied()
            .flatten()
            .and_then(|n| v.by_node.get(&n).cloned())
    };
    for target in edges {
        file.imports.push(ImportEdge {
            from_file: input.path.to_owned(),
            target,
        });
    }
    for u in uses {
        file.uses.push(UseBinding {
            from_file: input.path.to_owned(),
            local: u.local,
            target: u.target,
            public: u.public,
            container: u.container.and_then(symref_of),
        });
    }
    for (exported, local) in exports.aliases {
        file.uses.push(UseBinding {
            from_file: input.path.to_owned(),
            local: exported,
            target: encode_use(ImportMode::Static, "", &local),
            public: true,
            container: None,
        });
    }
    for site in sites {
        if let Some(caller) = symref_of(site.caller) {
            push_site(&mut file, &scopes, site, caller);
        }
    }
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        calls = file.calls.len(),
        refs = file.refs.len(),
        imports = file.imports.len(),
        status = ?file.parse_status,
        "typescript file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// Files `s` (found in `caller`) as a call or a value reference of `file`.
fn push_site(file: &mut FileSymbols, scopes: &ScopeGraph, s: Site, caller: Symref) {
    if s.value {
        file.refs.push(RefSite {
            from: caller,
            name: s.name,
            qualifier: None,
            kind: RefKind::Value,
        });
        return;
    }
    let local = local_binding(scopes, s.node, false);
    file.calls.push(CallSite {
        caller,
        callee: s.name,
        qualifier: s.qualifier,
        method: s.method,
        local,
        in_macro: false,
        receiver: s.receiver,
        opaque_qualifier: false,
        macro_exact: None,
        args: Some(s.args),
        qual_path: s.qual_path,
        bound: Vec::new(),
        line: s.line,
        text: s.text,
    });
}

/// The root of a member chain.
enum Root {
    Ident(String),
    This,
    Super,
    Other,
}

/// Everything `make_unit` needs besides the children.
struct UnitHead<'n> {
    kind: &'static str,
    name: String,
    vis: &'static str,
    span: (usize, usize),
    decorators: Vec<Node<'n>>,
}

impl<'a> Fold<'a> {
    fn t(&self, n: Node<'_>) -> &'a str {
        text_of(self.cx.text, n)
    }

    fn alloc(&mut self) -> usize {
        self.ord_nodes.push(None);
        self.ord_nodes.len() - 1
    }

    fn with_expr<T>(&mut self, on: bool, f: impl FnOnce(&mut Self) -> T) -> T {
        let saved = std::mem::replace(&mut self.expr, on);
        let out = f(self);
        self.expr = saved;
        out
    }

    /// The ordinal of the unit calls are attributed to (0, the file, outside any unit).
    fn caller(&self) -> usize {
        self.units.last().map_or(0, |u| u.0)
    }

    fn is_bound(&self, name: &str) -> bool {
        self.bound.iter().any(|s| s.contains(name))
    }

    /// True at the file level or directly inside a namespace: declarations there are units.
    fn at_module_level(&self) -> bool {
        self.units.last().is_none_or(|u| u.1 == Ctx::Namespace)
    }

    /// True when a `require` here runs unconditionally at load time.
    fn cjs_static(&self) -> bool {
        self.units
            .iter()
            .all(|u| matches!(u.1, Ctx::Namespace | Ctx::Value))
            && self.cond_depth == 0
    }

    // ---- statements and docs ----

    /// Translates `stmts` in order; a `/** */` comment right before a declaration becomes its doc.
    fn seq(&mut self, stmts: &[Node<'_>], depth: usize, direct: bool) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        let mut i = 0;
        while i < stmts.len() {
            let s = stmts[i];
            let documents_next = is_jsdoc(self.cx.text, s)
                && stmts.get(i + 1).is_some_and(|nx| {
                    DOCUMENTABLE.contains(&nx.kind())
                        && self.cx.text[s.end_byte()..nx.start_byte()]
                            .chars()
                            .all(char::is_whitespace)
                });
            if documents_next {
                self.pending_doc = Some(PendingDoc {
                    text: doc_text(self.t(s)),
                    start: s.start_byte(),
                    end: s.end_byte(),
                });
                i += 1;
                continue;
            }
            self.direct = direct;
            let id = self.tr(s, depth)?;
            self.direct = false;
            if let Some(d) = self.leftover_doc.take().or_else(|| self.pending_doc.take()) {
                let c = self.cx.add(
                    NodeSpec::new(Operator::comment(&d.text), self.cx.loc(d.start, d.end)),
                    &[],
                )?;
                out.push(c);
            }
            out.push(id);
            i += 1;
        }
        Ok(out)
    }

    /// The doc attribute for the declaration being translated, if a `JSDoc` comment precedes it.
    fn take_doc(&mut self) -> R<Option<NodeId>> {
        let Some(d) = self.pending_doc.take() else {
            return Ok(None);
        };
        let loc = self.cx.loc(d.start, d.end);
        let payload = self.cx.add(
            NodeSpec::new(Operator::lit("str", &d.text), loc.clone()),
            &[],
        )?;
        Ok(Some(self.cx.add(
            NodeSpec::new(Operator::attr("doc"), loc),
            &[payload],
        )?))
    }

    /// The span of the `export` statement wrapping the declaration being translated, once.
    fn take_export(&mut self) -> Option<(usize, usize)> {
        self.export.take()
    }

    // ---- generic translation ----

    fn hole(&mut self, n: Node<'_>) -> R<NodeId> {
        let kind = if n.is_missing() {
            HOLE_MISSING
        } else {
            HOLE_PARSE_ERROR
        };
        tracing::debug!(
            path = self.path,
            kind,
            at = n.start_byte(),
            "typescript hole"
        );
        self.cx.op(Operator::hole(kind), n, &[])
    }

    fn collapse(&mut self, nodes: &[Node<'_>]) -> R<NodeId> {
        let mut toks: Vec<&str> = Vec::new();
        for n in nodes {
            for l in leaves(*n, is_comment) {
                toks.push(self.t(l));
            }
            self.scan_calls(*n);
        }
        let (start, end) = nodes
            .first()
            .zip(nodes.last())
            .map_or((0, 0), |(a, b)| (a.start_byte(), b.end_byte()));
        tracing::debug!(
            path = self.path,
            start,
            end,
            "depth limit: subtree collapsed"
        );
        let spec = NodeSpec::new(
            Operator::opaque("depth-limit", toks.join(" ").as_bytes()),
            self.cx.loc(start, end),
        );
        self.cx.add(spec, &[])
    }

    /// Records the calls inside `root` without building term nodes (collapsed subtrees, decorators, defaults).
    fn scan_calls(&mut self, root: Node<'_>) {
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            match n.kind() {
                "call_expression" => {
                    if let Some(f) = n.child_by_field_name("function")
                        && (f.kind() == "import" || self.is_require(f))
                    {
                        let (mode, spec) = self.module_ref(n, f.kind() == "import");
                        self.edges.push(encode_edge(mode, &spec));
                    } else {
                        self.record_call(n, None);
                    }
                }
                "new_expression" => self.record_call(n, None),
                _ => {}
            }
            stack.extend(children(n));
        }
    }

    fn tr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let direct = std::mem::take(&mut self.direct);
        let incoming = self.pending_doc.take();
        if let Some(d) = incoming {
            if DOCUMENTABLE.contains(&n.kind()) {
                self.pending_doc = Some(d);
            } else {
                self.leftover_doc = Some(d);
            }
        }
        let cond = CONDITIONAL.contains(&n.kind());
        if cond {
            self.cond_depth += 1;
        }
        let out = self.tr_inner(n, depth, direct);
        if cond {
            self.cond_depth -= 1;
        }
        if let Some(d) = self.pending_doc.take() {
            self.leftover_doc = Some(d);
        }
        out
    }

    fn tr_inner(&mut self, n: Node<'_>, depth: usize, direct: bool) -> R<NodeId> {
        if depth > MAX_DEPTH {
            return self.collapse(&[n]);
        }
        if is_comment(n) {
            let text = self.t(n).to_owned();
            return self.cx.op(Operator::comment(&text), n, &[]);
        }
        if n.is_error() || n.is_missing() {
            return self.hole(n);
        }
        match n.kind() {
            "identifier" | "shorthand_property_identifier" if self.expr => {
                let name = self.t(n);
                self.cx.op(Operator::reference(name), n, &[])
            }
            "call_expression" if self.expr => self.call(n, depth),
            "new_expression" if self.expr => self.new_expr(n, depth),
            "member_expression" if self.expr => self.member(n, depth),
            "function_declaration" | "generator_function_declaration" => self.func_decl(n, depth),
            "class_declaration" | "abstract_class_declaration" => self.class_unit(n, depth),
            "interface_declaration" => self.simple_unit(n, "interface", depth),
            "type_alias_declaration" => self.simple_unit(n, "type", depth),
            "enum_declaration" => self.simple_unit(n, "enum", depth),
            "internal_module" => self.namespace_unit(n, depth),
            "export_statement" => self.export_stmt(n, depth, direct),
            "import_statement" => self.import_stmt(n),
            "lexical_declaration" | "variable_declaration" => self.var_decl(n, depth, direct),
            "method_definition"
                if self.units.last().is_some_and(|u| u.1 == Ctx::Class)
                    && n.parent().is_some_and(|p| p.kind() == "class_body") =>
            {
                self.method_unit(n, depth)
            }
            "public_field_definition" | "field_definition"
                if self.units.last().is_some_and(|u| u.1 == Ctx::Class) =>
            {
                self.field_member(n, depth)
            }
            k if FN_EXPR.contains(&k) || k == "method_definition" => self.anon_fn(n, depth),
            "class" if self.default_export => self.class_unit(n, depth),
            "jsx_element" | "jsx_self_closing_element" | "jsx_fragment" => self.jsx(n, depth),
            "jsx_expression" => self.jsx_expression(n, depth),
            "jsx_text" => self.cx.lit("text", self.t(n), n),
            "with_statement" => {
                let mut kids = self.gen_children(n, depth)?;
                kids.push(self.cx.op(Operator::hole(HOLE_UNMODELLED), n, &[])?);
                tracing::debug!(path = self.path, "typescript with statement is unmodelled");
                self.cx
                    .op(Operator::adapter(LANG, n.kind(), Sort::Exp), n, &kids)
            }
            "string" => self.cx.lit("string", self.t(n), n),
            k if TYPE_KINDS.contains(&k) => self.with_expr(false, |s| s.generic(n, depth)),
            _ => self.generic(n, depth),
        }
    }

    fn generic(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        if n.child_count() == 0 {
            return self.cx.lit(n.kind(), self.t(n), n);
        }
        let kids = self.gen_children(n, depth)?;
        self.cx
            .op(Operator::adapter(LANG, n.kind(), Sort::Exp), n, &kids)
    }

    fn gen_children(&mut self, n: Node<'_>, depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(n) {
            if c.kind() == "identifier" && is_decl_ident(n, c) {
                out.push(self.cx.lit("name", self.t(c), c)?);
            } else {
                out.push(self.tr(c, depth + 1)?);
            }
        }
        Ok(out)
    }

    /// `obj.name` in expression position: the object is an expression, the property a token.
    fn member(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        if let Some(o) = n.child_by_field_name("object") {
            kids.push(self.tr(o, depth + 1)?);
        }
        if let Some(p) = n.child_by_field_name("property") {
            kids.push(self.cx.lit("property", self.t(p), p)?);
        }
        self.cx.op(
            Operator::adapter(LANG, "member_expression", Sort::Exp),
            n,
            &kids,
        )
    }

    // ---- calls ----

    /// The head identifier or chain of `f`, unwrapping `!` and parentheses.
    fn chain(&self, f: Node<'_>) -> (Root, Vec<String>) {
        let mut names = Vec::new();
        let mut cur = f;
        loop {
            match cur.kind() {
                "member_expression" => {
                    let Some(p) = cur.child_by_field_name("property") else {
                        return (Root::Other, names);
                    };
                    names.push(self.t(p).to_owned());
                    let Some(o) = cur.child_by_field_name("object") else {
                        return (Root::Other, names);
                    };
                    cur = o;
                }
                "non_null_expression" | "parenthesized_expression" => {
                    let Some(i) = children(cur)
                        .into_iter()
                        .find(|c| c.is_named() && !is_comment(*c))
                    else {
                        return (Root::Other, names);
                    };
                    cur = i;
                }
                "identifier" => {
                    names.reverse();
                    return (Root::Ident(self.t(cur).to_owned()), names);
                }
                "this" => {
                    names.reverse();
                    return (Root::This, names);
                }
                "super" => {
                    names.reverse();
                    return (Root::Super, names);
                }
                _ => {
                    names.reverse();
                    return (Root::Other, names);
                }
            }
        }
    }

    fn call_target(&self, f: Node<'_>) -> CallTarget {
        let dynamic = || CallTarget {
            name: String::new(),
            qualifier: None,
            method: false,
            dynamic: true,
            receiver: None,
            path: Vec::new(),
        };
        let (root, names) = self.chain(f);
        let method_on = |name: String, receiver: Receiver| CallTarget {
            name,
            qualifier: None,
            method: true,
            dynamic: false,
            receiver: Some(receiver),
            path: Vec::new(),
        };
        match (root, names.as_slice()) {
            (Root::Ident(name), []) => CallTarget {
                name,
                qualifier: None,
                method: false,
                dynamic: false,
                receiver: None,
                path: Vec::new(),
            },
            (Root::This, [m]) => method_on(m.clone(), Receiver::SelfValue),
            (Root::This | Root::Super | Root::Other, [.., m]) => {
                method_on(m.clone(), Receiver::Expr)
            }
            (Root::Ident(head), [.., leaf]) => {
                if self.is_bound(&head) {
                    return method_on(leaf.clone(), Receiver::Expr);
                }
                let mut path = vec![head];
                path.extend(names[..names.len() - 1].iter().cloned());
                CallTarget {
                    name: leaf.clone(),
                    qualifier: path.last().cloned(),
                    method: false,
                    dynamic: false,
                    receiver: None,
                    path,
                }
            }
            _ => dynamic(),
        }
    }

    /// The callee node of a call or `new` expression.
    fn callee_of(n: Node<'_>) -> Option<Node<'_>> {
        n.child_by_field_name("function")
            .or_else(|| n.child_by_field_name("constructor"))
    }

    /// Records the call `n` (and the function values among its arguments) as sites of the current unit.
    fn record_call(&mut self, n: Node<'_>, node: Option<NodeId>) {
        let Some(f) = Self::callee_of(n) else {
            return;
        };
        let target = self.call_target(f);
        let caller = self.caller();
        let args = n.child_by_field_name("arguments");
        let arg_nodes: Vec<Node<'_>> = args
            .filter(|a| a.kind() == "arguments")
            .map(|a| {
                children(a)
                    .into_iter()
                    .filter(|c| c.is_named() && !is_comment(*c))
                    .collect()
            })
            .unwrap_or_default();
        for a in &arg_nodes {
            if a.kind() == "identifier" {
                self.value_site(*a);
            }
        }
        tracing::trace!(path = self.path, callee = %target.name, "typescript call");
        self.sites.push(Site {
            caller,
            value: false,
            name: target.name,
            qualifier: target.qualifier,
            method: target.method,
            receiver: target.receiver,
            node: node.filter(|_| !target.dynamic),
            args: arg_nodes.len(),
            qual_path: target.path,
            line: line_of(n),
            text: call_text(self.t(f)),
        });
    }

    /// Records the identifier `v`, used as a value, when it is not a local.
    fn value_site(&mut self, v: Node<'_>) {
        let name = self.t(v);
        if self.is_bound(name) {
            return;
        }
        let caller = self.caller();
        self.sites.push(Site {
            caller,
            value: true,
            name: name.to_owned(),
            qualifier: None,
            method: false,
            receiver: None,
            node: None,
            args: 0,
            qual_path: Vec::new(),
            line: line_of(v),
            text: String::new(),
        });
    }

    fn args_into(&mut self, n: Node<'_>, kids: &mut Vec<NodeId>, depth: usize) -> R<()> {
        if let Some(ta) = n.child_by_field_name("type_arguments") {
            kids.push(self.tr(ta, depth + 1)?);
        }
        if let Some(args) = n.child_by_field_name("arguments") {
            if args.kind() == "arguments" {
                for a in children(args) {
                    if a.is_named() {
                        kids.push(self.tr(a, depth + 1)?);
                    }
                }
            } else {
                kids.push(self.tr(args, depth + 1)?);
            }
        }
        Ok(())
    }

    /// The head and receiver children of a call to `target`.
    fn call_head(&mut self, f: Node<'_>, target: &CallTarget, depth: usize) -> R<Vec<NodeId>> {
        let mut kids = Vec::new();
        let head = if target.dynamic {
            self.tr(f, depth + 1)?
        } else if target.method {
            let name = format!(".{}", target.name);
            let field = f.child_by_field_name("property").unwrap_or(f);
            self.cx.op(Operator::reference(&name), field, &[])?
        } else {
            let text = collapse_ws(self.t(f));
            self.cx.op(Operator::reference(&text), f, &[])?
        };
        kids.push(head);
        if target.method
            && target.receiver == Some(Receiver::Expr)
            && let Some(obj) = f.child_by_field_name("object")
        {
            kids.push(self.tr(obj, depth + 1)?);
        }
        Ok(kids)
    }

    fn call(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(f) = n.child_by_field_name("function") else {
            return self.generic(n, depth);
        };
        if f.kind() == "import" || self.is_require(f) {
            return self.module_call(n, f, depth);
        }
        let target = self.call_target(f);
        let test = self.test_call(f, n, &target);
        let mut kids = self.call_head(f, &target, depth)?;
        self.args_into(n, &mut kids, depth)?;
        let kind = if target.method { "method" } else { "call" };
        let head = kids[0];
        self.record_call(n, Some(head));
        let mut spec = NodeSpec::new(Operator::apply(kind), self.cx.node_loc(n));
        if let Some(t) = test {
            tracing::trace!(path = self.path, role = t.role, title = %t.title, "test item");
            spec = spec
                .attr(ATTR_TEST_ROLE, t.role)
                .attr(ATTR_TEST_TITLE, t.title.as_str())
                .attr(ATTR_TEST_FRAMEWORK, t.framework.as_str())
                .attr(ATTR_TEST_LINE, i64::from(line_of(n)));
        }
        self.cx.add(spec, &kids)
    }

    fn new_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(f) = n.child_by_field_name("constructor") else {
            return self.generic(n, depth);
        };
        let target = self.call_target(f);
        let mut kids = self.call_head(f, &target, depth)?;
        self.args_into(n, &mut kids, depth)?;
        let head = kids[0];
        self.record_call(n, Some(head));
        self.cx.op(Operator::apply("new"), n, &kids)
    }

    // ---- test runners ----

    /// Recognises `describe("t", fn)`, `it("t", fn)`, `test.describe("t", fn)` and their modifiers.
    fn test_call(&self, f: Node<'_>, n: Node<'_>, target: &CallTarget) -> Option<TestCall> {
        if target.dynamic {
            return None;
        }
        let (Root::Ident(root), mods) = self.chain(f) else {
            return None;
        };
        if !matches!(root.as_str(), "describe" | "suite" | "it" | "test")
            || self.is_bound(&root)
            || !mods.iter().all(|m| TEST_MODIFIERS.contains(&m.as_str()))
        {
            return None;
        }
        let framework = self
            .test_names
            .get(&root)
            .cloned()
            .or_else(|| self.is_test_file.then(|| "globals".to_owned()))?;
        let args: Vec<Node<'_>> = n
            .child_by_field_name("arguments")?
            .named_children(&mut n.walk())
            .filter(|c| !is_comment(*c))
            .collect();
        let title = string_value(self.cx.text, *args.first()?)?;
        args.iter()
            .skip(1)
            .any(|a| FN_EXPR.contains(&a.kind()))
            .then_some(())?;
        let suite =
            matches!(root.as_str(), "describe" | "suite") || mods.iter().any(|m| m == "describe");
        Some(TestCall {
            role: if suite { "suite" } else { "case" },
            framework,
            title,
        })
    }

    // ---- imports ----

    fn push_use(&mut self, local: String, target: String, public: bool) {
        let container = self.units.last().map(|u| u.0);
        tracing::trace!(path = self.path, %local, %target, public, "typescript import binding");
        self.uses.push(PendingUse {
            container,
            local,
            target,
            public,
        });
    }

    fn is_require(&self, f: Node<'_>) -> bool {
        f.kind() == "identifier" && self.t(f) == "require" && !self.is_bound("require")
    }

    /// The mode and specifier (or expression text) of the module reference `call`.
    fn module_ref(&self, call: Node<'_>, dynamic: bool) -> (ImportMode, String) {
        let arg = call.child_by_field_name("arguments").and_then(|a| {
            children(a)
                .into_iter()
                .find(|c| c.is_named() && !is_comment(*c))
        });
        if let Some(spec) = arg.and_then(|a| string_value(self.cx.text, a)) {
            let mode = if dynamic || !self.cjs_static() {
                ImportMode::May
            } else {
                ImportMode::Static
            };
            (mode, spec)
        } else {
            let mut text = collapse_ws(self.t(call));
            if text.chars().count() > MAX_SPEC_TEXT {
                text = text.chars().take(MAX_SPEC_TEXT).collect();
                text.push_str("...");
            }
            (ImportMode::Unknown, text)
        }
    }

    /// `import(..)` or `require(..)`: an import edge, never a call.
    fn module_call(&mut self, n: Node<'_>, f: Node<'_>, depth: usize) -> R<NodeId> {
        let dynamic = f.kind() == "import";
        let (mode, spec) = self.module_ref(n, dynamic);
        tracing::debug!(path = self.path, ?mode, %spec, dynamic, "typescript module reference");
        self.edges.push(encode_edge(mode, &spec));
        let kind = if dynamic { "import" } else { "require" };
        let head = self.cx.lit("keyword", kind, f)?;
        let mut kids = vec![head];
        self.args_into(n, &mut kids, depth)?;
        self.cx.op(Operator::apply(kind), n, &kids)
    }

    /// Records the bindings of `const x = require("m")`, `const { a } = require("m")` and `await import("m")`.
    fn bind_require(&mut self, d: Node<'_>) {
        let (Some(name), Some(mut value)) = (
            d.child_by_field_name("name"),
            d.child_by_field_name("value"),
        ) else {
            return;
        };
        while matches!(
            value.kind(),
            "await_expression" | "parenthesized_expression"
        ) {
            let Some(i) = children(value)
                .into_iter()
                .find(|c| c.is_named() && !is_comment(*c))
            else {
                return;
            };
            value = i;
        }
        let mut member: Option<String> = None;
        if value.kind() == "member_expression"
            && let (Some(o), Some(p)) = (
                value.child_by_field_name("object"),
                value.child_by_field_name("property"),
            )
        {
            member = Some(self.t(p).to_owned());
            value = o;
        }
        if value.kind() != "call_expression" {
            return;
        }
        let Some(f) = value.child_by_field_name("function") else {
            return;
        };
        let dynamic = f.kind() == "import";
        if !dynamic && !self.is_require(f) {
            return;
        }
        let (mode, spec) = self.module_ref(value, dynamic);
        match name.kind() {
            "identifier" => {
                let m = member.as_deref().unwrap_or("*");
                self.push_use(self.t(name).to_owned(), encode_use(mode, &spec, m), false);
            }
            "object_pattern" if member.is_none() => {
                for p in children(name) {
                    match p.kind() {
                        "shorthand_property_identifier_pattern" => {
                            let local = self.t(p).to_owned();
                            self.push_use(local.clone(), encode_use(mode, &spec, &local), false);
                        }
                        "pair_pattern" => {
                            let (Some(k), Some(v)) =
                                (p.child_by_field_name("key"), p.child_by_field_name("value"))
                            else {
                                continue;
                            };
                            if v.kind() == "identifier" {
                                let key = self.t(k).trim_matches(['"', '\'']).to_owned();
                                self.push_use(
                                    self.t(v).to_owned(),
                                    encode_use(mode, &spec, &key),
                                    false,
                                );
                            }
                        }
                        _ => {}
                    }
                }
            }
            _ => {}
        }
    }

    fn import_stmt(&mut self, n: Node<'_>) -> R<NodeId> {
        let clause = children(n)
            .into_iter()
            .find(|c| c.kind() == "import_require_clause");
        let source = n
            .child_by_field_name("source")
            .or_else(|| clause.and_then(|c| c.child_by_field_name("source")));
        if let Some(spec) = source.and_then(|s| string_value(self.cx.text, s)) {
            self.edges.push(encode_edge(ImportMode::Static, &spec));
            let framework = TEST_PACKAGES
                .iter()
                .find(|(p, _)| *p == spec)
                .map(|(_, f)| (*f).to_owned());
            let bind = |this: &mut Self, local: &str, member: &str| {
                if let Some(fw) = &framework {
                    this.test_names.insert(local.to_owned(), fw.clone());
                }
                this.push_use(
                    local.to_owned(),
                    encode_use(ImportMode::Static, &spec, member),
                    false,
                );
            };
            if let Some(rc) = clause
                && let Some(id) = children(rc).into_iter().find(|c| c.kind() == "identifier")
            {
                let local = self.t(id);
                bind(self, local, "*");
            }
            for c in children(n)
                .into_iter()
                .filter(|c| c.kind() == "import_clause")
            {
                for part in children(c) {
                    match part.kind() {
                        "identifier" => {
                            let local = self.t(part);
                            bind(self, local, "default");
                        }
                        "namespace_import" => {
                            if let Some(id) = children(part)
                                .into_iter()
                                .find(|c| c.kind() == "identifier")
                            {
                                let local = self.t(id);
                                bind(self, local, "*");
                            }
                        }
                        "named_imports" => {
                            for sp in children(part)
                                .into_iter()
                                .filter(|c| c.kind() == "import_specifier")
                            {
                                let Some(name) = sp.child_by_field_name("name") else {
                                    continue;
                                };
                                let member = self.t(name).trim_matches(['"', '\'']);
                                let local = sp
                                    .child_by_field_name("alias")
                                    .map_or(member, |a| self.t(a));
                                bind(self, local, member);
                            }
                        }
                        _ => {}
                    }
                }
            }
        } else {
            tracing::debug!(
                path = self.path,
                "import statement without a literal source"
            );
        }
        self.token_op(n, "import")
    }

    /// One adapter operator `kind` over the leaf tokens of `n`.
    fn token_op(&mut self, n: Node<'_>, kind: &str) -> R<NodeId> {
        let toks: Vec<NodeId> = leaves(n, is_comment)
            .into_iter()
            .map(|l| self.cx.lit(l.kind(), self.t(l), l))
            .collect::<R<_>>()?;
        self.cx
            .op(Operator::adapter(LANG, kind, Sort::Exp), n, &toks)
    }

    fn export_stmt(&mut self, n: Node<'_>, depth: usize, direct: bool) -> R<NodeId> {
        let span = (n.start_byte(), n.end_byte());
        for d in children(n).into_iter().filter(|c| c.kind() == "decorator") {
            self.scan_calls(d);
        }
        if let Some(src) = n.child_by_field_name("source") {
            return self.reexport(n, src);
        }
        let is_default = children(n).iter().any(|c| c.kind() == "default");
        if let Some(d) = n.child_by_field_name("declaration") {
            self.export = Some(span);
            self.direct = direct;
            let id = self.tr(d, depth + 1);
            self.export = None;
            return self
                .cx
                .op(Operator::adapter(LANG, "export", Sort::Exp), n, &[id?]);
        }
        if let Some(v) = n.child_by_field_name("value") {
            self.export = Some(span);
            self.default_export = is_default;
            let id = self.default_value(v, depth + 1);
            self.export = None;
            self.default_export = false;
            return self
                .cx
                .op(Operator::adapter(LANG, "export", Sort::Exp), n, &[id?]);
        }
        let kids = self.gen_children(n, depth)?;
        self.cx
            .op(Operator::adapter(LANG, "export", Sort::Exp), n, &kids)
    }

    /// `export default <expr>`: a function or class becomes the unit `default` (or its own name).
    fn default_value(&mut self, v: Node<'_>, depth: usize) -> R<NodeId> {
        if FN_EXPR.contains(&v.kind()) {
            let doc = self.take_doc()?;
            let span = self.take_export().unwrap_or((v.start_byte(), v.end_byte()));
            let name = v
                .child_by_field_name("name")
                .map_or_else(|| "default".to_owned(), |x| unit_name(self.t(x)));
            let head = UnitHead {
                kind: "function",
                name,
                vis: "public",
                span,
                decorators: Vec::new(),
            };
            return self.fn_unit(v, &head, doc, &[], depth);
        }
        self.default_export = v.kind() == "class";
        self.tr(v, depth)
    }

    /// `export ... from "m"`: an import edge plus public bindings.
    fn reexport(&mut self, n: Node<'_>, src: Node<'_>) -> R<NodeId> {
        let Some(spec) = string_value(self.cx.text, src) else {
            tracing::debug!(path = self.path, "re-export without a literal source");
            return self.token_op(n, "export_from");
        };
        self.edges.push(encode_edge(ImportMode::Static, &spec));
        let target = |member: &str| encode_use(ImportMode::Static, &spec, member);
        let mut bindings: Vec<(String, String)> = Vec::new();
        let kids = children(n);
        let clause = kids.iter().find(|c| c.kind() == "export_clause");
        let ns = kids.iter().find(|c| c.kind() == "namespace_export");
        if let Some(ns) = ns {
            if let Some(id) = children(*ns).into_iter().find(Node::is_named) {
                bindings.push((self.t(id).to_owned(), target("*")));
            }
        } else if let Some(clause) = clause {
            for sp in children(*clause)
                .into_iter()
                .filter(|c| c.kind() == "export_specifier")
            {
                let Some(name) = sp.child_by_field_name("name") else {
                    continue;
                };
                let member = self.t(name).trim_matches(['"', '\'']).to_owned();
                let local = sp
                    .child_by_field_name("alias")
                    .map_or_else(|| member.clone(), |a| self.t(a).to_owned());
                bindings.push((local, target(&member)));
            }
        } else {
            bindings.push(("*".to_owned(), target("*")));
        }
        for (local, t) in bindings {
            self.push_use(local, t, true);
        }
        self.token_op(n, "export_from")
    }

    // ---- units ----

    /// Builds a unit with its doc, decorator, sig and body children.
    #[allow(
        clippy::too_many_arguments,
        reason = "one unit constructor, inputs distinct"
    )]
    fn make_unit(
        &mut self,
        ord: usize,
        head: &UnitHead<'_>,
        doc: Option<NodeId>,
        sig: Vec<NodeId>,
        body: Vec<NodeId>,
        binders: &[String],
    ) -> R<NodeId> {
        let loc = self.cx.loc(head.span.0, head.span.1);
        let mut kids = Vec::new();
        kids.extend(doc);
        let mut sig_kids = Vec::new();
        for d in &head.decorators {
            kids.push(self.decorator_attr(*d)?);
            sig_kids.push(self.decorator_attr(*d)?);
        }
        sig_kids.extend(sig);
        let sig_group = NodeSpec::new(Operator::group(GroupOrder::Sequence), loc.clone())
            .attr(reserved::FACET, "sig");
        kids.push(self.cx.add(sig_group, &sig_kids)?);
        kids.extend(body);
        let names: Vec<&str> = binders.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::unit(head.kind, "impl"), loc)
            .named(&head.name)
            .binders(&names)
            .attr(ATTR_VISIBILITY, head.vis);
        let id = self.cx.add(spec, &kids)?;
        self.ord_nodes[ord] = Some(id);
        tracing::trace!(path = self.path, kind = head.kind, name = %head.name, "typescript unit");
        Ok(id)
    }

    /// One `attr` node for decorator `d`: its name is the callee text, its payload the call arguments.
    fn decorator_attr(&mut self, d: Node<'_>) -> R<NodeId> {
        let expr = children(d)
            .into_iter()
            .find(|c| c.is_named() && !is_comment(*c));
        let (name, args) = match expr {
            Some(e) if e.kind() == "call_expression" => (
                e.child_by_field_name("function").map(|f| self.t(f)),
                e.child_by_field_name("arguments"),
            ),
            Some(e) => (Some(self.t(e)), None),
            None => (None, None),
        };
        let name: String = name.unwrap_or_default().split_whitespace().collect();
        let mut payload = Vec::new();
        if let Some(a) = args {
            for l in leaves(a, is_comment) {
                payload.push(self.cx.lit(l.kind(), self.t(l), l)?);
            }
        }
        self.cx.op(Operator::attr(&name), d, &payload)
    }

    /// The leaf tokens of the children of `n` other than those in `exclude`, in token mode.
    fn sig_lits(&mut self, n: Node<'_>, exclude: &[Node<'_>]) -> R<Vec<NodeId>> {
        let skip: HashSet<usize> = exclude.iter().map(Node::id).collect();
        let mut out = Vec::new();
        for c in children(n) {
            if skip.contains(&c.id()) || is_comment(c) || c.kind() == "decorator" {
                continue;
            }
            for l in leaves(c, is_comment) {
                out.push(self.cx.lit(l.kind(), self.t(l), l)?);
            }
        }
        Ok(out)
    }

    /// The named statements of a `statement_block`.
    fn block_stmts(block: Node<'_>) -> Vec<Node<'_>> {
        children(block).into_iter().filter(Node::is_named).collect()
    }

    /// The binders of function-like `f`: its parameters and the names its body declares.
    fn fn_binders(&self, f: Node<'_>) -> Vec<String> {
        let seed = param_names(f, self.cx.text);
        let stmts = f
            .child_by_field_name("body")
            .filter(|b| b.kind() == "statement_block")
            .map(Self::block_stmts)
            .unwrap_or_default();
        scope_binders(seed, &stmts, self.cx.text, &HashSet::new())
    }

    /// The body of function-like `f` as one group: statements, or the single expression of an arrow.
    fn fn_body_group(&mut self, f: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(body) = f.child_by_field_name("body") else {
            return self.cx.add(
                NodeSpec::new(Operator::group(GroupOrder::Sequence), self.cx.node_loc(f)),
                &[],
            );
        };
        let kids = if body.kind() == "statement_block" {
            let stmts = Self::block_stmts(body);
            self.with_expr(true, |s| s.seq(&stmts, depth + 1, false))?
        } else {
            vec![self.with_expr(true, |s| s.tr(body, depth + 1))?]
        };
        self.cx
            .op(Operator::group(GroupOrder::Sequence), body, &kids)
    }

    /// A unit for function-like `f` (declaration, arrow, method, default export).
    fn fn_unit(
        &mut self,
        f: Node<'_>,
        head: &UnitHead<'_>,
        doc: Option<NodeId>,
        extra_sig: &[Node<'_>],
        depth: usize,
    ) -> R<NodeId> {
        if let Some(p) = f
            .child_by_field_name("parameters")
            .or_else(|| f.child_by_field_name("parameter"))
        {
            self.scan_calls(p);
        }
        let body = f.child_by_field_name("body");
        let name_node = f.child_by_field_name("name");
        let mut exclude: Vec<Node<'_>> = body.into_iter().chain(name_node).collect();
        exclude.extend(extra_sig.iter().copied());
        let mut sig = vec![self.cx.lit("name", &head.name, name_node.unwrap_or(f))?];
        for e in extra_sig {
            for l in leaves(*e, is_comment) {
                sig.push(self.cx.lit(l.kind(), self.t(l), l)?);
            }
        }
        sig.extend(self.with_expr(false, |s| s.sig_lits(f, &exclude))?);
        let binders = self.fn_binders(f);
        let ord = self.alloc();
        self.units.push((ord, Ctx::Function));
        self.bound.push(binders.iter().cloned().collect());
        let body = self.fn_body_group(f, depth);
        self.bound.pop();
        self.units.pop();
        self.make_unit(ord, head, doc, sig, vec![body?], &binders)
    }

    /// The visibility word of a declaration directly in the current scope.
    fn scope_vis(&self, name: &str, exported: bool) -> &'static str {
        match self.units.last() {
            Some((_, Ctx::Namespace)) if exported => "public",
            None if exported || self.exports.names.contains(name) => "public",
            _ => "private",
        }
    }

    fn func_decl(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let export = self.take_export();
        let (Some(name_node), Some(_)) =
            (n.child_by_field_name("name"), n.child_by_field_name("body"))
        else {
            return self.generic(n, depth);
        };
        let doc = self.take_doc()?;
        let name = unit_name(self.t(name_node));
        let head = UnitHead {
            kind: "function",
            vis: self.scope_vis(&name, export.is_some()),
            name,
            span: export.unwrap_or((n.start_byte(), n.end_byte())),
            decorators: Vec::new(),
        };
        self.fn_unit(n, &head, doc, &[], depth)
    }

    fn class_unit(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let export = self.take_export();
        let default = std::mem::take(&mut self.default_export);
        let Some(body) = n.child_by_field_name("body") else {
            return self.generic(n, depth);
        };
        let name = match n.child_by_field_name("name") {
            Some(x) => unit_name(self.t(x)),
            None if default => "default".to_owned(),
            None => return self.generic(n, depth),
        };
        let doc = self.take_doc()?;
        let decorators: Vec<Node<'_>> = children(n)
            .into_iter()
            .filter(|c| c.kind() == "decorator")
            .collect();
        for d in &decorators {
            self.scan_calls(*d);
        }
        for c in children(n)
            .into_iter()
            .filter(|c| c.kind() == "class_heritage")
        {
            self.scan_calls(c);
        }
        let sig = self.with_expr(false, |s| s.sig_lits(n, &[body]))?;
        let vis = self.scope_vis(&name, export.is_some());
        let ord = self.alloc();
        self.units.push((ord, Ctx::Class));
        let members: Vec<Node<'_>> = children(body).into_iter().filter(Node::is_named).collect();
        let kids = self.seq(&members, depth + 1, false);
        self.units.pop();
        let group = self
            .cx
            .op(Operator::group(GroupOrder::Sequence), body, &kids?)?;
        let head = UnitHead {
            kind: "class",
            name,
            vis,
            span: export.unwrap_or((n.start_byte(), n.end_byte())),
            decorators,
        };
        self.make_unit(ord, &head, doc, sig, vec![group], &[])
    }

    /// The visibility word of a class member from its modifiers and name.
    fn member_vis(&self, n: Node<'_>) -> &'static str {
        let private_name = n
            .child_by_field_name("name")
            .or_else(|| n.child_by_field_name("property"))
            .is_some_and(|x| x.kind() == "private_property_identifier");
        let modifier = children(n)
            .into_iter()
            .find(|c| c.kind() == "accessibility_modifier")
            .map(|c| self.t(c).trim());
        match (private_name, modifier) {
            (true, _) | (_, Some("private")) => "private",
            (_, Some("protected")) => "crate",
            _ => "public",
        }
    }

    /// The unit name of a class member's name node.
    fn member_name(&self, name: Node<'_>) -> String {
        match name.kind() {
            "computed_property_name" => "$computed".to_owned(),
            _ => unit_name(self.t(name)),
        }
    }

    fn method_unit(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let (Some(name_node), Some(_)) =
            (n.child_by_field_name("name"), n.child_by_field_name("body"))
        else {
            return self.generic(n, depth);
        };
        let doc = self.take_doc()?;
        let head = UnitHead {
            kind: "method",
            name: self.member_name(name_node),
            vis: self.member_vis(n),
            span: (n.start_byte(), n.end_byte()),
            decorators: children(n)
                .into_iter()
                .filter(|c| c.kind() == "decorator")
                .collect(),
        };
        for d in &head.decorators {
            self.scan_calls(*d);
        }
        self.fn_unit(n, &head, doc, &[], depth)
    }

    /// A class field: a method unit when it holds a function (`handle = () => {}`), else tokens and expressions.
    fn field_member(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let name_node = n
            .child_by_field_name("name")
            .or_else(|| n.child_by_field_name("property"));
        let value = n.child_by_field_name("value");
        if let (Some(name_node), Some(v)) = (name_node, value)
            && FN_EXPR.contains(&v.kind())
        {
            let doc = self.take_doc()?;
            let decorators: Vec<Node<'_>> = children(n)
                .into_iter()
                .filter(|c| c.kind() == "decorator")
                .collect();
            for d in &decorators {
                self.scan_calls(*d);
            }
            let head = UnitHead {
                kind: "method",
                name: self.member_name(name_node),
                vis: self.member_vis(n),
                span: (n.start_byte(), n.end_byte()),
                decorators,
            };
            let annotation: Vec<Node<'_>> = children(n)
                .into_iter()
                .filter(|c| c.kind() == "type_annotation" || c.kind() == "accessibility_modifier")
                .collect();
            return self.fn_unit(v, &head, doc, &annotation, depth);
        }
        let mut kids = Vec::new();
        for c in children(n) {
            if Some(c.id()) == name_node.map(|x| x.id()) {
                kids.push(self.cx.lit("name", self.t(c), c)?);
            } else {
                kids.push(self.tr(c, depth + 1)?);
            }
        }
        self.cx
            .op(Operator::adapter(LANG, n.kind(), Sort::Exp), n, &kids)
    }

    /// Interface, type alias and enum: the whole declaration is the signature.
    fn simple_unit(&mut self, n: Node<'_>, kind: &'static str, depth: usize) -> R<NodeId> {
        let export = self.take_export();
        let Some(name_node) = n.child_by_field_name("name") else {
            return self.generic(n, depth);
        };
        let doc = self.take_doc()?;
        let name = unit_name(self.t(name_node));
        let sig = self.with_expr(false, |s| s.sig_lits(n, &[]))?;
        let ord = self.alloc();
        self.units.push((ord, Ctx::Function));
        self.scan_calls(n);
        self.units.pop();
        let body = self.cx.op(Operator::group(GroupOrder::Sequence), n, &[])?;
        let head = UnitHead {
            kind,
            vis: self.scope_vis(&name, export.is_some()),
            name,
            span: export.unwrap_or((n.start_byte(), n.end_byte())),
            decorators: Vec::new(),
        };
        self.make_unit(ord, &head, doc, sig, vec![body], &[])
    }

    /// `namespace A.B { .. }`: one unit per dotted component, the body in the innermost.
    fn namespace_unit(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let export = self.take_export();
        let (Some(name_node), Some(body)) =
            (n.child_by_field_name("name"), n.child_by_field_name("body"))
        else {
            return self.generic(n, depth);
        };
        let mut doc = self.take_doc()?;
        let comps: Vec<String> = self
            .t(name_node)
            .split('.')
            .map(|c| unit_name(c.trim()))
            .collect();
        let vis = self.scope_vis(&comps[0], export.is_some());
        let stmts = Self::block_stmts(body);
        let skip = unit_declarators(&stmts, self.cx.text);
        let binders = scope_binders(Vec::new(), &stmts, self.cx.text, &skip);
        let ords: Vec<usize> = comps.iter().map(|_| self.alloc()).collect();
        for &o in &ords {
            self.units.push((o, Ctx::Namespace));
        }
        self.bound.push(binders.iter().cloned().collect());
        let kids = self.seq(&stmts, depth + 1, true);
        self.bound.pop();
        for _ in &ords {
            self.units.pop();
        }
        let mut inner = self
            .cx
            .op(Operator::group(GroupOrder::Sequence), body, &kids?)?;
        let span = export.unwrap_or((n.start_byte(), n.end_byte()));
        for (i, comp) in comps.iter().enumerate().rev() {
            let sig = vec![self.cx.lit("name", comp, name_node)?];
            let head = UnitHead {
                kind: "namespace",
                name: comp.clone(),
                vis: if i == 0 { vis } else { "public" },
                span,
                decorators: Vec::new(),
            };
            let own_binders: &[String] = if i + 1 == comps.len() { &binders } else { &[] };
            let d = if i == 0 { doc.take() } else { None };
            inner = self.make_unit(ords[i], &head, d, sig, vec![inner], own_binders)?;
        }
        Ok(inner)
    }

    /// `const`, `let` and `var` declarations: units at module level, binders elsewhere.
    fn var_decl(&mut self, n: Node<'_>, depth: usize, direct: bool) -> R<NodeId> {
        let export = self.take_export();
        let keyword = children(n).first().map_or("var", |k| self.t(*k)).to_owned();
        let module_level = direct && self.at_module_level();
        let mut kids = Vec::new();
        for c in children(n) {
            if c.kind() != "variable_declarator" {
                kids.push(if is_comment(c) {
                    self.tr(c, depth + 1)?
                } else {
                    self.cx.lit(c.kind(), self.t(c), c)?
                });
                continue;
            }
            self.bind_require(c);
            let unit_name_node = c
                .child_by_field_name("name")
                .filter(|x| x.kind() == "identifier" && !is_module_binding(c, self.cx.text));
            match unit_name_node {
                Some(nm) if module_level => {
                    let doc = self.take_doc()?;
                    let id = self.declarator_unit(c, nm, &keyword, export, doc, depth)?;
                    kids.push(id);
                }
                _ => {
                    // Not a unit: any doc stays unused.
                    kids.push(self.generic(c, depth + 1)?);
                }
            }
        }
        self.cx
            .op(Operator::adapter(LANG, n.kind(), Sort::Exp), n, &kids)
    }

    /// One module-level declarator as a unit: a function for an arrow or function value, else a constant.
    fn declarator_unit(
        &mut self,
        d: Node<'_>,
        name_node: Node<'_>,
        keyword: &str,
        export: Option<(usize, usize)>,
        doc: Option<NodeId>,
        depth: usize,
    ) -> R<NodeId> {
        let name = unit_name(self.t(name_node));
        let value = d.child_by_field_name("value");
        let annotation: Vec<Node<'_>> = children(d)
            .into_iter()
            .filter(|c| c.kind() == "type_annotation")
            .collect();
        let vis = self.scope_vis(&name, export.is_some());
        let span = export.unwrap_or((d.start_byte(), d.end_byte()));
        match value {
            Some(v) if FN_EXPR.contains(&v.kind()) => {
                let head = UnitHead {
                    kind: "function",
                    name,
                    vis,
                    span,
                    decorators: Vec::new(),
                };
                self.fn_unit(v, &head, doc, &annotation, depth)
            }
            _ => {
                let mut sig = vec![self.cx.lit("name", &name, name_node)?];
                for a in &annotation {
                    for l in leaves(*a, is_comment) {
                        sig.push(self.cx.lit(l.kind(), self.t(l), l)?);
                    }
                }
                let ord = self.alloc();
                self.units.push((ord, Ctx::Value));
                let body = match value {
                    Some(v) => {
                        let id = self.with_expr(true, |s| s.tr(v, depth + 1));
                        id.and_then(|id| {
                            self.cx.op(Operator::group(GroupOrder::Sequence), v, &[id])
                        })
                    }
                    None => self.cx.op(Operator::group(GroupOrder::Sequence), d, &[]),
                };
                self.units.pop();
                let kind = if keyword == "const" {
                    "const"
                } else {
                    "static"
                };
                let head = UnitHead {
                    kind,
                    name,
                    vis,
                    span,
                    decorators: Vec::new(),
                };
                self.make_unit(ord, &head, doc, sig, vec![body?], &[])
            }
        }
    }

    /// An anonymous function: arrow, function expression or object-literal method.
    fn anon_fn(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let names = self.fn_binders(n);
        if let Some(p) = n
            .child_by_field_name("parameters")
            .or_else(|| n.child_by_field_name("parameter"))
        {
            self.scan_calls(p);
        }
        let body = n.child_by_field_name("body");
        let exclude: Vec<Node<'_>> = body.into_iter().collect();
        let sig_toks = self.with_expr(false, |s| s.sig_lits(n, &exclude))?;
        let sig = self
            .cx
            .op(Operator::group(GroupOrder::Sequence), n, &sig_toks)?;
        self.bound.push(names.iter().cloned().collect());
        self.cond_depth += 1;
        let body = self.fn_body_group(n, depth);
        self.cond_depth -= 1;
        self.bound.pop();
        let refs: Vec<&str> = names.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::anon("function"), self.cx.node_loc(n)).binders(&refs);
        self.cx.add(spec, &[sig, body?])
    }

    // ---- JSX ----

    /// The tag, kind (`intrinsic`, `component`, `member`, `fragment`) and head node of a JSX name.
    fn jsx_head(
        &mut self,
        name: Option<Node<'_>>,
        fallback: Node<'_>,
    ) -> R<(String, &'static str, NodeId)> {
        let Some(nm) = name else {
            let id = self.cx.lit("tag", "", fallback)?;
            return Ok((String::new(), "fragment", id));
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
            Ok((tag, kind, id))
        } else {
            let id = self.cx.lit("tag", &tag, nm)?;
            Ok((tag, "intrinsic", id))
        }
    }

    fn jsx_attribute(&mut self, a: Node<'_>, depth: usize) -> R<(String, NodeId)> {
        if a.kind() != "jsx_attribute" {
            // `{...props}`: a spread contributes any attribute.
            let id = self.tr(a, depth + 1)?;
            let id = self
                .cx
                .op(Operator::adapter(LANG, "jsx_spread", Sort::Exp), a, &[id])?;
            return Ok(("...".to_owned(), id));
        }
        let kids_src = children(a);
        let name = kids_src.first().copied();
        let name_text = name.map(|x| self.t(x).to_owned()).unwrap_or_default();
        let mut kids = Vec::new();
        if let Some(nm) = name {
            kids.push(self.cx.lit("attr-name", self.t(nm), nm)?);
        }
        for v in kids_src.into_iter().skip(1).filter(Node::is_named) {
            kids.push(self.tr(v, depth + 1)?);
        }
        let spec = NodeSpec::new(
            Operator::adapter(LANG, "jsx_attribute", Sort::Exp),
            self.cx.node_loc(a),
        )
        .attr("jsx.name", name_text.as_str());
        Ok((name_text, self.cx.add(spec, &kids)?))
    }

    fn jsx(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let (open, rest): (Option<Node<'_>>, Vec<Node<'_>>) = match n.kind() {
            "jsx_element" => (
                n.child_by_field_name("open_tag"),
                children(n)
                    .into_iter()
                    .filter(|c| {
                        c.is_named()
                            && c.kind() != "jsx_opening_element"
                            && c.kind() != "jsx_closing_element"
                    })
                    .collect(),
            ),
            "jsx_self_closing_element" => (Some(n), Vec::new()),
            _ => (
                None,
                children(n).into_iter().filter(Node::is_named).collect(),
            ),
        };
        let name = open.and_then(|o| o.child_by_field_name("name"));
        let (tag, kind, head) = self.jsx_head(name, n)?;
        let mut kids = vec![head];
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
            kids.push(self.tr(c, depth + 1)?);
        }
        let op = if n.kind() == "jsx_fragment" {
            "jsx_fragment"
        } else {
            n.kind()
        };
        let spec = NodeSpec::new(Operator::adapter(LANG, op, Sort::Exp), self.cx.node_loc(n))
            .attr(ATTR_JSX_TAG, tag.as_str())
            .attr(ATTR_JSX_KIND, kind)
            .attr(ATTR_JSX_ATTRS, attr_names.join(",").as_str())
            .attr(ATTR_JSX_LINE, i64::from(line_of(n)));
        self.cx.add(spec, &kids)
    }

    /// `{expr}`: a lone identifier is a function or value passed along (a handler, a render prop).
    fn jsx_expression(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let named: Vec<Node<'_>> = children(n)
            .into_iter()
            .filter(|c| c.is_named() && !is_comment(*c))
            .collect();
        if let [only] = named.as_slice()
            && only.kind() == "identifier"
        {
            self.value_site(*only);
        }
        let kids = self.with_expr(true, |s| s.gen_children(n, depth))?;
        self.cx.op(
            Operator::adapter(LANG, "jsx_expression", Sort::Exp),
            n,
            &kids,
        )
    }
}
