//! The Rust adapter (fidelity F3): tree-sitter tree to a U term plus scope graph.
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`; items are `unit(kind, role)` children with
//!   role `impl` (a definition) or `sig` (a bodiless declaration). Impl members are
//!   children of the impl unit (`Type[Trait].member`); enum variants children of
//!   the enum. `mod`, `trait`, `struct`, `enum`, `const`, `static`, `type` and
//!   `macro_rules!` are units too.
//! - Every unit has children in four groups: `attr("doc")` (Doc facet), other
//!   `attr` nodes (Attr facet), a `group` marked `ir.facet = "sig"` holding the
//!   signature tokens and a copy of the outer attributes (G7), and the body.
//! - Parameters are the binders of the function unit; `let`, `for`, `if let`,
//!   `while let` and match arms are `bind` nodes whose scope is the code they
//!   cover; closures are `anon(closure)`; nested `fn` items are `anon(fn)`.
//! - Identifiers in expression position are `ref`s; calls are `apply(call)`
//!   (`apply(method)` for method calls, `apply(construct)` for tuple
//!   constructors); macro invocations are `phase(macro)` over their tokens;
//!   `unsafe` blocks are `region(unsafe)`; `use` is the adapter operator `rust.use`;
//!   syntax errors are `hole(parse-error)` nodes.
//! - Everything else maps to the adapter operator `rust.<tree-sitter kind>` over
//!   its children, with leaves as `lit`s: a token change always changes the
//!   stream, reformatting and comments never do (G8).
//! - Subtrees deeper than [`RustAdapter::MAX_DEPTH`] collapse into one `opaque(depth-limit)`
//!   holding their tokens, because the gob-ir printer recurses over term depth.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::cell::RefCell;
use std::collections::HashSet;

use gob_ir::{
    GroupOrder, NodeId, NodeSpec, Operator, Resolution, ScopeGraph, Sort, TermError, reserved,
};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
    Precision,
};
use crate::fold::{Cx, base_file, failed_file, file_root_spec};
use crate::model::{
    CallRef, CallSite, FieldDecl, ImportEdge, LocalBinding, Receiver, RefKind, RefSite, RetType,
    SelfKind, UseBinding, Visibility, collapse_ws,
};
use crate::paths::crate_and_module;
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{
    self, ATTR_ARITY, ATTR_IMPLEMENTS, ATTR_RET, ATTR_RET_ARG, ATTR_SELF_KIND, ATTR_VISIBILITY,
    HOLE_MISSING, HOLE_PARSE_ERROR, Naming,
};

/// Deepest term nesting before a subtree collapses into one opaque node.
const MAX_DEPTH: usize = 160;

type R<T> = Result<T, TermError>;

/// The Rust adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct RustAdapter;

impl RustAdapter {
    /// Deepest term nesting before a subtree collapses into one opaque node.
    pub const MAX_DEPTH: usize = MAX_DEPTH;
}

impl Adapter for RustAdapter {
    fn language(&self) -> &'static str {
        "rust"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Rust)
        )
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F3
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
            .with(Capability::ResolveRef, Precision::LexicalImports)
            .with(Capability::ApplyTargets, Precision::ByNameInCrate)
            .with(Capability::Visibility, Precision::Keyword)
            .with(Capability::Imports, Precision::Syntactic)
            .with(Capability::TestItems, Precision::Syntactic)
            .with(Capability::Order, Precision::Declared)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Rust, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "rust", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "rust",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// Where the item being visited lives.
#[derive(Clone, Default)]
struct Scope {
    /// Inside an impl or trait: functions are methods.
    member: bool,
    /// Visibility inherited by members without a modifier (trait items, variants).
    inherit: Option<Visibility>,
    /// The trait text of the enclosing `impl Trait for Type`.
    implements: Option<String>,
    /// Inside a trait impl: members without a modifier are public.
    trait_impl: bool,
}

/// Leading doc comments, attributes and plain comments waiting for their item.
#[derive(Default)]
struct Lead<'t> {
    docs: Vec<Node<'t>>,
    attrs: Vec<Node<'t>>,
    comments: Vec<Node<'t>>,
}

enum SiteKind {
    Call { method: bool, in_macro: bool },
    Value,
}

struct Site {
    kind: SiteKind,
    caller: usize,
    name: String,
    qualifier: Option<String>,
    node: Option<NodeId>,
    item_local: bool,
    /// Method-call receiver; `None` for non-method sites.
    receiver: Option<Receiver>,
    /// The qualifying path is a generic parameter or bracketed type.
    opaque: bool,
    /// The std macro whose arguments were parsed as ordinary expressions around this call.
    macro_exact: Option<String>,
    /// Call argument count, receiver excluded (`None` inside macro arguments).
    args: Option<usize>,
    /// The full qualifying path segments of a path call.
    qual_path: Vec<String>,
    /// One-based source line.
    line: u32,
    /// The callee expression as written.
    text: String,
}

struct PendingUse {
    container: Option<usize>,
    local: String,
    target: String,
    public: bool,
}

/// What a call's function expression is, read from the syntax alone.
#[allow(
    clippy::struct_excessive_bools,
    reason = "construct/dynamic/method/opaque are independent syntactic facts of one call head"
)]
struct CallTarget {
    name: String,
    qualifier: Option<String>,
    method: bool,
    construct: bool,
    dynamic: bool,
    receiver: Option<Receiver>,
    opaque: bool,
    /// The full qualifying path segments, generics stripped (`frob_ack::inputs`).
    path: Vec<String>,
}

/// Wrapper types whose methods are reached by auto-deref: a declared type of these says nothing about the callee.
const DEREF_WRAPPERS: &[&str] = &[
    "Box",
    "Rc",
    "Arc",
    "Cow",
    "Pin",
    "Ref",
    "RefMut",
    "RefCell",
    "Mutex",
    "RwLock",
    "MutexGuard",
    "RwLockReadGuard",
    "RwLockWriteGuard",
    "ManuallyDrop",
    "Self",
];

/// Std and `tracing` macros whose arguments are ordinary expressions (calls in them resolve like any other).
const EXACT_MACROS: &[&str] = &[
    "assert",
    "assert_eq",
    "assert_ne",
    "debug_assert",
    "debug_assert_eq",
    "debug_assert_ne",
    "format",
    "format_args",
    "print",
    "println",
    "eprint",
    "eprintln",
    "write",
    "writeln",
    "panic",
    "unreachable",
    "todo",
    "unimplemented",
    "dbg",
    "info",
    "debug",
    "warn",
    "error",
    "trace",
];

/// `c` blanked for the synthetic text: newlines stay so line numbers match.
fn blank(c: u8) -> u8 {
    if c == b'\n' { b'\n' } else { b' ' }
}

/// The call expression `f(..)` of the synthetic wrapper whose callee starts at byte `at`.
fn find_synthetic_call(root: Node<'_>, at: usize) -> Option<Node<'_>> {
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        if n.kind() == "call_expression"
            && n.child_by_field_name("function")
                .is_some_and(|f| f.start_byte() == at)
        {
            return Some(n);
        }
        stack.extend(children(n));
    }
    None
}

/// True when `n` sits inside a macro invocation of the synthetic tree (its own scan handles it).
fn inside_macro(n: Node<'_>) -> bool {
    let mut cur = n.parent();
    while let Some(p) = cur {
        if p.kind() == "macro_invocation" {
            return true;
        }
        cur = p.parent();
    }
    false
}

/// Longest callee text kept for diagnostics.
const MAX_CALL_TEXT: usize = 80;

fn call_text(raw: &str) -> String {
    let mut t = collapse_ws(raw);
    if t.chars().count() > MAX_CALL_TEXT {
        t = t.chars().take(MAX_CALL_TEXT).collect();
        t.push_str("...");
    }
    format!("{t}(..)")
}

struct Fold<'a> {
    cx: Cx<'a>,
    path: &'a str,
    module: Vec<String>,
    /// Identifiers are references (expression context) rather than tokens.
    expr: bool,
    /// Depth of enclosing function bodies (uses inside are not file imports).
    fn_depth: usize,
    ord_nodes: Vec<Option<NodeId>>,
    callers: Vec<usize>,
    unit_stack: Vec<usize>,
    locals: Vec<String>,
    sites: Vec<Site>,
    uses: Vec<PendingUse>,
    /// Variables in scope with their declared type when syntactically evident (latest wins).
    env: RefCell<Vec<(String, Option<Receiver>)>>,
    /// Generic parameter names of the enclosing items.
    generics: Vec<String>,
    /// Trait bounds of the generic parameters in scope, as (parameter, trait names), innermost last.
    bounds: Vec<(String, Vec<String>)>,
    /// The calling shape of the function about to become a unit (taken by `make_unit`).
    fn_sig: Option<(SelfKind, usize, Option<RetType>)>,
    /// Struct fields with a concrete declared type.
    fields: Vec<FieldDecl>,
}

/// One-based source line of `n`.
fn line_of(n: Node<'_>) -> u32 {
    u32::try_from(n.start_position().row + 1).unwrap_or(u32::MAX)
}

fn text_of<'t>(text: &'t str, n: Node<'_>) -> &'t str {
    &text[n.start_byte()..n.end_byte()]
}

fn children(n: Node<'_>) -> Vec<Node<'_>> {
    let mut c = n.walk();
    n.children(&mut c).collect()
}

fn is_comment(n: Node<'_>) -> bool {
    matches!(n.kind(), "line_comment" | "block_comment")
}

fn upper_first(s: &str) -> bool {
    s.chars().next().is_some_and(char::is_uppercase)
}

/// Removes `<...>` generic arguments (nesting-aware).
fn strip_generics(s: &str) -> String {
    let mut depth = 0u32;
    let mut out = String::new();
    for ch in s.chars() {
        match ch {
            '<' => depth += 1,
            '>' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(ch),
            _ => {}
        }
    }
    out
}

fn split_path(s: &str) -> Vec<String> {
    strip_generics(s)
        .split("::")
        .map(|p| p.split_whitespace().collect::<String>())
        .filter(|p| !p.is_empty())
        .collect()
}

fn vis_text(v: Visibility) -> &'static str {
    match v {
        Visibility::Public => "public",
        Visibility::Crate => "crate",
        Visibility::Private => "private",
    }
}

/// All leaf tokens of `n` in source order, comments skipped.
fn leaves<'t>(n: Node<'t>) -> Vec<Node<'t>> {
    let mut out = Vec::new();
    let mut stack = vec![n];
    while let Some(x) = stack.pop() {
        if is_comment(x) {
            continue;
        }
        if x.child_count() == 0 {
            out.push(x);
        } else {
            let mut c = x.walk();
            let kids: Vec<Node<'t>> = x.children(&mut c).collect();
            stack.extend(kids.into_iter().rev());
        }
    }
    out
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let (_, module) = crate_and_module(input.path);
    let mut f = Fold {
        cx: Cx::new(input.path, "rust", text),
        path: input.path,
        module,
        expr: false,
        fn_depth: 0,
        ord_nodes: Vec::new(),
        callers: Vec::new(),
        unit_stack: Vec::new(),
        locals: Vec::new(),
        sites: Vec::new(),
        uses: Vec::new(),
        env: RefCell::new(Vec::new()),
        generics: Vec::new(),
        bounds: Vec::new(),
        fn_sig: None,
        fields: Vec::new(),
    };
    let kids = f.container(root, &Scope::default(), true)?;
    let root_id =
        f.cx.add(file_root_spec(&f.cx, input.size as usize), &kids)?;
    let Fold {
        cx,
        ord_nodes,
        sites,
        uses,
        fields,
        ..
    } = f;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Rust);
    let mut file = base_file(input, "rust");
    file.fidelity = Fidelity::F3;
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
            target: u.target.clone(),
        });
        file.uses.push(UseBinding {
            from_file: input.path.to_owned(),
            local: u.local,
            target: u.target,
            public: u.public,
            container: u.container.and_then(symref_of),
        });
    }
    for s in sites {
        let Some(caller) = symref_of(s.caller) else {
            continue;
        };
        match s.kind {
            SiteKind::Call { method, in_macro } => {
                let local = local_binding(&scopes, s.node, s.item_local);
                file.calls.push(CallSite {
                    caller,
                    callee: s.name,
                    qualifier: s.qualifier,
                    method,
                    local,
                    in_macro,
                    receiver: s.receiver,
                    opaque_qualifier: s.opaque,
                    macro_exact: s.macro_exact,
                    args: s.args,
                    qual_path: s.qual_path,
                    line: s.line,
                    text: s.text,
                });
            }
            SiteKind::Value => file.refs.push(RefSite {
                from: caller,
                name: s.name,
                qualifier: s.qualifier,
                kind: RefKind::Value,
            }),
        }
    }
    file.symbols = v.symbols;
    file.extras = v.extras;
    file.fields = fields;
    tracing::debug!(
        path = input.path,
        symbols = file.symbols.len(),
        calls = file.calls.len(),
        refs = file.refs.len(),
        status = ?file.parse_status,
        "rust file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// What the file's scope graph says about the callee reference at `node`.
fn local_binding(scopes: &ScopeGraph, node: Option<NodeId>, item_local: bool) -> LocalBinding {
    let Some(r) = node.and_then(|n| scopes.ref_at(n)) else {
        return LocalBinding::None;
    };
    let is_binder = |d| scopes.decl(d).kind == gob_ir::DeclKind::Binder;
    let bound = match scopes.resolve(r) {
        Resolution::Must(d) => is_binder(d),
        Resolution::May(ds) => ds.iter().all(|&d| is_binder(d)),
        Resolution::Unknown => false,
    };
    match (bound, item_local) {
        (false, _) => LocalBinding::None,
        (true, true) => LocalBinding::Item,
        (true, false) => LocalBinding::Value,
    }
}

/// Kinds whose identifiers are tokens, not references.
fn token_kind(kind: &str) -> bool {
    (kind.contains("type") && kind != "type_cast_expression")
        || matches!(
            kind,
            "where_clause"
                | "trait_bounds"
                | "attribute_item"
                | "inner_attribute_item"
                | "attribute"
                | "lifetime"
                | "visibility_modifier"
                | "token_tree"
                | "label"
        )
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

    // ---- generic translation ----

    fn hole(&mut self, n: Node<'_>) -> R<NodeId> {
        let kind = if n.is_missing() {
            HOLE_MISSING
        } else {
            HOLE_PARSE_ERROR
        };
        tracing::debug!(path = self.path, kind, at = n.start_byte(), "rust hole");
        self.cx.op(Operator::hole(kind), n, &[])
    }

    fn comment(&mut self, n: Node<'_>) -> R<NodeId> {
        let text = self.t(n).to_owned();
        self.cx.op(Operator::comment(&text), n, &[])
    }

    fn collapse(&mut self, nodes: &[Node<'_>]) -> R<NodeId> {
        let mut toks: Vec<&str> = Vec::new();
        for n in nodes {
            for l in leaves(*n) {
                toks.push(self.t(l));
            }
            self.scan_calls(*n);
        }
        let payload = toks.join(" ");
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
            Operator::opaque("depth-limit", payload.as_bytes()),
            self.cx.loc(start, end),
        );
        self.cx.add(spec, &[])
    }

    /// Records the calls inside a collapsed subtree (no term nodes exist for them).
    fn scan_calls(&mut self, root: Node<'_>) {
        let Some(&caller) = self.callers.last() else {
            return;
        };
        let mut stack = vec![root];
        while let Some(n) = stack.pop() {
            if n.kind() == "call_expression"
                && let Some(f) = n.child_by_field_name("function")
            {
                let t = self.call_target(f);
                if !t.construct {
                    self.sites.push(Site {
                        kind: SiteKind::Call {
                            method: t.method,
                            in_macro: false,
                        },
                        caller,
                        name: t.name,
                        qualifier: t.qualifier,
                        node: None,
                        item_local: false,
                        receiver: t.receiver,
                        opaque: t.opaque,
                        macro_exact: None,
                        args: Some(Self::arg_count(n)),
                        qual_path: t.path,
                        line: line_of(n),
                        text: call_text(self.t(f)),
                    });
                }
            }
            if n.kind() == "macro_invocation" {
                self.scan_macro(n, caller);
            } else {
                stack.extend(children(n));
            }
        }
    }

    fn tr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        if depth > MAX_DEPTH {
            return self.collapse(&[n]);
        }
        let kind = n.kind();
        if is_comment(n) {
            return self.comment(n);
        }
        if n.is_error() || n.is_missing() {
            return self.hole(n);
        }
        match kind {
            "identifier" if self.expr => self.ident_ref(n),
            "self" if self.expr => self.cx.op(Operator::reference("self"), n, &[]),
            "scoped_identifier" if self.expr => self.path_ref(n),
            "call_expression" if self.expr => self.call(n, depth),
            "macro_invocation" => self.macro_call(n),
            "block" => self.block(n, depth),
            "unsafe_block" => {
                let kids = self.gen_children(n, depth)?;
                self.cx.op(Operator::region("unsafe"), n, &kids)
            }
            "closure_expression" => self.closure(n, depth),
            "match_expression" => self.match_expr(n, depth),
            "for_expression" => self.for_expr(n, depth),
            "if_expression" | "while_expression" => self.cond_expr(n, depth),
            "let_condition" => self.let_condition(n, depth),
            "use_declaration" => self.use_node(n),
            "function_item" => self.nested_fn(n, depth),
            _ if token_kind(kind) => self.with_expr(false, |s| s.generic(n, depth)),
            _ => self.generic(n, depth),
        }
    }

    fn generic(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        if n.child_count() == 0 {
            return self.cx.lit(n.kind(), self.t(n), n);
        }
        let kids = self.gen_children(n, depth)?;
        let op = Operator::adapter("rust", n.kind(), Sort::Exp);
        self.cx.op(op, n, &kids)
    }

    fn gen_children(&mut self, n: Node<'_>, depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for c in children(n) {
            out.push(self.tr(c, depth + 1)?);
        }
        Ok(out)
    }

    fn ident_ref(&mut self, n: Node<'_>) -> R<NodeId> {
        let name = self.t(n);
        let id = self.cx.op(Operator::reference(name), n, &[])?;
        if !upper_first(name) {
            self.value_site(name, None, id);
        }
        Ok(id)
    }

    fn path_ref(&mut self, n: Node<'_>) -> R<NodeId> {
        let segs = split_path(self.t(n));
        let text = segs.join("::");
        let id = self.cx.op(Operator::reference(&text), n, &[])?;
        if let Some((leaf, rest)) = segs.split_last()
            && !upper_first(leaf)
        {
            self.value_site(leaf, rest.last().cloned(), id);
        }
        Ok(id)
    }

    fn value_site(&mut self, name: &str, qualifier: Option<String>, node: NodeId) {
        let Some(&caller) = self.callers.last() else {
            return;
        };
        let item_local = self.locals.iter().any(|l| l == name);
        self.sites.push(Site {
            kind: SiteKind::Value,
            caller,
            name: name.to_owned(),
            qualifier,
            node: Some(node),
            item_local,
            receiver: None,
            opaque: false,
            macro_exact: None,
            args: None,
            qual_path: Vec::new(),
            line: 0,
            text: String::new(),
        });
    }

    // ---- calls and macros ----

    fn call_target(&self, f: Node<'_>) -> CallTarget {
        let dynamic = || CallTarget {
            name: String::new(),
            qualifier: None,
            method: false,
            construct: false,
            dynamic: true,
            receiver: None,
            opaque: false,
            path: Vec::new(),
        };
        match f.kind() {
            "identifier" => {
                let name = self.t(f).to_owned();
                CallTarget {
                    construct: upper_first(&name),
                    name,
                    qualifier: None,
                    method: false,
                    dynamic: false,
                    receiver: None,
                    opaque: false,
                    path: Vec::new(),
                }
            }
            "scoped_identifier" => {
                let Some(leaf) = f.child_by_field_name("name").map(|n| self.t(n).to_owned()) else {
                    return dynamic();
                };
                let path = f.child_by_field_name("path");
                let qualifier = path.and_then(|p| {
                    strip_generics(self.t(p))
                        .rsplit("::")
                        .next()
                        .map(str::to_owned)
                });
                let opaque = path.is_some_and(|p| {
                    !matches!(
                        p.kind(),
                        "identifier"
                            | "scoped_identifier"
                            | "self"
                            | "crate"
                            | "super"
                            | "generic_type"
                            | "generic_type_with_turbofish"
                    )
                }) || qualifier
                    .as_ref()
                    .is_some_and(|q| self.generics.contains(q));
                CallTarget {
                    construct: upper_first(&leaf),
                    name: leaf,
                    qualifier,
                    method: false,
                    dynamic: false,
                    receiver: None,
                    opaque,
                    path: path.map(|p| split_path(self.t(p))).unwrap_or_default(),
                }
            }
            "field_expression" => match f.child_by_field_name("field") {
                Some(n) => CallTarget {
                    name: self.t(n).to_owned(),
                    qualifier: None,
                    method: true,
                    construct: false,
                    dynamic: false,
                    receiver: Some(self.receiver_of(f.child_by_field_name("value"))),
                    opaque: false,
                    path: Vec::new(),
                },
                None => dynamic(),
            },
            "generic_function" => f
                .child_by_field_name("function")
                .map_or_else(dynamic, |inner| self.call_target(inner)),
            _ => dynamic(),
        }
    }

    /// The receiver kind of a method call: `self`, a typed local, or an unknown expression.
    fn receiver_of(&self, value: Option<Node<'_>>) -> Receiver {
        let Some(v) = value else {
            return Receiver::Expr;
        };
        match v.kind() {
            "self" => Receiver::SelfValue,
            "identifier" => {
                let name = self.t(v);
                self.env
                    .borrow()
                    .iter()
                    .rev()
                    .find(|(n, _)| n == name)
                    .and_then(|(_, t)| t.clone())
                    .unwrap_or(Receiver::Expr)
            }
            "parenthesized_expression" | "reference_expression" => {
                let inner = if v.kind() == "reference_expression" {
                    v.child_by_field_name("value")
                } else {
                    children(v).into_iter().find(tree_sitter::Node::is_named)
                };
                self.receiver_of(inner)
            }
            "try_expression" => {
                match self.receiver_of(children(v).into_iter().find(tree_sitter::Node::is_named)) {
                    Receiver::Expr => Receiver::Expr,
                    inner => Receiver::Unwrap(Box::new(inner)),
                }
            }
            "call_expression" => self.call_receiver(v),
            "field_expression" => {
                let field = v.child_by_field_name("field");
                match (self.receiver_of(v.child_by_field_name("value")), field) {
                    (Receiver::Expr, _) | (_, None) => Receiver::Expr,
                    (base, Some(f)) if f.kind() == "field_identifier" => {
                        Receiver::Field(Box::new(base), self.t(f).to_owned())
                    }
                    _ => Receiver::Expr,
                }
            }
            _ => Receiver::Expr,
        }
    }

    /// The receiver standing for the value of the call expression `v`: its callee, for a return-type lookup.
    fn call_receiver(&self, v: Node<'_>) -> Receiver {
        let Some(f) = v.child_by_field_name("function") else {
            return Receiver::Expr;
        };
        let f = if f.kind() == "generic_function" {
            f.child_by_field_name("function").unwrap_or(f)
        } else {
            f
        };
        let t = self.call_target(f);
        let args = Self::arg_count(v);
        if t.dynamic || t.opaque || t.construct {
            return Receiver::Expr;
        }
        if t.method {
            let Some(
                Receiver::SelfValue
                | Receiver::Typed(_)
                | Receiver::Field(..)
                | Receiver::Ret(_)
                | Receiver::Unwrap(_),
            ) = t.receiver.as_ref()
            else {
                return Receiver::Expr;
            };
            let recv = t.receiver;
            if matches!(t.name.as_str(), "unwrap" | "expect") && args <= 1 {
                return recv.map_or(Receiver::Expr, |r| Receiver::Unwrap(Box::new(r)));
            }
            return Receiver::Ret(Box::new(CallRef {
                name: t.name,
                path: Vec::new(),
                recv,
                args,
            }));
        }
        let bound =
            self.env.borrow().iter().any(|(n, _)| *n == t.name) || self.locals.contains(&t.name);
        if bound && t.path.is_empty() {
            return Receiver::Expr;
        }
        Receiver::Ret(Box::new(CallRef {
            name: t.name,
            path: t.path,
            recv: None,
            args,
        }))
    }

    /// The receiver a `let` value evidently has: a struct literal, `Type::new`/`Type::default`, or a typed expression.
    fn value_receiver(&self, v: Node<'_>) -> Option<Receiver> {
        if let Some(t) = self.value_type(v) {
            return Some(Receiver::Typed(t));
        }
        match self.receiver_of(Some(v)) {
            Receiver::Expr => None,
            r => Some(r),
        }
    }

    /// A declared return type reduced to its plain head and first generic argument.
    fn ret_type(&self, t: Node<'_>) -> Option<RetType> {
        let name = |n: Node<'_>| -> Option<String> {
            if n.kind() == "type_identifier" && self.t(n) == "Self" {
                return Some("Self".to_owned());
            }
            self.plain_type(n)
        };
        match t.kind() {
            "reference_type" => self.ret_type(t.child_by_field_name("type")?),
            "generic_type" => {
                let head = name(t.child_by_field_name("type")?)?;
                let arg = t
                    .child_by_field_name("type_arguments")
                    .and_then(|a| {
                        children(a)
                            .into_iter()
                            .find(|c| c.is_named() && c.kind() != "lifetime")
                    })
                    .and_then(name);
                Some(RetType { head, arg })
            }
            _ => Some(RetType {
                head: name(t)?,
                arg: None,
            }),
        }
    }

    /// Number of arguments in the call expression `n` (comments excluded).
    fn arg_count(n: Node<'_>) -> usize {
        n.child_by_field_name("arguments").map_or(0, |a| {
            children(a)
                .into_iter()
                .filter(|c| c.is_named() && !is_comment(*c))
                .count()
        })
    }

    /// The plain type named by `t` (through references), when it says what a method call on it reaches.
    fn plain_type(&self, t: Node<'_>) -> Option<String> {
        let name = match t.kind() {
            "reference_type" => return self.plain_type(t.child_by_field_name("type")?),
            "type_identifier" => self.t(t).to_owned(),
            "scoped_type_identifier" => {
                // `module::Type` names a type; `Self::Item`, `T::Output` name associated types.
                let path = t.child_by_field_name("path")?;
                if !split_path(self.t(path)).iter().all(|s| !upper_first(s)) {
                    return None;
                }
                self.t(t.child_by_field_name("name")?).to_owned()
            }
            "generic_type" => {
                let head = t.child_by_field_name("type")?;
                if head.kind() != "type_identifier" {
                    return None;
                }
                self.t(head).to_owned()
            }
            _ => return None,
        };
        (!DEREF_WRAPPERS.contains(&name.as_str()) && !self.generics.contains(&name)).then_some(name)
    }

    /// The type a `let` value evidently has: a struct literal or `Type::new`/`Type::default`.
    fn value_type(&self, v: Node<'_>) -> Option<String> {
        match v.kind() {
            "struct_expression" => self.plain_type(v.child_by_field_name("name")?),
            "call_expression" => {
                let f = v.child_by_field_name("function")?;
                if f.kind() != "scoped_identifier" {
                    return None;
                }
                let leaf = self.t(f.child_by_field_name("name")?);
                let path = f.child_by_field_name("path")?;
                let name = self.t(path);
                (matches!(leaf, "new" | "default")
                    && path.kind() == "identifier"
                    && upper_first(name)
                    && !DEREF_WRAPPERS.contains(&name)
                    && !self.generics.iter().any(|g| g == name))
                .then(|| name.to_owned())
            }
            _ => None,
        }
    }

    /// Declares the type of the variable `pattern` pushed at `env[at]` (a single plain binder only).
    fn type_binder(&self, at: usize, pat: Option<Node<'_>>, ty: Option<Receiver>) {
        let Some(pat) = pat else { return };
        let plain = pat.kind() == "identifier"
            || (pat.kind() == "mut_pattern"
                && children(pat).iter().any(|c| c.kind() == "identifier"));
        if let (true, Some(ty), Some(slot)) = (plain, ty, self.env.borrow_mut().get_mut(at)) {
            slot.1 = Some(ty);
        }
    }

    /// Generic parameter names declared by `node`'s `type_parameters`.
    fn declared_generics(&self, node: Node<'_>) -> Vec<String> {
        let Some(tp) = node.child_by_field_name("type_parameters") else {
            return Vec::new();
        };
        children(tp)
            .into_iter()
            .filter_map(|c| match c.kind() {
                "type_parameter" | "const_parameter" => c.child_by_field_name("name"),
                "constrained_type_parameter" => c.child_by_field_name("left"),
                _ => None,
            })
            .map(|n| self.t(n).to_owned())
            .collect()
    }

    /// The trait bounds `node` puts on its generic parameters, inline and in its `where` clause.
    fn declared_bounds(&self, node: Node<'_>) -> Vec<(String, Vec<String>)> {
        let mut out: Vec<(String, Vec<String>)> = Vec::new();
        let mut add = |name: &str, bounds: Option<Node<'_>>| {
            let traits = bounds.map(|b| self.trait_names(b)).unwrap_or_default();
            if let Some((_, have)) = out.iter_mut().find(|(n, _)| n == name) {
                have.extend(traits);
            } else {
                out.push((name.to_owned(), traits));
            }
        };
        if let Some(tp) = node.child_by_field_name("type_parameters") {
            for c in children(tp) {
                if c.kind() == "constrained_type_parameter"
                    && let Some(l) = c.child_by_field_name("left")
                {
                    add(self.t(l), c.child_by_field_name("bounds"));
                }
            }
        }
        for w in children(node)
            .into_iter()
            .filter(|c| c.kind() == "where_clause")
        {
            for p in children(w)
                .into_iter()
                .filter(|c| c.kind() == "where_predicate")
            {
                if let Some(l) = p.child_by_field_name("left")
                    && l.kind() == "type_identifier"
                {
                    add(self.t(l), p.child_by_field_name("bounds"));
                }
            }
        }
        out
    }

    /// The trait names written in a bound list or trait type (`A + B`, `dyn A`, `impl A<T>`).
    fn trait_names(&self, n: Node<'_>) -> Vec<String> {
        match n.kind() {
            "type_identifier" => vec![self.t(n).to_owned()],
            "scoped_type_identifier" => n
                .child_by_field_name("name")
                .map(|x| vec![self.t(x).to_owned()])
                .unwrap_or_default(),
            "generic_type" => n
                .child_by_field_name("type")
                .map(|x| self.trait_names(x))
                .unwrap_or_default(),
            "trait_bounds" | "bounded_type" | "abstract_type" | "dynamic_type" => children(n)
                .into_iter()
                .filter(tree_sitter::Node::is_named)
                .flat_map(|c| self.trait_names(c))
                .collect(),
            _ => Vec::new(),
        }
    }

    /// Brings the generics and bounds of `node` into scope; returns the marks for [`Self::leave_generics`].
    fn enter_generics(&mut self, node: Node<'_>) -> (usize, usize) {
        let marks = (self.generics.len(), self.bounds.len());
        let own = self.declared_generics(node);
        self.generics.extend(own);
        let bounds = self.declared_bounds(node);
        self.bounds.extend(bounds);
        marks
    }

    /// Drops the generics and bounds brought in since `marks`.
    fn leave_generics(&mut self, marks: (usize, usize)) {
        self.generics.truncate(marks.0);
        self.bounds.truncate(marks.1);
    }

    /// The receiver a parameter or `let` type stands for when it is only known by its trait bounds.
    fn bound_receiver(&self, t: Node<'_>) -> Option<Receiver> {
        let traits: Vec<String> = match t.kind() {
            "reference_type" => return self.bound_receiver(t.child_by_field_name("type")?),
            "abstract_type" | "dynamic_type" => self.trait_names(t),
            "type_identifier" => {
                let name = self.t(t);
                self.bounds
                    .iter()
                    .rev()
                    .find(|(n, _)| n == name)
                    .map(|(_, b)| b.clone())
                    .unwrap_or_default()
            }
            _ => Vec::new(),
        };
        let mut traits = traits;
        traits.sort();
        traits.dedup();
        (!traits.is_empty()).then_some(Receiver::Bound(traits))
    }

    fn call(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(f) = n.child_by_field_name("function") else {
            return self.generic(n, depth);
        };
        let (head_node, targs) = if f.kind() == "generic_function" {
            (
                f.child_by_field_name("function").unwrap_or(f),
                f.child_by_field_name("type_arguments"),
            )
        } else {
            (f, None)
        };
        let target = self.call_target(head_node);
        let mut kids = Vec::new();
        let kind = if target.construct {
            "construct"
        } else if target.method {
            "method"
        } else {
            "call"
        };
        let head = if target.dynamic {
            self.tr(head_node, depth + 1)?
        } else if target.method {
            let name = format!(".{}", target.name);
            let field = head_node.child_by_field_name("field").unwrap_or(head_node);
            self.cx.op(Operator::reference(&name), field, &[])?
        } else if head_node.kind() == "scoped_identifier" {
            let text = split_path(self.t(head_node)).join("::");
            self.cx.op(Operator::reference(&text), head_node, &[])?
        } else {
            self.cx
                .op(Operator::reference(self.t(head_node)), head_node, &[])?
        };
        kids.push(head);
        if target.method
            && let Some(recv) = head_node.child_by_field_name("value")
        {
            kids.push(self.tr(recv, depth + 1)?);
        }
        if let Some(t) = targs {
            kids.push(self.tr(t, depth + 1)?);
        }
        if let Some(args) = n.child_by_field_name("arguments") {
            for a in children(args) {
                if a.is_named() {
                    kids.push(self.tr(a, depth + 1)?);
                }
            }
        }
        if !target.construct
            && let Some(&caller) = self.callers.last()
        {
            let item_local = self.locals.contains(&target.name);
            self.sites.push(Site {
                kind: SiteKind::Call {
                    method: target.method,
                    in_macro: false,
                },
                caller,
                name: target.name,
                qualifier: target.qualifier,
                node: Some(head),
                item_local,
                receiver: target.receiver,
                opaque: target.opaque,
                macro_exact: None,
                args: Some(Self::arg_count(n)),
                qual_path: target.path,
                line: line_of(n),
                text: call_text(self.t(f)),
            });
        }
        self.cx.op(Operator::apply(kind), n, &kids)
    }

    fn macro_call(&mut self, n: Node<'_>) -> R<NodeId> {
        let mut toks = Vec::new();
        for l in leaves(n) {
            toks.push(self.cx.lit(l.kind(), self.t(l), l)?);
        }
        let group = self
            .cx
            .op(Operator::group(GroupOrder::Sequence), n, &toks)?;
        if let Some(&caller) = self.callers.last() {
            self.scan_macro(n, caller);
        }
        self.cx.op(Operator::phase("macro"), n, &[group])
    }

    /// Records the calls inside the macro invocation `n`: exactly when it is a std macro with expression
    /// arguments, else by the token-shape scan (status capped at May).
    fn scan_macro(&mut self, n: Node<'_>, caller: usize) {
        if !self.scan_exact_macro(n, caller) {
            self.scan_macro_calls(n, caller);
        }
    }

    /// Parses the arguments of a std macro (`assert_eq!`, `format!`, ...) as ordinary call arguments and
    /// records their calls like any others; false when the macro is not one of those or does not parse.
    ///
    /// The arguments are re-parsed inside a synthetic `fn g(){f(ARGS);}` laid over blanks so every node
    /// keeps its byte offset and line in the real file. Names bound inside the arguments (closure
    /// parameters, `let`, match arms) shadow outer typed variables for the whole invocation.
    fn scan_exact_macro(&mut self, n: Node<'_>, caller: usize) -> bool {
        let Some(name) = n
            .child_by_field_name("macro")
            .and_then(|m| self.t(m).rsplit("::").next())
            .filter(|m| EXACT_MACROS.contains(m))
        else {
            return false;
        };
        let Some(tt) = children(n).into_iter().find(|c| c.kind() == "token_tree") else {
            return false;
        };
        let (a, b) = (tt.start_byte(), tt.end_byte());
        let bytes = self.cx.text.as_bytes();
        if a < 8 || b > bytes.len() || b < a + 2 {
            return false;
        }
        let mut synth: Vec<u8> = bytes[..b]
            .iter()
            .enumerate()
            .map(|(i, &c)| if i < a { blank(c) } else { c })
            .collect();
        synth[..7].copy_from_slice(b"fn g(){");
        synth[a - 1] = b'f';
        synth[a] = b'(';
        synth[b - 1] = b')';
        // `%x` and `?x` field values (tracing) are not Rust expressions: blank the sigil.
        for i in a + 1..b - 1 {
            if matches!(synth[i], b'%' | b'?')
                && synth[..i]
                    .iter()
                    .rev()
                    .find(|c| !c.is_ascii_whitespace())
                    .is_some_and(|c| matches!(c, b'=' | b',' | b'('))
            {
                synth[i] = b' ';
            }
        }
        synth.extend_from_slice(b";}");
        let Ok(synth) = String::from_utf8(synth) else {
            return false;
        };
        let gob_languages::ParseResult::Parsed(tree) =
            parse(Language::Rust, &synth, &ParseLimits::default())
        else {
            return false;
        };
        if tree.has_errors() {
            tracing::trace!(
                path = self.path,
                macro_name = name,
                "macro arguments are not plain expressions"
            );
            return false;
        }
        let Some(call) = find_synthetic_call(tree.root(), a - 1) else {
            return false;
        };
        let Some(args) = call.child_by_field_name("arguments") else {
            return false;
        };
        let saved_env = self.env.borrow().len();
        let mut all = vec![args];
        let mut nodes = Vec::new();
        while let Some(x) = all.pop() {
            nodes.push(x);
            all.extend(children(x));
        }
        for x in &nodes {
            for p in Self::binder_patterns(*x) {
                let _ = self.pattern(p);
            }
        }
        for x in nodes {
            self.exact_macro_node(x, caller, name);
        }
        self.env.borrow_mut().truncate(saved_env);
        tracing::trace!(
            path = self.path,
            macro_name = name,
            "std macro arguments scanned as expressions"
        );
        true
    }

    /// The pattern nodes that `x` itself introduces bindings with.
    fn binder_patterns(x: Node<'_>) -> Vec<Node<'_>> {
        match x.kind() {
            "closure_parameters" => vec![x],
            "let_declaration" | "match_arm" | "for_expression" | "let_condition" => {
                x.child_by_field_name("pattern").into_iter().collect()
            }
            _ => Vec::new(),
        }
    }

    /// Records the site of `x` (a node of a parsed std-macro argument) when it is a call or a nested macro.
    fn exact_macro_node(&mut self, x: Node<'_>, caller: usize, macro_name: &str) {
        if x.kind() == "macro_invocation" {
            // Handled whole (the walk of its token tree below is token-shaped, not expression-shaped).
            self.scan_macro(x, caller);
            return;
        }
        if x.kind() != "call_expression" || inside_macro(x) {
            return;
        }
        let Some(f) = x.child_by_field_name("function") else {
            return;
        };
        let t = self.call_target(f);
        if t.construct {
            return;
        }
        let bare_local = !t.method
            && t.path.is_empty()
            && (self.env.borrow().iter().any(|(n, _)| *n == t.name)
                || self.locals.contains(&t.name));
        self.sites.push(Site {
            kind: SiteKind::Call {
                method: t.method,
                in_macro: true,
            },
            caller,
            name: if bare_local { String::new() } else { t.name },
            qualifier: t.qualifier,
            node: None,
            item_local: false,
            receiver: t.receiver,
            opaque: t.opaque,
            macro_exact: Some(macro_name.to_owned()),
            args: Some(Self::arg_count(x)),
            qual_path: t.path,
            line: line_of(x),
            text: call_text(self.t(f)),
        });
    }

    /// The type or module before `::name` at `kids[i]` inside a macro, skipping a turbofish (`Vec::<T>::new`).
    fn macro_qualifier(&self, kids: &[Node<'_>], i: usize) -> Option<String> {
        let mut j = i.checked_sub(2)?;
        if self.t(kids[j]) == ">" {
            let mut depth = 0usize;
            loop {
                match self.t(kids[j]) {
                    ">" => depth += 1,
                    "<" => depth -= 1,
                    _ => {}
                }
                if depth == 0 {
                    break;
                }
                j = j.checked_sub(1)?;
            }
            if j < 2 || self.t(kids[j - 1]) != "::" {
                return None;
            }
            j -= 2;
        }
        (kids[j].kind() == "identifier").then(|| self.t(kids[j]).to_owned())
    }

    /// Records `name(` call shapes inside a macro's token trees (status capped at May).
    fn scan_macro_calls(&mut self, n: Node<'_>, caller: usize) {
        let mut stack = vec![n];
        while let Some(x) = stack.pop() {
            let kids = children(x);
            for (i, k) in kids.iter().enumerate() {
                if k.kind() == "identifier"
                    && let Some(next) = kids.get(i + 1)
                    && next.kind() == "token_tree"
                    && self.t(*next).starts_with('(')
                {
                    let prev = i.checked_sub(1).map(|j| self.t(kids[j]));
                    let method = prev == Some(".");
                    let qualifier = if prev == Some("::") {
                        self.macro_qualifier(&kids, i)
                    } else {
                        None
                    };
                    let name = self.t(*k).to_owned();
                    if !upper_first(&name) {
                        self.sites.push(Site {
                            kind: SiteKind::Call {
                                method,
                                in_macro: true,
                            },
                            caller,
                            text: call_text(&match (&qualifier, method) {
                                (Some(q), _) => format!("{q}::{name}"),
                                (None, true) => format!(".{name}"),
                                (None, false) => name.clone(),
                            }),
                            line: line_of(*k),
                            name,
                            qualifier,
                            node: None,
                            item_local: false,
                            receiver: method.then_some(Receiver::Expr),
                            opaque: false,
                            macro_exact: None,
                            args: None,
                            qual_path: Vec::new(),
                        });
                    }
                }
                if k.kind() == "token_tree" {
                    stack.push(*k);
                }
            }
        }
    }

    // ---- patterns and binders ----

    fn is_binder_leaf(&self, l: Node<'_>) -> bool {
        match l.kind() {
            "shorthand_field_identifier" => true,
            "identifier" => {
                let name = self.t(l);
                !upper_first(name)
                    && !l
                        .parent()
                        .is_some_and(|p| matches!(p.kind(), "scoped_identifier"))
            }
            _ => false,
        }
    }

    /// The variables a pattern binds (deduplicated, in order) and its shape text.
    fn pattern(&self, p: Node<'_>) -> (Vec<String>, String) {
        let mut names: Vec<String> = Vec::new();
        let mut shape: Vec<String> = Vec::new();
        for l in leaves(p) {
            if self.is_binder_leaf(l) {
                let name = self.t(l).to_owned();
                if !names.contains(&name) {
                    self.env.borrow_mut().push((name.clone(), None));
                    names.push(name);
                }
                shape.push("_".to_owned());
            } else {
                shape.push(self.t(l).to_owned());
            }
        }
        (names, shape.join(" "))
    }

    fn bind_node(
        &mut self,
        kind: &str,
        n: Node<'_>,
        binders: &[String],
        scope: NodeId,
        rhs: NodeId,
    ) -> R<NodeId> {
        let names: Vec<&str> = binders.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::bind(kind, ""), self.cx.node_loc(n)).binders(&names);
        self.cx.add(spec, &[scope, rhs])
    }

    // ---- blocks and statements ----

    fn block(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let kids: Vec<Node<'_>> = children(n)
            .into_iter()
            .filter(|c| !matches!(c.kind(), "{" | "}"))
            .collect();
        let saved = self.locals.len();
        let saved_env = self.env.borrow().len();
        let nodes = self.with_expr(true, |s| s.seq(&kids, depth + 1))?;
        self.locals.truncate(saved);
        self.env.borrow_mut().truncate(saved_env);
        self.cx.op(Operator::group(GroupOrder::Sequence), n, &nodes)
    }

    fn seq(&mut self, kids: &[Node<'_>], depth: usize) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        for (i, k) in kids.iter().enumerate() {
            match k.kind() {
                "let_declaration" if !k.has_error() => {
                    if depth > MAX_DEPTH {
                        out.push(self.collapse(&kids[i..])?);
                    } else {
                        out.push(self.let_stmt(*k, &kids[i + 1..], depth)?);
                    }
                    return Ok(out);
                }
                "function_item"
                    if !k.has_error()
                        && let Some(name) = k.child_by_field_name("name") =>
                {
                    if depth > MAX_DEPTH {
                        out.push(self.collapse(&kids[i..])?);
                    } else {
                        let name = self.t(name).to_owned();
                        out.push(self.item_stmt(*k, &name, &kids[i + 1..], depth)?);
                    }
                    return Ok(out);
                }
                _ => out.push(self.tr(*k, depth)?),
            }
        }
        Ok(out)
    }

    fn rest_group(&mut self, at: Node<'_>, rest: &[Node<'_>], depth: usize) -> R<NodeId> {
        let nodes = self.seq(rest, depth + 1)?;
        let (s, e) = rest
            .first()
            .zip(rest.last())
            .map_or((at.end_byte(), at.end_byte()), |(a, b)| {
                (a.start_byte(), b.end_byte())
            });
        let spec = NodeSpec::new(Operator::group(GroupOrder::Sequence), self.cx.loc(s, e));
        self.cx.add(spec, &nodes)
    }

    fn let_stmt(&mut self, k: Node<'_>, rest: &[Node<'_>], depth: usize) -> R<NodeId> {
        let env_at = self.env.borrow().len();
        let (binders, shape) = k
            .child_by_field_name("pattern")
            .map_or((Vec::new(), String::new()), |p| self.pattern(p));
        let mut rhs = vec![self.cx.lit("pattern", &shape, k)?];
        for field in ["type", "value", "alternative"] {
            if let Some(c) = k.child_by_field_name(field) {
                rhs.push(self.tr(c, depth + 1)?);
            }
        }
        let declared = k.child_by_field_name("type").and_then(|t| {
            self.plain_type(t)
                .map(Receiver::Typed)
                .or_else(|| self.bound_receiver(t))
        });
        let ty = declared.or_else(|| {
            k.child_by_field_name("value")
                .and_then(|v| self.value_receiver(v))
        });
        self.type_binder(env_at, k.child_by_field_name("pattern"), ty);
        let rhs = self.cx.op(Operator::group(GroupOrder::Sequence), k, &rhs)?;
        let scope = self.rest_group(k, rest, depth)?;
        self.bind_node("let", k, &binders, scope, rhs)
    }

    fn nested_fn_anon(&mut self, k: Node<'_>, depth: usize) -> R<NodeId> {
        let name = k.child_by_field_name("name");
        let ord_guard = self.callers.len();
        let mut kids = Vec::new();
        let saved_locals = self.locals.len();
        let saved_env = std::mem::take(&mut *self.env.borrow_mut());
        for c in children(k) {
            if Some(c.id()) == name.map(|n| n.id()) {
                continue;
            }
            let is_body = k
                .child_by_field_name("body")
                .is_some_and(|b| b.id() == c.id());
            let node = if is_body {
                self.with_expr(true, |s| s.tr(c, depth + 1))?
            } else {
                self.with_expr(false, |s| s.tr(c, depth + 1))?
            };
            kids.push(node);
        }
        self.locals.truncate(saved_locals);
        *self.env.borrow_mut() = saved_env;
        debug_assert_eq!(ord_guard, self.callers.len());
        self.cx.op(Operator::anon("fn"), k, &kids)
    }

    fn nested_fn(&mut self, k: Node<'_>, depth: usize) -> R<NodeId> {
        self.nested_fn_anon(k, depth)
    }

    fn item_stmt(&mut self, k: Node<'_>, name: &str, rest: &[Node<'_>], depth: usize) -> R<NodeId> {
        let rhs = self.nested_fn_anon(k, depth + 1)?;
        self.locals.push(name.to_owned());
        let scope = self.rest_group(k, rest, depth)?;
        self.bind_node("item", k, &[name.to_owned()], scope, rhs)
    }

    fn closure(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut binders: Vec<String> = Vec::new();
        let mut kids = Vec::new();
        for c in children(n) {
            if c.kind() == "closure_parameters" {
                for p in children(c).into_iter().filter(tree_sitter::Node::is_named) {
                    let pat = if p.kind() == "parameter" {
                        p.child_by_field_name("pattern").unwrap_or(p)
                    } else {
                        p
                    };
                    let (names, shape) = self.pattern(pat);
                    for nm in names {
                        if !binders.contains(&nm) {
                            binders.push(nm);
                        }
                    }
                    kids.push(self.cx.lit("pattern", &shape, p)?);
                    if p.kind() == "parameter"
                        && let Some(t) = p.child_by_field_name("type")
                    {
                        kids.push(self.tr(t, depth + 1)?);
                    }
                }
            } else {
                kids.push(self.tr(c, depth + 1)?);
            }
        }
        let names: Vec<&str> = binders.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::anon("closure"), self.cx.node_loc(n)).binders(&names);
        self.cx.add(spec, &kids)
    }

    fn match_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        if let Some(v) = n.child_by_field_name("value") {
            kids.push(self.tr(v, depth + 1)?);
        }
        if let Some(body) = n.child_by_field_name("body") {
            let mut arms = Vec::new();
            for c in children(body) {
                match c.kind() {
                    "match_arm" => arms.push(self.match_arm(c, depth + 2)?),
                    "{" | "}" => {}
                    _ => arms.push(self.tr(c, depth + 2)?),
                }
            }
            kids.push(
                self.cx
                    .op(Operator::group(GroupOrder::Sequence), body, &arms)?,
            );
        }
        self.cx.op(Operator::group(GroupOrder::Sequence), n, &kids)
    }

    fn match_arm(&mut self, arm: Node<'_>, depth: usize) -> R<NodeId> {
        let mp = arm.child_by_field_name("pattern");
        let cond = mp.and_then(|m| m.child_by_field_name("condition"));
        let mut binders = Vec::new();
        let mut shapes = Vec::new();
        if let Some(m) = mp {
            for c in children(m).into_iter().filter(tree_sitter::Node::is_named) {
                if cond.is_some_and(|x| x.id() == c.id()) {
                    continue;
                }
                let (names, shape) = self.pattern(c);
                for nm in names {
                    if !binders.contains(&nm) {
                        binders.push(nm);
                    }
                }
                shapes.push(shape);
            }
        }
        let shape = self
            .cx
            .lit("pattern", &shapes.join(" | "), mp.unwrap_or(arm))?;
        let mut scope_kids = Vec::new();
        if let Some(c) = cond {
            scope_kids.push(self.tr(c, depth + 1)?);
        }
        if let Some(v) = arm.child_by_field_name("value") {
            scope_kids.push(self.tr(v, depth + 1)?);
        }
        let scope = self
            .cx
            .op(Operator::group(GroupOrder::Sequence), arm, &scope_kids)?;
        self.bind_node("pattern", arm, &binders, scope, shape)
    }

    fn for_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let (Some(p), Some(body)) = (
            n.child_by_field_name("pattern"),
            n.child_by_field_name("body"),
        ) else {
            return self.generic(n, depth);
        };
        let (binders, shape) = self.pattern(p);
        let mut rhs = vec![self.cx.lit("pattern", &shape, p)?];
        if let Some(v) = n.child_by_field_name("value") {
            rhs.push(self.tr(v, depth + 1)?);
        }
        let rhs = self.cx.op(Operator::group(GroupOrder::Sequence), n, &rhs)?;
        let scope = self.tr(body, depth + 1)?;
        self.bind_node("for", n, &binders, scope, rhs)
    }

    /// Binders of every `let` condition in `cond` (not looking into blocks or closures).
    fn cond_binders(&self, cond: Node<'_>) -> Vec<String> {
        let mut out: Vec<String> = Vec::new();
        let mut stack = vec![cond];
        while let Some(x) = stack.pop() {
            match x.kind() {
                "let_condition" => {
                    if let Some(p) = x.child_by_field_name("pattern") {
                        for nm in self.pattern(p).0 {
                            if !out.contains(&nm) {
                                out.push(nm);
                            }
                        }
                    }
                }
                "block" | "closure_expression" => {}
                _ => stack.extend(children(x)),
            }
        }
        out
    }

    fn cond_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let Some(cond) = n.child_by_field_name("condition") else {
            return self.generic(n, depth);
        };
        let binders = self.cond_binders(cond);
        let body = n
            .child_by_field_name("consequence")
            .or_else(|| n.child_by_field_name("body"));
        let Some(body) = body.filter(|_| !binders.is_empty()) else {
            return self.generic(n, depth);
        };
        let rhs = self.tr(cond, depth + 1)?;
        let scope = self.tr(body, depth + 1)?;
        let kind = if n.kind() == "if_expression" {
            "if-let"
        } else {
            "while-let"
        };
        let bound = self.bind_node(kind, n, &binders, scope, rhs)?;
        match n.child_by_field_name("alternative") {
            Some(alt) => {
                let alt = self.tr(alt, depth + 1)?;
                self.cx
                    .op(Operator::group(GroupOrder::Sequence), n, &[bound, alt])
            }
            None => Ok(bound),
        }
    }

    fn let_condition(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        if let Some(p) = n.child_by_field_name("pattern") {
            let shape = self.pattern(p).1;
            kids.push(self.cx.lit("pattern", &shape, p)?);
        }
        if let Some(v) = n.child_by_field_name("value") {
            kids.push(self.tr(v, depth + 1)?);
        }
        self.cx.op(Operator::group(GroupOrder::Sequence), n, &kids)
    }

    // ---- items ----

    fn visibility(&self, node: Node<'_>, scope: &Scope) -> Visibility {
        let modifier = children(node)
            .into_iter()
            .find(|k| k.kind() == "visibility_modifier");
        match modifier {
            Some(m) => {
                let t = collapse_ws(self.t(m));
                if t == "pub" {
                    Visibility::Public
                } else if t.replace(' ', "") == "pub(self)" {
                    Visibility::Private
                } else {
                    Visibility::Crate
                }
            }
            None => scope.inherit.unwrap_or(if scope.trait_impl {
                Visibility::Public
            } else {
                Visibility::Private
            }),
        }
    }

    fn doc_text(&self, docs: &[Node<'_>]) -> String {
        let mut lines: Vec<String> = Vec::new();
        for d in docs {
            let t = self.t(*d);
            if t.starts_with("/**") {
                let inner = t.trim_start_matches("/**").trim_end_matches("*/");
                lines.push(collapse_ws(inner));
            } else if let Some(r) = t.trim_end().strip_prefix("///") {
                lines.push(r.trim().to_owned());
            } else if let Some(r) = t.trim_end().strip_prefix("//!") {
                lines.push(r.trim().to_owned());
            }
        }
        lines.join("\n")
    }

    fn attr_node(&mut self, item: Node<'_>) -> R<NodeId> {
        let attr = children(item)
            .into_iter()
            .find(|c| c.kind() == "attribute")
            .unwrap_or(item);
        let kids = children(attr);
        let (name, rest): (String, &[Node<'_>]) = match kids.split_first() {
            Some((first, rest)) if first.is_named() => {
                (split_path(self.t(*first)).join("::"), rest)
            }
            _ => (collapse_ws(self.t(attr)), &[]),
        };
        let mut payload = Vec::new();
        for r in rest {
            for l in leaves(*r) {
                payload.push(self.cx.lit(l.kind(), self.t(l), l)?);
            }
        }
        self.cx.op(Operator::attr(&name), item, &payload)
    }

    fn doc_node(&mut self, docs: &[Node<'_>]) -> R<Option<NodeId>> {
        let Some(first) = docs.first() else {
            return Ok(None);
        };
        let text = self.doc_text(docs);
        let payload = self.cx.lit("str", &text, *first)?;
        Ok(Some(self.cx.op(
            Operator::attr("doc"),
            *first,
            &[payload],
        )?))
    }

    /// Builds a unit with its doc, attribute, comment, sig and body children.
    #[allow(
        clippy::too_many_arguments,
        reason = "one unit constructor, inputs distinct"
    )]
    fn make_unit(
        &mut self,
        ord: usize,
        node: Node<'_>,
        kind: &str,
        role: &str,
        name: &str,
        qualifier: Option<&str>,
        extra: (Option<Visibility>, Option<&str>, &[String]),
        lead: &Lead<'_>,
        sig: Vec<NodeId>,
        body: Vec<NodeId>,
    ) -> R<NodeId> {
        let (vis, implements, binders) = extra;
        let mut kids = Vec::new();
        if let Some(d) = self.doc_node(&lead.docs)? {
            kids.push(d);
        }
        for a in &lead.attrs {
            kids.push(self.attr_node(*a)?);
        }
        for c in &lead.comments {
            kids.push(self.comment(*c)?);
        }
        let mut sig_kids = Vec::new();
        for a in &lead.attrs {
            sig_kids.push(self.attr_node(*a)?);
        }
        sig_kids.extend(sig);
        let sig_group = NodeSpec::new(
            Operator::group(GroupOrder::Sequence),
            self.cx.node_loc(node),
        )
        .attr(reserved::FACET, "sig");
        kids.push(self.cx.add(sig_group, &sig_kids)?);
        kids.extend(body);
        let names: Vec<&str> = binders.iter().map(String::as_str).collect();
        let mut spec = NodeSpec::new(Operator::unit(kind, role), self.cx.node_loc(node))
            .named(name)
            .binders(&names);
        if let Some(q) = qualifier {
            spec = spec.attr(reserved::QUALIFIER, q);
        }
        if let Some(v) = vis {
            spec = spec.attr(ATTR_VISIBILITY, vis_text(v));
        }
        if let Some(i) = implements {
            spec = spec.attr(ATTR_IMPLEMENTS, i);
        }
        if let Some((self_kind, arity, ret)) = self.fn_sig.take() {
            spec = spec
                .attr(ATTR_SELF_KIND, self_kind.as_attr())
                .attr(ATTR_ARITY, arity.to_string().as_str());
            if let Some(r) = ret {
                spec = spec.attr(ATTR_RET, r.head.as_str());
                if let Some(a) = r.arg {
                    spec = spec.attr(ATTR_RET_ARG, a.as_str());
                }
            }
        }
        let id = self.cx.add(spec, &kids)?;
        self.ord_nodes[ord] = Some(id);
        tracing::trace!(path = self.path, kind, name, "rust unit");
        Ok(id)
    }

    /// Token-mode translation of every child of `node` except those in `skip`.
    fn sig_tokens(&mut self, node: Node<'_>, skip: &[Option<Node<'_>>]) -> R<Vec<NodeId>> {
        let skip: HashSet<usize> = skip.iter().flatten().map(Node::id).collect();
        let mut out = Vec::new();
        for c in children(node) {
            if skip.contains(&c.id()) {
                continue;
            }
            out.push(self.with_expr(false, |s| s.tr(c, 1))?);
        }
        Ok(out)
    }

    fn container(&mut self, c: Node<'_>, scope: &Scope, inner_docs: bool) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        let mut lead = Lead::default();
        let mut inner: Vec<Node<'_>> = Vec::new();
        for k in children(c) {
            if matches!(k.kind(), "{" | "}" | ",") {
                continue;
            }
            match k.kind() {
                "line_comment" | "block_comment" => {
                    let t = self.t(k).trim_end();
                    let outer = (t.starts_with("///") && !t.starts_with("////"))
                        || (t.starts_with("/**") && !t.starts_with("/***") && t != "/**/");
                    let inner_doc = t.starts_with("//!") || t.starts_with("/*!");
                    if inner_doc && inner_docs {
                        inner.push(k);
                    } else if outer {
                        lead.docs.push(k);
                    } else {
                        let orphaned = std::mem::take(&mut lead.docs);
                        lead.comments.extend(orphaned);
                        lead.comments.push(k);
                    }
                }
                "attribute_item" => lead.attrs.push(k),
                "inner_attribute_item" => out.push(self.with_expr(false, |s| s.attr_node(k))?),
                _ => {
                    let taken = std::mem::take(&mut lead);
                    if let Some(id) = self.item(k, scope, &taken)? {
                        out.push(id);
                    } else {
                        for a in &taken.attrs {
                            out.push(self.with_expr(false, |s| s.tr(*a, 1))?);
                        }
                        for d in taken.docs.iter().chain(&taken.comments) {
                            out.push(self.comment(*d)?);
                        }
                        out.push(self.tr(k, 1)?);
                    }
                }
            }
        }
        for d in lead.docs.iter().chain(&lead.comments) {
            out.push(self.comment(*d)?);
        }
        for a in &lead.attrs {
            out.push(self.with_expr(false, |s| s.tr(*a, 1))?);
        }
        if let Some(d) = self.doc_node(&inner)? {
            out.insert(0, d);
        }
        Ok(out)
    }

    fn name_of<'n>(&self, node: Node<'n>) -> Option<(Node<'n>, String)> {
        node.child_by_field_name("name")
            .map(|n| (n, self.t(n).to_owned()))
    }

    fn item(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        match node.kind() {
            "function_item" | "function_signature_item" => self.function(node, scope, lead),
            "struct_item" | "union_item" => self.simple(node, "struct", scope, lead),
            "enum_item" => self.enum_item(node, scope, lead),
            "trait_item" => self.trait_item(node, scope, lead),
            "impl_item" => self.impl_item(node, scope, lead),
            "mod_item" => self.mod_item(node, scope, lead),
            "const_item" => self.value_item(node, "const", scope, lead),
            "static_item" => self.value_item(node, "static", scope, lead),
            "type_item" => self.simple(node, "type", scope, lead),
            "macro_definition" => self.macro_def(node, lead),
            "enum_variant" => self.variant(node, scope, lead),
            "use_declaration" => {
                let id = self.use_node(node)?;
                Ok(Some(id))
            }
            _ => Ok(None),
        }
    }

    fn simple(
        &mut self,
        node: Node<'_>,
        kind: &str,
        scope: &Scope,
        lead: &Lead<'_>,
    ) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        if node.kind() == "struct_item" {
            self.struct_fields(node, &name);
        }
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = self.sig_tokens(node, &[Some(name_node), body])?;
        let body_nodes = match body {
            Some(b) => vec![self.with_expr(false, |s| s.tr(b, 1))?],
            None => Vec::new(),
        };
        self.unit_stack.pop();
        let role = "impl";
        let id = self.make_unit(
            ord,
            node,
            kind,
            role,
            &name,
            None,
            (Some(vis), scope.implements.as_deref(), &[]),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    fn function(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        let params = node.child_by_field_name("parameters");
        let kind = if scope.member { "method" } else { "function" };
        let ord = self.alloc();
        self.unit_stack.push(ord);
        self.callers.push(ord);
        self.fn_depth += 1;
        let saved_env = std::mem::take(&mut *self.env.borrow_mut());
        let saved_generics = self.enter_generics(node);
        let ret = node
            .child_by_field_name("return_type")
            .and_then(|t| self.ret_type(t));
        let mut binders: Vec<String> = Vec::new();
        let mut sig = Vec::new();
        for c in children(node) {
            if c.id() == name_node.id() || body.is_some_and(|b| b.id() == c.id()) {
                continue;
            }
            if params.is_some_and(|p| p.id() == c.id()) {
                self.params(c, &mut binders, &mut sig)?;
            } else {
                sig.push(self.with_expr(false, |s| s.tr(c, 1))?);
            }
        }
        let body_nodes = match body {
            Some(b) => vec![self.with_expr(true, |s| s.tr(b, 1))?],
            None => Vec::new(),
        };
        self.fn_depth -= 1;
        self.leave_generics(saved_generics);
        *self.env.borrow_mut() = saved_env;
        self.callers.pop();
        self.unit_stack.pop();
        let role = if body.is_some() { "impl" } else { "sig" };
        self.fn_sig = Some(self.signature_of(params, ret));
        let id = self.make_unit(
            ord,
            node,
            kind,
            role,
            &name,
            None,
            (Some(vis), scope.implements.as_deref(), &binders),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    /// The `self` kind and parameter count of a function with parameter list `params`.
    fn signature_of(
        &self,
        params: Option<Node<'_>>,
        ret: Option<RetType>,
    ) -> (SelfKind, usize, Option<RetType>) {
        let mut kind = SelfKind::None;
        let mut arity = 0;
        for p in params.map(children).into_iter().flatten() {
            match p.kind() {
                "self_parameter" => {
                    let text = collapse_ws(self.t(p));
                    kind = if text.starts_with('&') {
                        if text
                            .split(|c: char| !c.is_alphanumeric())
                            .any(|w| w == "mut")
                        {
                            SelfKind::RefMut
                        } else {
                            SelfKind::Ref
                        }
                    } else {
                        SelfKind::Value
                    };
                }
                "parameter" | "variadic_parameter" => arity += 1,
                _ => {}
            }
        }
        (kind, arity, ret)
    }

    /// Records the concrete-typed fields of the struct `node` named `owner` (the field type table).
    fn struct_fields(&mut self, node: Node<'_>, owner: &str) {
        let Some(list) = node
            .child_by_field_name("body")
            .filter(|b| b.kind() == "field_declaration_list")
        else {
            return;
        };
        let saved = self.enter_generics(node);
        for d in children(list)
            .into_iter()
            .filter(|c| c.kind() == "field_declaration")
        {
            let (Some(name), Some(ty)) = (
                d.child_by_field_name("name"),
                d.child_by_field_name("type")
                    .and_then(|t| self.plain_type(t)),
            ) else {
                continue;
            };
            tracing::trace!(path = self.path, owner, field = self.t(name), %ty, "struct field type");
            self.fields.push(FieldDecl {
                owner: owner.to_owned(),
                field: self.t(name).to_owned(),
                ty,
            });
        }
        self.leave_generics(saved);
    }

    fn params(
        &mut self,
        params: Node<'_>,
        binders: &mut Vec<String>,
        sig: &mut Vec<NodeId>,
    ) -> R<()> {
        for p in children(params)
            .into_iter()
            .filter(tree_sitter::Node::is_named)
        {
            match p.kind() {
                "parameter" => {
                    let pat = p.child_by_field_name("pattern");
                    let env_at = self.env.borrow().len();
                    let (names, mut shape) =
                        pat.map_or((Vec::new(), String::new()), |x| self.pattern(x));
                    if children(p).iter().any(|c| c.kind() == "mutable_specifier") {
                        shape.insert_str(0, "mut ");
                    }
                    for nm in names {
                        if !binders.contains(&nm) {
                            binders.push(nm);
                        }
                    }
                    let ty = p.child_by_field_name("type").and_then(|t| {
                        self.plain_type(t)
                            .map(Receiver::Typed)
                            .or_else(|| self.bound_receiver(t))
                    });
                    self.type_binder(env_at, pat, ty);
                    let mut kids = vec![self.cx.lit("pattern", &shape, pat.unwrap_or(p))?];
                    if let Some(t) = p.child_by_field_name("type") {
                        kids.push(self.with_expr(false, |s| s.tr(t, 2))?);
                    }
                    let op = Operator::adapter("rust", "parameter", Sort::Exp);
                    sig.push(self.cx.op(op, p, &kids)?);
                }
                "self_parameter" => {
                    if !binders.iter().any(|b| b == "self") {
                        binders.push("self".to_owned());
                    }
                    let text = collapse_ws(self.t(p));
                    sig.push(self.cx.lit("self_parameter", &text, p)?);
                }
                _ => sig.push(self.with_expr(false, |s| s.tr(p, 2))?),
            }
        }
        Ok(())
    }

    fn value_item(
        &mut self,
        node: Node<'_>,
        kind: &str,
        scope: &Scope,
        lead: &Lead<'_>,
    ) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = self.visibility(node, scope);
        let value = node.child_by_field_name("value");
        let ord = self.alloc();
        self.unit_stack.push(ord);
        self.callers.push(ord);
        let sig = self.sig_tokens(node, &[Some(name_node), value])?;
        let body = match value {
            Some(v) => vec![self.with_expr(true, |s| s.tr(v, 1))?],
            None => Vec::new(),
        };
        self.callers.pop();
        self.unit_stack.pop();
        let id = self.make_unit(
            ord,
            node,
            kind,
            "impl",
            &name,
            None,
            (Some(vis), scope.implements.as_deref(), &[]),
            lead,
            sig,
            body,
        )?;
        Ok(Some(id))
    }

    fn macro_def(&mut self, node: Node<'_>, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let exported = lead
            .attrs
            .iter()
            .any(|a| self.t(*a).contains("macro_export"));
        let vis = if exported {
            Visibility::Public
        } else {
            Visibility::Private
        };
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = vec![self.cx.lit("keyword", "macro_rules!", name_node)?];
        let mut body = Vec::new();
        for c in children(node) {
            if c.start_byte() > name_node.end_byte() {
                body.push(self.with_expr(false, |s| s.tr(c, 1))?);
            }
        }
        self.unit_stack.pop();
        let id = self.make_unit(
            ord,
            node,
            "macro",
            "impl",
            &name,
            None,
            (Some(vis), None, &[]),
            lead,
            sig,
            body,
        )?;
        Ok(Some(id))
    }

    fn enum_item(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = self.sig_tokens(node, &[Some(name_node), body])?;
        let body_nodes = match body {
            Some(b) => {
                let inner = Scope {
                    inherit: Some(vis),
                    ..Scope::default()
                };
                let saved_generics = self.enter_generics(node);
                let out = self.container(b, &inner, false);
                self.leave_generics(saved_generics);
                out?
            }
            None => Vec::new(),
        };
        self.unit_stack.pop();
        let id = self.make_unit(
            ord,
            node,
            "enum",
            "impl",
            &name,
            None,
            (Some(vis), scope.implements.as_deref(), &[]),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    fn variant(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = scope.inherit.unwrap_or(Visibility::Private);
        let body = node.child_by_field_name("body");
        let value = node.child_by_field_name("value");
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = self.sig_tokens(node, &[Some(name_node), body, value])?;
        let mut body_nodes = Vec::new();
        for part in [body, value].into_iter().flatten() {
            body_nodes.push(self.with_expr(false, |s| s.tr(part, 1))?);
        }
        self.unit_stack.pop();
        let id = self.make_unit(
            ord,
            node,
            "variant",
            "impl",
            &name,
            None,
            (Some(vis), None, &[]),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    fn trait_item(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = self.sig_tokens(node, &[Some(name_node), body])?;
        let body_nodes = match body {
            Some(b) => {
                let inner = Scope {
                    member: true,
                    inherit: Some(vis),
                    ..Scope::default()
                };
                self.container(b, &inner, false)?
            }
            None => Vec::new(),
        };
        self.unit_stack.pop();
        let id = self.make_unit(
            ord,
            node,
            "trait",
            "impl",
            &name,
            None,
            (Some(vis), scope.implements.as_deref(), &[]),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    fn type_name(&self, node: Node<'_>) -> String {
        match node.kind() {
            "generic_type" | "reference_type" | "pointer_type" => node
                .child_by_field_name("type")
                .map_or_else(|| collapse_ws(self.t(node)), |n| self.type_name(n)),
            "scoped_type_identifier" => node
                .child_by_field_name("name")
                .map_or_else(|| collapse_ws(self.t(node)), |n| self.t(n).to_owned()),
            _ => collapse_ws(self.t(node)),
        }
    }

    fn impl_item(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some(ty) = node.child_by_field_name("type") else {
            return Ok(None);
        };
        let tname = self.type_name(ty);
        let tr: Option<String> = node
            .child_by_field_name("trait")
            .map(|n| self.t(n).split_whitespace().collect());
        let label = tr.clone().unwrap_or_else(|| "impl".to_owned());
        let body = node.child_by_field_name("body");
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = self.sig_tokens(node, &[body])?;
        let body_nodes = match body {
            Some(b) => {
                let inner = Scope {
                    member: true,
                    inherit: None,
                    implements: tr.clone(),
                    trait_impl: tr.is_some(),
                };
                let saved_generics = self.enter_generics(node);
                let out = self.container(b, &inner, false);
                self.leave_generics(saved_generics);
                out?
            }
            None => Vec::new(),
        };
        self.unit_stack.pop();
        let _ = scope;
        let id = self.make_unit(
            ord,
            node,
            "impl",
            "impl",
            &tname,
            Some(&label),
            (None, tr.as_deref(), &[]),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    fn mod_item(&mut self, node: Node<'_>, scope: &Scope, lead: &Lead<'_>) -> R<Option<NodeId>> {
        let Some((name_node, name)) = self.name_of(node) else {
            return Ok(None);
        };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        let ord = self.alloc();
        self.unit_stack.push(ord);
        let sig = self.sig_tokens(node, &[Some(name_node), body])?;
        let body_nodes = match body {
            Some(b) => self.container(b, &Scope::default(), true)?,
            None => Vec::new(),
        };
        self.unit_stack.pop();
        let role = if body.is_some() { "impl" } else { "sig" };
        let id = self.make_unit(
            ord,
            node,
            "module",
            role,
            &name,
            None,
            (Some(vis), scope.implements.as_deref(), &[]),
            lead,
            sig,
            body_nodes,
        )?;
        Ok(Some(id))
    }

    // ---- imports ----

    fn use_node(&mut self, node: Node<'_>) -> R<NodeId> {
        let public = children(node)
            .into_iter()
            .find(|k| k.kind() == "visibility_modifier")
            .is_some_and(|m| collapse_ws(self.t(m)) == "pub");
        let mut kids = Vec::new();
        if let Some(arg) = node.child_by_field_name("argument") {
            let mut paths = Vec::new();
            self.flatten_use(arg, &[], None, &mut paths);
            let container = self.unit_stack.last().copied();
            for (segs, alias) in paths {
                let target = self.normalize_import(&segs);
                let local = alias.unwrap_or_else(|| segs.last().cloned().unwrap_or_default());
                kids.push(
                    self.cx
                        .lit("use-path", &format!("{target} as {local}"), arg)?,
                );
                if self.fn_depth == 0 {
                    tracing::trace!(file = self.path, %target, "rust import");
                    self.uses.push(PendingUse {
                        container,
                        local,
                        target,
                        public,
                    });
                }
            }
        }
        if public {
            kids.push(self.cx.lit("visibility", "pub", node)?);
        }
        self.cx
            .op(Operator::adapter("rust", "use", Sort::Exp), node, &kids)
    }

    fn flatten_use(
        &self,
        node: Node<'_>,
        prefix: &[String],
        alias: Option<String>,
        out: &mut Vec<(Vec<String>, Option<String>)>,
    ) {
        let with = |segs: Vec<String>| {
            let mut v = prefix.to_vec();
            v.extend(segs);
            v
        };
        match node.kind() {
            "scoped_use_list" => {
                let mut pre = prefix.to_vec();
                if let Some(p) = node.child_by_field_name("path") {
                    pre.extend(split_path(self.t(p)));
                }
                if let Some(list) = node.child_by_field_name("list") {
                    self.flatten_use(list, &pre, None, out);
                }
            }
            "use_list" => {
                for ch in children(node)
                    .into_iter()
                    .filter(tree_sitter::Node::is_named)
                {
                    self.flatten_use(ch, prefix, None, out);
                }
            }
            "use_as_clause" => {
                let alias = node
                    .child_by_field_name("alias")
                    .map(|a| self.t(a).to_owned());
                if let Some(p) = node.child_by_field_name("path") {
                    self.flatten_use(p, prefix, alias, out);
                }
            }
            "use_wildcard" => {
                let mut segs = children(node)
                    .into_iter()
                    .find(tree_sitter::Node::is_named)
                    .map(|p| split_path(self.t(p)))
                    .unwrap_or_default();
                segs.push("*".to_owned());
                out.push((with(segs), Some("*".to_owned())));
            }
            "line_comment" | "block_comment" => {}
            _ => {
                let segs = split_path(self.t(node));
                if segs.len() == 1 && segs[0] == "self" && !prefix.is_empty() {
                    out.push((prefix.to_vec(), alias));
                } else {
                    out.push((with(segs), alias));
                }
            }
        }
    }

    fn normalize_import(&self, segs: &[String]) -> String {
        let join = |v: &[String]| v.join("::");
        match segs.first().map(String::as_str) {
            Some("self") => {
                let mut v = vec!["crate".to_owned()];
                v.extend(self.module.iter().cloned());
                v.extend(segs[1..].iter().cloned());
                join(&v)
            }
            Some("super") => {
                let mut module = self.module.clone();
                let mut i = 0;
                while segs.get(i).is_some_and(|s| s == "super") {
                    module.pop();
                    i += 1;
                }
                let mut v = vec!["crate".to_owned()];
                v.extend(module);
                v.extend(segs[i..].iter().cloned());
                join(&v)
            }
            _ => join(segs),
        }
    }
}
