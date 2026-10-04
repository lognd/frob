//! The Python adapter (fidelity F2): tree-sitter tree to a U term plus scope graph.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`; `def` is `unit(function, impl)` (`unit(method, impl)`
//!   directly inside a `class`), `class` is `unit(class, impl)`; nested functions are
//!   children of their function (`outer.inner`), methods children of their class
//!   (`Class.method`). `async def` is a function like any other.
//! - Every unit has children in four groups: `attr("doc")` (the docstring, taken out of
//!   the body), one `attr` per decorator (also copied into the signature group,
//!   G7), a `group` marked `ir.facet = "sig"` holding the name, parameter and
//!   base-class tokens, and the body as one `group`.
//! - Scoping follows Python: the binders of a function unit are its parameters and every
//!   name it assigns, loops over, unpacks, binds with `as`, or captures with `:=` or in a
//!   comprehension anywhere in its body (minus `global` and `nonlocal` names); the file unit
//!   binds the module-level assigned names. A `lambda` is `anon(lambda)` over its parameters.
//!   Imports bind no names in the scope graph; they are recorded as use bindings (resolved
//!   by the graph) so a call through an import is never taken for a local value.
//! - Identifiers in expression position are `ref`s; calls are `apply(call)` (`apply(method)`
//!   for `obj.m()`), `import` statements the adapter operator `python.import`.
//! - Calls in decorators and parameter defaults belong to the enclosing scope and are
//!   recorded there.
//! - A `match` statement binds names this adapter does not model: it carries a
//!   `hole(unmodelled)`, so the file reads as a partial parse and rules that need
//!   the missing facts answer Unresolved. Syntax errors are `hole(parse-error)`.
//! - Everything else maps to the adapter operator `python.<tree-sitter kind>` over its
//!   children, with leaves as `lit`s: a token change always changes the stream,
//!   reformatting and comments never do (G8).
//! - Subtrees deeper than [`MAX_DEPTH`] collapse into one `opaque(depth-limit)`.

// frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF

use std::collections::HashSet;

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, Sort, TermError, reserved};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
    Precision,
};
use crate::fold::{
    Cx, base_file, call_text, children, failed_file, file_root_spec, leaves, line_of,
    local_binding, text_of,
};
use crate::model::{
    CallSite, FileSymbols, ImportEdge, Receiver, RefKind, RefSite, SymbolKind, SymbolRecord,
    UseBinding, collapse_ws,
};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{self, ATTR_VISIBILITY, HOLE_MISSING, HOLE_PARSE_ERROR, HOLE_UNMODELLED, Naming};

/// Deepest term nesting before a subtree collapses into one opaque node.
const MAX_DEPTH: usize = 160;

type R<T> = Result<T, TermError>;

/// The Python adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct PythonAdapter;

impl Adapter for PythonAdapter {
    fn language(&self) -> &'static str {
        "python"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Python)
        )
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F2
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
            .with(Capability::ResolveRef, Precision::Lexical)
            .with(Capability::ApplyTargets, Precision::ByNameInCrate)
            .with(Capability::Visibility, Precision::Syntactic)
            .with(Capability::Imports, Precision::Syntactic)
            .with(Capability::TestItems, Precision::Syntactic)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Python, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "python", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "python",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is a Python source file (`.py` or `.pyi`, any case).
pub fn is_python_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("py") || e.eq_ignore_ascii_case("pyi"))
}

/// True when `path` is a Python test module: `test*.py`, `*_test.py` or `*_tests.py` (pytest and unittest discovery).
pub fn is_python_test_module(path: &str) -> bool {
    let base = path.rsplit('/').next().unwrap_or(path);
    let Some(stem) = base.strip_suffix(".py") else {
        return false;
    };
    stem.starts_with("test") || stem.ends_with("_test") || stem.ends_with("_tests")
}

/// True when `path` is Python test support: a test module, `conftest.py`, or any `.py` under a `tests`/`test` directory.
pub fn is_python_test_file(path: &str) -> bool {
    if !std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("py"))
    {
        return false;
    }
    let mut parts: Vec<&str> = path.split('/').collect();
    let base = parts.pop().unwrap_or_default();
    is_python_test_module(path)
        || base == "conftest.py"
        || parts.iter().any(|d| matches!(*d, "tests" | "test"))
}

/// True when `rec` is a Python test: a module-level `test*` function, or a `test*` method of a class, in a test module.
///
/// This is the pytest and unittest naming convention read from the symbol alone; a class
/// not named `Test*` (a `unittest.TestCase` subclass) counts too, so a non-collected helper
/// class is over-approximated as a test (selecting it only adds a filter that matches nothing).
pub fn is_python_test_fn(rec: &SymbolRecord) -> bool {
    let segs = rec.symref.segments();
    let Some(name) = segs.last() else {
        return false;
    };
    let shape = match rec.kind {
        SymbolKind::Function => segs.len() == 1,
        SymbolKind::Method => segs.len() == 2,
        _ => false,
    };
    shape && is_python_test_module(rec.symref.path()) && name.starts_with("test")
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

/// An import binding waiting for its container's `Symref`.
struct PendingUse {
    container: Option<usize>,
    local: String,
    target: String,
    /// The target of the import edge (the full module of a plain `import a.b.c`).
    edge: String,
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

struct Fold<'a> {
    cx: Cx<'a>,
    path: &'a str,
    /// Identifiers are references (expression context) rather than tokens.
    expr: bool,
    ord_nodes: Vec<Option<NodeId>>,
    /// Enclosing units, innermost last: (ordinal, is a class).
    units: Vec<(usize, bool)>,
    /// Binder names of the enclosing scopes (file, functions, lambdas), innermost last.
    bound: Vec<HashSet<String>>,
    sites: Vec<Site>,
    uses: Vec<PendingUse>,
}

/// Appends every identifier a binding pattern `n` assigns (not attribute or subscript targets).
fn pattern_names(n: Node<'_>, text: &str, out: &mut Vec<String>) {
    match n.kind() {
        "identifier" => out.push(text_of(text, n).to_owned()),
        "attribute" | "subscript" | "comment" => {}
        _ => {
            for c in children(n) {
                pattern_names(c, text, out);
            }
        }
    }
}

/// Appends the parameter names of a `parameters` or `lambda_parameters` node.
fn param_names(params: Node<'_>, text: &str, out: &mut Vec<String>) {
    for p in children(params).into_iter().filter(Node::is_named) {
        match p.kind() {
            "default_parameter" | "typed_default_parameter" => {
                if let Some(n) = p.child_by_field_name("name") {
                    pattern_names(n, text, out);
                }
            }
            "typed_parameter" => {
                if let Some(n) = children(p).into_iter().find(Node::is_named) {
                    pattern_names(n, text, out);
                }
            }
            "comment" | "keyword_separator" | "positional_separator" => {}
            _ => pattern_names(p, text, out),
        }
    }
}

/// Appends the names bound by the statements under `n` in its own scope, and the `global`/`nonlocal` names.
fn walk_binders(n: Node<'_>, text: &str, out: &mut Vec<String>, escaped: &mut HashSet<String>) {
    match n.kind() {
        "function_definition" | "class_definition" | "decorated_definition" | "lambda" => return,
        "assignment" | "augmented_assignment" | "for_statement" | "for_in_clause" => {
            if let Some(l) = n.child_by_field_name("left") {
                pattern_names(l, text, out);
            }
        }
        "named_expression" => {
            if let Some(l) = n.child_by_field_name("name") {
                pattern_names(l, text, out);
            }
        }
        "as_pattern" | "except_clause" => {
            if let Some(a) = n.child_by_field_name("alias") {
                pattern_names(a, text, out);
            }
        }
        "case_clause" => {
            for p in children(n)
                .into_iter()
                .filter(|c| c.kind() == "case_pattern")
            {
                pattern_names(p, text, out);
            }
        }
        "global_statement" | "nonlocal_statement" => {
            for c in children(n).into_iter().filter(|c| c.kind() == "identifier") {
                escaped.insert(text_of(text, c).to_owned());
            }
        }
        _ => {}
    }
    for c in children(n) {
        walk_binders(c, text, out, escaped);
    }
}

/// The binder names of a scope whose statements are `body`, `seed` (parameters) first.
fn scope_binders(seed: Vec<String>, body: &[Node<'_>], text: &str) -> Vec<String> {
    let mut names = seed;
    let mut escaped = HashSet::new();
    for s in body {
        walk_binders(*s, text, &mut names, &mut escaped);
    }
    names.retain(|n| !escaped.contains(n));
    names.sort();
    names.dedup();
    names
}

fn is_comment(n: Node<'_>) -> bool {
    n.kind() == "comment"
}

/// The string literal of a docstring statement, when `stmt` is one.
fn docstring_of(stmt: Node<'_>) -> Option<Node<'_>> {
    if stmt.kind() != "expression_statement" {
        return None;
    }
    let mut named = children(stmt).into_iter().filter(Node::is_named);
    let s = named.next()?;
    (named.next().is_none() && matches!(s.kind(), "string" | "concatenated_string")).then_some(s)
}

/// Splits a block's statements into its docstring statement (if first) and the rest.
fn split_docstring(stmts: Vec<Node<'_>>) -> (Option<Node<'_>>, Vec<Node<'_>>) {
    let first = stmts.iter().position(|s| !is_comment(*s));
    match first {
        Some(i) if docstring_of(stmts[i]).is_some() => {
            let doc = stmts[i];
            let rest = stmts
                .into_iter()
                .enumerate()
                .filter(|(j, _)| *j != i)
                .map(|(_, s)| s)
                .collect();
            (Some(doc), rest)
        }
        _ => (None, stmts),
    }
}

/// `public` for a name without a leading underscore (dunder names included), else `private`.
fn visibility_text(name: &str, in_function: bool) -> &'static str {
    let dunder = name.starts_with("__") && name.ends_with("__") && name.len() > 4;
    if in_function || (name.starts_with('_') && !dunder) {
        "private"
    } else {
        "public"
    }
}

/// The text of a docstring string literal without its quotes and prefix, trimmed.
fn docstring_text(text: &str, s: Node<'_>) -> String {
    let raw = text_of(text, s);
    let body = raw.trim_start_matches(|c: char| c.is_ascii_alphabetic());
    for q in ["\"\"\"", "'''", "\"", "'"] {
        if let Some(inner) = body.strip_prefix(q).and_then(|b| b.strip_suffix(q)) {
            return inner.trim().to_owned();
        }
    }
    body.trim().to_owned()
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut f = Fold {
        cx: Cx::new(input.path, "python", text),
        path: input.path,
        expr: true,
        ord_nodes: vec![None],
        units: Vec::new(),
        bound: Vec::new(),
        sites: Vec::new(),
        uses: Vec::new(),
    };
    let stmts = children(root);
    let (doc, rest) = split_docstring(stmts);
    let names = scope_binders(Vec::new(), &rest, text);
    f.bound.push(names.iter().cloned().collect());
    let mut kids = Vec::new();
    if let Some(d) = doc.and_then(docstring_of) {
        kids.push(f.doc_node(d)?);
    }
    for s in &rest {
        kids.push(f.tr(*s, 1)?);
    }
    let refs: Vec<&str> = names.iter().map(String::as_str).collect();
    let spec = file_root_spec(&f.cx, input.size as usize).binders(&refs);
    let root_id = f.cx.add(spec, &kids)?;
    f.ord_nodes[0] = Some(root_id);
    let Fold {
        cx,
        ord_nodes,
        sites,
        uses,
        ..
    } = f;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Python);
    let mut file = base_file(input, "python");
    file.fidelity = Fidelity::F2;
    file.parse_status = view::parse_status_of(&term);
    let symref_of = |ord: usize| -> Option<Symref> {
        ord_nodes
            .get(ord)
            .copied()
            .flatten()
            .and_then(|n| v.by_node.get(&n).cloned())
    };
    for u in uses {
        file.imports.push(ImportEdge {
            from_file: input.path.to_owned(),
            target: u.edge,
        });
        file.uses.push(UseBinding {
            from_file: input.path.to_owned(),
            local: u.local,
            target: u.target,
            public: false,
            container: u.container.and_then(symref_of),
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
        status = ?file.parse_status,
        "python file folded"
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

    /// The ordinal of the unit calls are attributed to (0, the file, outside any def or class).
    fn caller(&self) -> usize {
        self.units.last().map_or(0, |u| u.0)
    }

    fn is_bound(&self, name: &str) -> bool {
        self.bound.iter().any(|s| s.contains(name))
    }

    // ---- generic translation ----

    fn hole(&mut self, n: Node<'_>) -> R<NodeId> {
        let kind = if n.is_missing() {
            HOLE_MISSING
        } else {
            HOLE_PARSE_ERROR
        };
        tracing::debug!(path = self.path, kind, at = n.start_byte(), "python hole");
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
            if n.kind() == "call" {
                self.record_call(n, None);
            }
            stack.extend(children(n));
        }
    }

    fn tr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
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
            "identifier" if self.expr => {
                let name = self.t(n);
                self.cx.op(Operator::reference(name), n, &[])
            }
            "call" if self.expr => self.call(n, depth),
            "attribute" if self.expr => self.attribute(n, depth),
            "keyword_argument" if self.expr => self.keyword_argument(n, depth),
            "function_definition" => self.def_unit(n, n, &[], depth),
            "class_definition" => self.class_unit(n, n, &[], depth),
            "decorated_definition" => self.decorated(n, depth),
            "lambda" => self.lambda(n, depth),
            "import_statement" | "import_from_statement" | "future_import_statement" => {
                self.import(n)
            }
            "match_statement" => {
                let mut kids = self.gen_children(n, depth)?;
                kids.push(self.cx.op(Operator::hole(HOLE_UNMODELLED), n, &[])?);
                tracing::debug!(path = self.path, "python match statement is unmodelled");
                self.cx
                    .op(Operator::adapter("python", n.kind(), Sort::Exp), n, &kids)
            }
            "string" if !children(n).iter().any(|c| c.kind() == "interpolation") => {
                self.cx.lit("string", self.t(n), n)
            }
            "type" | "dotted_name" | "global_statement" | "nonlocal_statement" => {
                self.with_expr(false, |s| s.generic(n, depth))
            }
            _ => self.generic(n, depth),
        }
    }

    fn generic(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        if n.child_count() == 0 {
            return self.cx.lit(n.kind(), self.t(n), n);
        }
        let kids = self.gen_children(n, depth)?;
        self.cx
            .op(Operator::adapter("python", n.kind(), Sort::Exp), n, &kids)
    }

    fn gen_children(&mut self, n: Node<'_>, depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(n) {
            out.push(self.tr(c, depth + 1)?);
        }
        Ok(out)
    }

    /// `obj.name` in expression position: the object is an expression, the attribute a token.
    fn attribute(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        if let Some(o) = n.child_by_field_name("object") {
            kids.push(self.tr(o, depth + 1)?);
        }
        if let Some(a) = n.child_by_field_name("attribute") {
            kids.push(self.cx.lit("attr", self.t(a), a)?);
        }
        self.cx.op(
            Operator::adapter("python", "attribute", Sort::Exp),
            n,
            &kids,
        )
    }

    /// `name=value`: the name is a token, the value an expression.
    fn keyword_argument(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        if let Some(k) = n.child_by_field_name("name") {
            kids.push(self.cx.lit("kwarg", self.t(k), k)?);
        }
        if let Some(v) = n.child_by_field_name("value") {
            kids.push(self.tr(v, depth + 1)?);
        }
        self.cx.op(
            Operator::adapter("python", "keyword_argument", Sort::Exp),
            n,
            &kids,
        )
    }

    // ---- calls ----

    fn call_target(&self, f: Node<'_>) -> CallTarget {
        let dynamic = || CallTarget {
            name: String::new(),
            qualifier: None,
            method: false,
            dynamic: true,
            receiver: None,
            path: Vec::new(),
        };
        match f.kind() {
            "identifier" => CallTarget {
                name: self.t(f).to_owned(),
                qualifier: None,
                method: false,
                dynamic: false,
                receiver: None,
                path: Vec::new(),
            },
            "attribute" => {
                let Some(leaf) = f.child_by_field_name("attribute") else {
                    return dynamic();
                };
                let name = self.t(leaf).to_owned();
                let mut chain = Vec::new();
                let mut cur = f.child_by_field_name("object");
                let mut pure = false;
                while let Some(c) = cur {
                    match c.kind() {
                        "identifier" => {
                            chain.push(self.t(c).to_owned());
                            pure = true;
                            break;
                        }
                        "attribute" => {
                            let Some(a) = c.child_by_field_name("attribute") else {
                                break;
                            };
                            chain.push(self.t(a).to_owned());
                            cur = c.child_by_field_name("object");
                        }
                        _ => break,
                    }
                }
                chain.reverse();
                let method_on = |receiver: Receiver| CallTarget {
                    name: name.clone(),
                    qualifier: None,
                    method: true,
                    dynamic: false,
                    receiver: Some(receiver),
                    path: Vec::new(),
                };
                if !pure {
                    return method_on(Receiver::Expr);
                }
                let head = chain[0].as_str();
                if chain.len() == 1 && matches!(head, "self" | "cls") {
                    return method_on(Receiver::SelfValue);
                }
                if matches!(head, "self" | "cls") || self.is_bound(head) {
                    return method_on(Receiver::Expr);
                }
                CallTarget {
                    name,
                    qualifier: chain.last().cloned(),
                    method: false,
                    dynamic: false,
                    receiver: None,
                    path: chain,
                }
            }
            _ => dynamic(),
        }
    }

    /// Records the call `n` (and the function values among its arguments) as sites of the current unit.
    fn record_call(&mut self, n: Node<'_>, node: Option<NodeId>) {
        let Some(f) = n.child_by_field_name("function") else {
            return;
        };
        let target = self.call_target(f);
        let caller = self.caller();
        let args = n.child_by_field_name("arguments");
        let arg_nodes: Vec<Node<'_>> = args
            .map(|a| {
                children(a)
                    .into_iter()
                    .filter(|c| c.is_named() && !is_comment(*c))
                    .collect()
            })
            .unwrap_or_default();
        for a in &arg_nodes {
            let value = if a.kind() == "keyword_argument" {
                a.child_by_field_name("value")
            } else {
                Some(*a)
            };
            if let Some(v) = value.filter(|v| v.kind() == "identifier") {
                let name = self.t(v);
                if !self.is_bound(name) {
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
            }
        }
        tracing::trace!(path = self.path, callee = %target.name, "python call");
        self.sites.push(Site {
            caller,
            value: false,
            name: target.name,
            qualifier: target.qualifier,
            method: target.method,
            receiver: target.receiver,
            node: node.filter(|_| !target.dynamic),
            args: if args.is_some_and(|a| a.kind() == "generator_expression") {
                1
            } else {
                arg_nodes.len()
            },
            qual_path: target.path,
            line: line_of(n),
            text: call_text(self.t(f)),
        });
    }

    fn call(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(f) = n.child_by_field_name("function") else {
            return self.generic(n, depth);
        };
        let target = self.call_target(f);
        let mut kids = Vec::new();
        let head = if target.dynamic {
            self.tr(f, depth + 1)?
        } else if target.method {
            let name = format!(".{}", target.name);
            let field = f.child_by_field_name("attribute").unwrap_or(f);
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
        if let Some(args) = n.child_by_field_name("arguments") {
            if args.kind() == "argument_list" {
                for a in children(args) {
                    if a.is_named() {
                        kids.push(self.tr(a, depth + 1)?);
                    }
                }
            } else {
                kids.push(self.tr(args, depth + 1)?);
            }
        }
        let kind = if target.method { "method" } else { "call" };
        self.record_call(n, Some(head));
        self.cx.op(Operator::apply(kind), n, &kids)
    }

    // ---- imports ----

    fn push_use(&mut self, local: String, target: String) {
        let container = self.units.last().map(|u| u.0);
        tracing::trace!(path = self.path, %local, %target, "python import");
        self.uses.push(PendingUse {
            container,
            local,
            edge: target.clone(),
            target,
        });
    }

    /// `a.b.c` (a `dotted_name`) as its text with whitespace removed.
    fn dotted(&self, n: Node<'_>) -> String {
        self.t(n).split_whitespace().collect()
    }

    fn import(&mut self, n: Node<'_>) -> R<NodeId> {
        let names: Vec<Node<'_>> = {
            let mut c = n.walk();
            n.children_by_field_name("name", &mut c).collect()
        };
        match n.kind() {
            "import_statement" => {
                for name in names {
                    let (module, alias) = self.aliased(name);
                    if let Some(a) = alias {
                        self.push_use(a, module);
                    } else {
                        let head = module.split('.').next().unwrap_or_default().to_owned();
                        self.uses.push(PendingUse {
                            container: self.units.last().map(|u| u.0),
                            local: head.clone(),
                            target: head,
                            edge: module,
                        });
                    }
                }
            }
            "import_from_statement" => {
                let module = n
                    .child_by_field_name("module_name")
                    .map(|m| self.dotted(m))
                    .unwrap_or_default();
                let base = if module.ends_with('.') {
                    module
                } else {
                    format!("{module}.")
                };
                if children(n).iter().any(|c| c.kind() == "wildcard_import") {
                    self.push_use("*".to_owned(), format!("{base}*"));
                }
                for name in names {
                    let (member, alias) = self.aliased(name);
                    let local = alias.unwrap_or_else(|| member.clone());
                    self.push_use(local, format!("{base}{member}"));
                }
            }
            _ => {}
        }
        let toks: Vec<NodeId> = leaves(n, is_comment)
            .into_iter()
            .map(|l| self.cx.lit(l.kind(), self.t(l), l))
            .collect::<R<_>>()?;
        self.cx
            .op(Operator::adapter("python", "import", Sort::Exp), n, &toks)
    }

    /// The `(name, alias)` of an import entry (`a.b as c`).
    fn aliased(&self, n: Node<'_>) -> (String, Option<String>) {
        if n.kind() == "aliased_import" {
            let name = n
                .child_by_field_name("name")
                .map(|m| self.dotted(m))
                .unwrap_or_default();
            let alias = n.child_by_field_name("alias").map(|a| self.t(a).to_owned());
            (name, alias)
        } else {
            (self.dotted(n), None)
        }
    }

    // ---- units ----

    fn doc_node(&mut self, s: Node<'_>) -> R<NodeId> {
        let text = docstring_text(self.cx.text, s);
        let payload = self.cx.lit("str", &text, s)?;
        self.cx.op(Operator::attr("doc"), s, &[payload])
    }

    /// One `attr` node for decorator `d`: its name is the dotted callee, its payload the call arguments.
    fn decorator_attr(&mut self, d: Node<'_>) -> R<NodeId> {
        let expr = children(d)
            .into_iter()
            .find(|c| c.is_named() && !is_comment(*c));
        let (name, args) = match expr {
            Some(e) if e.kind() == "call" => (
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

    fn decorated(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let decorators: Vec<Node<'_>> = children(n)
            .into_iter()
            .filter(|c| c.kind() == "decorator")
            .collect();
        match n.child_by_field_name("definition") {
            Some(d) if d.kind() == "class_definition" => self.class_unit(d, n, &decorators, depth),
            Some(d) if d.kind() == "function_definition" => self.def_unit(d, n, &decorators, depth),
            _ => self.generic(n, depth),
        }
    }

    /// The signature tokens of `parts` (fields of `def`) in token mode.
    fn sig_tokens(&mut self, name: Option<Node<'_>>, parts: &[Option<Node<'_>>]) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        if let Some(n) = name {
            out.push(self.cx.lit("name", self.t(n), n)?);
        }
        for p in parts.iter().flatten() {
            for l in leaves(*p, is_comment) {
                out.push(self.cx.lit(l.kind(), self.t(l), l)?);
            }
        }
        Ok(out)
    }

    /// Builds a unit with its doc, decorator, sig and body children.
    #[allow(
        clippy::too_many_arguments,
        reason = "one unit constructor, inputs distinct"
    )]
    fn make_unit(
        &mut self,
        ord: usize,
        span: Node<'_>,
        (kind, name, vis): (&str, &str, &str),
        doc: Option<NodeId>,
        decorators: &[Node<'_>],
        sig: Vec<NodeId>,
        body: Vec<NodeId>,
        binders: &[String],
    ) -> R<NodeId> {
        let mut kids = Vec::new();
        kids.extend(doc);
        let mut sig_kids = Vec::new();
        for d in decorators {
            kids.push(self.decorator_attr(*d)?);
            sig_kids.push(self.decorator_attr(*d)?);
        }
        sig_kids.extend(sig);
        let sig_group = NodeSpec::new(
            Operator::group(GroupOrder::Sequence),
            self.cx.node_loc(span),
        )
        .attr(reserved::FACET, "sig");
        kids.push(self.cx.add(sig_group, &sig_kids)?);
        kids.extend(body);
        let names: Vec<&str> = binders.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::unit(kind, "impl"), self.cx.node_loc(span))
            .named(name)
            .binders(&names)
            .attr(ATTR_VISIBILITY, vis);
        let id = self.cx.add(spec, &kids)?;
        self.ord_nodes[ord] = Some(id);
        tracing::trace!(path = self.path, kind, name, "python unit");
        Ok(id)
    }

    /// The body statements of `block` as one group, docstring excluded, in the current scope.
    fn body_group(&mut self, block: Node<'_>, stmts: &[Node<'_>], depth: usize) -> R<NodeId> {
        let mut nodes = Vec::new();
        for s in stmts {
            nodes.push(self.with_expr(true, |f| f.tr(*s, depth + 1))?);
        }
        self.cx
            .op(Operator::group(GroupOrder::Sequence), block, &nodes)
    }

    fn def_unit(
        &mut self,
        def: Node<'_>,
        span: Node<'_>,
        decorators: &[Node<'_>],
        depth: usize,
    ) -> R<NodeId> {
        let (Some(name_node), Some(block)) = (
            def.child_by_field_name("name"),
            def.child_by_field_name("body"),
        ) else {
            return self.generic(def, depth);
        };
        let name = self.t(name_node).to_owned();
        let in_class = self.units.last().is_some_and(|u| u.1);
        let in_function = !self.units.is_empty() && !in_class;
        let params = def.child_by_field_name("parameters");
        // Decorators and defaults run in the enclosing scope.
        for d in decorators {
            self.scan_calls(*d);
        }
        if let Some(p) = params {
            self.scan_calls(p);
        }
        let sig = self.with_expr(false, |f| {
            f.sig_tokens(
                Some(name_node),
                &[params, def.child_by_field_name("return_type")],
            )
        })?;
        let (doc, stmts) = split_docstring(children(block));
        let doc_id = match doc.and_then(docstring_of) {
            Some(s) => Some(self.doc_node(s)?),
            None => None,
        };
        let mut seed = Vec::new();
        if let Some(p) = params {
            param_names(p, self.cx.text, &mut seed);
        }
        let binders = scope_binders(seed, &stmts, self.cx.text);
        let ord = self.alloc();
        self.units.push((ord, false));
        self.bound.push(binders.iter().cloned().collect());
        let body = self.body_group(block, &stmts, depth);
        self.bound.pop();
        self.units.pop();
        let kind = if in_class { "method" } else { "function" };
        self.make_unit(
            ord,
            span,
            (kind, &name, visibility_text(&name, in_function)),
            doc_id,
            decorators,
            sig,
            vec![body?],
            &binders,
        )
    }

    fn class_unit(
        &mut self,
        def: Node<'_>,
        span: Node<'_>,
        decorators: &[Node<'_>],
        depth: usize,
    ) -> R<NodeId> {
        let (Some(name_node), Some(block)) = (
            def.child_by_field_name("name"),
            def.child_by_field_name("body"),
        ) else {
            return self.generic(def, depth);
        };
        let name = self.t(name_node).to_owned();
        let in_function = self.units.last().is_some_and(|u| !u.1);
        let supers = def.child_by_field_name("superclasses");
        for d in decorators {
            self.scan_calls(*d);
        }
        if let Some(s) = supers {
            self.scan_calls(s);
        }
        let sig = self.with_expr(false, |f| f.sig_tokens(Some(name_node), &[supers]))?;
        let (doc, stmts) = split_docstring(children(block));
        let doc_id = match doc.and_then(docstring_of) {
            Some(s) => Some(self.doc_node(s)?),
            None => None,
        };
        let ord = self.alloc();
        self.units.push((ord, true));
        let body = self.body_group(block, &stmts, depth);
        self.units.pop();
        self.make_unit(
            ord,
            span,
            ("class", &name, visibility_text(&name, in_function)),
            doc_id,
            decorators,
            sig,
            vec![body?],
            &[],
        )
    }

    fn lambda(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut names = Vec::new();
        if let Some(p) = n.child_by_field_name("parameters") {
            param_names(p, self.cx.text, &mut names);
            self.scan_calls(p);
        }
        names.sort();
        names.dedup();
        self.bound.push(names.iter().cloned().collect());
        let body = n
            .child_by_field_name("body")
            .map(|b| self.with_expr(true, |f| f.tr(b, depth + 1)));
        self.bound.pop();
        let kids: Vec<NodeId> = body.transpose()?.into_iter().collect();
        let refs: Vec<&str> = names.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::anon("lambda"), self.cx.node_loc(n)).binders(&refs);
        self.cx.add(spec, &kids)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fold_src(path: &str, src: &str) -> Folded {
        let a = PythonAdapter;
        let tree = a.parse(src, &ParseLimits::default());
        let input = FileInput {
            path,
            digest: "d",
            size: u32::try_from(src.len()).expect("small"),
        };
        a.fold(&tree, &input).expect("fold")
    }

    fn names(f: &Folded) -> Vec<String> {
        f.file
            .symbols
            .iter()
            .map(|s| s.symref.to_string())
            .collect()
    }

    const SAMPLE: &str = "\"\"\"Module doc.\"\"\"\nimport os\nfrom . import util\nfrom .sub.mod import helper as h\n\n\n@decorator(1)\ndef top(a, b=2):\n    \"\"\"Doc.\"\"\"\n    x = h(a)\n    x()\n    util.run(x)\n    return os.path.join(a)\n\n\nclass Thing(Base):\n    def method(self):\n        self.other()\n        def inner():\n            pass\n        inner()\n\n    def other(self):\n        pass\n";

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::fold_tree
    fn units_nest_and_carry_kinds() {
        let f = fold_src("pkg/a.py", SAMPLE);
        assert_eq!(
            names(&f),
            [
                "pkg/a.py::top",
                "pkg/a.py::Thing",
                "pkg/a.py::Thing.method",
                "pkg/a.py::Thing.method.inner",
                "pkg/a.py::Thing.other"
            ]
        );
        let kinds: Vec<SymbolKind> = f.file.symbols.iter().map(|s| s.kind).collect();
        assert_eq!(
            kinds,
            [
                SymbolKind::Function,
                SymbolKind::Class,
                SymbolKind::Method,
                SymbolKind::Function,
                SymbolKind::Method
            ]
        );
        assert!(f.file.parse_status.is_complete());
    }

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::Fold.record_call
    fn calls_carry_qualifiers_and_locals() {
        let f = fold_src("pkg/a.py", SAMPLE);
        let calls: Vec<(String, String, Option<String>, bool, crate::LocalBinding)> = f
            .file
            .calls
            .iter()
            .map(|c| {
                (
                    c.caller.to_string(),
                    c.callee.clone(),
                    c.qualifier.clone(),
                    c.method,
                    c.local,
                )
            })
            .collect();
        let top = "pkg/a.py::top".to_owned();
        assert!(calls.contains(&(
            top.clone(),
            "h".into(),
            None,
            false,
            crate::LocalBinding::None
        )));
        assert!(calls.contains(&(
            top.clone(),
            "x".into(),
            None,
            false,
            crate::LocalBinding::Value
        )));
        assert!(calls.contains(&(
            top.clone(),
            "run".into(),
            Some("util".into()),
            false,
            crate::LocalBinding::None
        )));
        assert!(calls.contains(&(
            top,
            "join".into(),
            Some("path".into()),
            false,
            crate::LocalBinding::None
        )));
        let m = "pkg/a.py::Thing.method".to_owned();
        assert!(calls.contains(&(m, "other".into(), None, true, crate::LocalBinding::None)));
        let c = f
            .file
            .calls
            .iter()
            .find(|c| c.callee == "other")
            .expect("call");
        assert_eq!(c.receiver, Some(Receiver::SelfValue));
    }

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::Fold.import
    fn imports_become_use_bindings() {
        let f = fold_src("pkg/a.py", SAMPLE);
        let uses: Vec<(String, String)> = f
            .file
            .uses
            .iter()
            .map(|u| (u.local.clone(), u.target.clone()))
            .collect();
        assert!(uses.contains(&("os".into(), "os".into())));
        assert!(uses.contains(&("util".into(), ".util".into())));
        assert!(uses.contains(&("h".into(), ".sub.mod.helper".into())));
    }

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::fold_tree
    fn visibility_follows_underscores_and_docs_split_from_body() {
        let src = "def _hidden():\n    pass\n\ndef shown():\n    \"\"\"d\"\"\"\n    return 1\n\ndef shown2():\n    return 1\n";
        let f = fold_src("m.py", src);
        let vis: Vec<_> = f.file.symbols.iter().map(|s| s.visibility).collect();
        assert_eq!(
            vis,
            [
                crate::Visibility::Private,
                crate::Visibility::Public,
                crate::Visibility::Public
            ]
        );
        let (a, b) = (&f.file.symbols[1], &f.file.symbols[2]);
        assert_ne!(a.digests.doc, b.digests.doc);
        assert_eq!(a.digests.body, b.digests.body);
    }

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::Fold.tr
    fn match_statement_is_reported_unmodelled() {
        let src = "def f(x):\n    match x:\n        case 1:\n            g()\n";
        let f = fold_src("m.py", src);
        assert!(matches!(
            f.file.parse_status,
            crate::ParseStatus::Partial { holes: 1 }
        ));
    }

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::is_python_test_fn
    fn test_naming_convention() {
        let f = fold_src(
            "tests/test_x.py",
            "def test_a():\n    pass\nclass TestB:\n    def test_c(self):\n        pass\n    def helper(self):\n        pass\n",
        );
        let tests: Vec<String> = f
            .file
            .symbols
            .iter()
            .filter(|s| is_python_test_fn(s))
            .map(|s| s.symref.to_string())
            .collect();
        assert_eq!(
            tests,
            ["tests/test_x.py::test_a", "tests/test_x.py::TestB.test_c"]
        );
        assert!(is_python_test_file("pkg/tests/helpers.py"));
        assert!(is_python_test_file("conftest.py"));
        assert!(!is_python_test_file("pkg/main.py"));
        assert!(!is_python_test_module("pkg/helpers.py"));
    }

    #[test]
    // frob:tests crates/gob-symbols/src/python.rs::Fold.collapse
    fn deep_nesting_collapses_without_losing_calls() {
        let expr = (0..400).map(|_| "1").collect::<Vec<_>>().join(" + ");
        let src = format!("def f():\n    x = {expr}\n    g()\n");
        let f = fold_src("m.py", &src);
        assert!(f.file.calls.iter().any(|c| c.callee == "g"));
    }
}
