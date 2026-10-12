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
use std::collections::{HashMap, HashSet};

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, Sort, TermError, reserved};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{
    Cx, base_file, call_text, children, failed_file, file_root_spec, line_of, local_binding,
    text_of,
};
use crate::model::{
    CallRef, CallSite, DeriveDecl, FieldDecl, FileSymbols, ImportEdge, MapKind, Receiver, RefKind,
    RefSite, RetType, SelfKind, UseBinding, Visibility, collapse_ws,
};
use crate::paths::crate_and_module;
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{
    self, ATTR_ARITY, ATTR_IMPLEMENTS, ATTR_RET, ATTR_RET_ARG, ATTR_RET_ARG2, ATTR_RET_TUPLE,
    ATTR_SELF_KIND, ATTR_VISIBILITY, HOLE_MISSING, HOLE_PARSE_ERROR, Naming,
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
        gob_caps::lang_fidelity(Lang::Rust)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Rust)
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
    /// Trait bounds of a generic qualifier.
    bound: Vec<String>,
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
    /// Trait bounds of a generic qualifier (`C::from_matches` with `C: Command`).
    bound: Vec<String>,
}

/// Methods whose closure argument (at the given position, with the given parameter count unless 0) receives the receiver's item as the listed parameters.
///
/// `Receiver::Item` of a receiver that is not a known standard iterable types nothing, so a method
/// that exists on other types too (`map` on a repository type) is harmless here.
const ITEM_CLOSURES: &[(&str, usize, &[usize], usize)] = &[
    ("map", 0, &[0], 0),
    ("filter", 0, &[0], 0),
    ("for_each", 0, &[0], 0),
    ("any", 0, &[0], 0),
    ("all", 0, &[0], 0),
    ("find", 0, &[0], 0),
    ("position", 0, &[0], 0),
    ("take_while", 0, &[0], 0),
    ("skip_while", 0, &[0], 0),
    ("filter_map", 0, &[0], 0),
    ("flat_map", 0, &[0], 0),
    ("inspect", 0, &[0], 0),
    ("find_map", 0, &[0], 0),
    ("max_by_key", 0, &[0], 0),
    ("min_by_key", 0, &[0], 0),
    ("map_while", 0, &[0], 0),
    ("partition", 0, &[0], 0),
    ("is_some_and", 0, &[0], 0),
    ("is_none_or", 0, &[0], 0),
    ("is_ok_and", 0, &[0], 0),
    ("and_then", 0, &[0], 0),
    ("map_or", 1, &[0], 0),
    ("map_or_else", 1, &[0], 0),
    ("retain", 0, &[0], 1),
    ("sort_by_key", 0, &[0], 0),
    ("sort_unstable_by_key", 0, &[0], 0),
    ("fold", 1, &[1], 0),
    ("max_by", 0, &[0, 1], 0),
    ("min_by", 0, &[0, 1], 0),
    ("sort_by", 0, &[0, 1], 0),
    ("sort_unstable_by", 0, &[0, 1], 0),
    ("reduce", 0, &[0, 1], 0),
];

/// The standard type built by `Type::new()`, `Type::from(..)`, `Type::with_capacity(..)` or `Type::default()`.
///
/// The graph ignores the answer when the repository declares a type of that name.
fn std_constructor<'p>(path: &'p [String], name: &str) -> Option<&'p str> {
    let [.., ty] = path else { return None };
    let ctor = matches!(name, "new" | "default" | "with_capacity" | "from");
    (ctor
        && matches!(
            ty.as_str(),
            "String" | "Vec" | "HashMap" | "HashSet" | "BTreeMap" | "BTreeSet" | "VecDeque"
        ))
    .then_some(ty.as_str())
}

/// The named, non-comment children of `n` other than a `mut` marker.
fn named_children(n: Node<'_>) -> Vec<Node<'_>> {
    children(n)
        .into_iter()
        .filter(|c| c.is_named() && !is_comment(*c) && c.kind() != "mutable_specifier")
        .collect()
}

/// The positional elements of a tuple or tuple-struct pattern, wildcards (`_`, an anonymous token) included.
fn pattern_elements(n: Node<'_>) -> Vec<Node<'_>> {
    children(n)
        .into_iter()
        .filter(|c| !is_comment(*c) && !matches!(c.kind(), "(" | ")" | "," | "::"))
        .collect()
}

/// True for the `..` rest element of a tuple or struct pattern.
fn is_rest_pattern(n: Node<'_>) -> bool {
    n.kind().contains("remaining") || n.kind().contains("rest") || n.kind() == ".."
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
    "matches",
    "vec",
];

/// `c` blanked for the synthetic text: newlines stay so line numbers match.
fn blank(c: u8) -> u8 {
    if c == b'\n' { b'\n' } else { b' ' }
}

/// The node of `kind` in the synthetic macro tree that starts at byte `at` (a call is matched by its callee).
fn find_synthetic<'t>(root: Node<'t>, kind: &str, at: usize) -> Option<Node<'t>> {
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        let start = match kind {
            "call_expression" => n.child_by_field_name("function").map(|f| f.start_byte()),
            _ => Some(n.start_byte()),
        };
        if n.kind() == kind && start == Some(at) {
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

/// The first named child of `n` that is not a lifetime.
fn first_named(n: Node<'_>) -> Option<Node<'_>> {
    children(n)
        .into_iter()
        .find(|c| c.is_named() && !matches!(c.kind(), "lifetime" | "lifetime_parameter"))
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
    /// `Result`/`Option` aliases whose first parameter is not the Ok/Some type.
    opaque_aliases: Vec<String>,
    /// The declared type of each module-level `const`/`static` outside function bodies, by name; `None` when the name is declared twice.
    consts: HashMap<String, Option<Receiver>>,
    /// The impl types being visited, innermost last (`Self` in `Self::NAME`).
    impl_types: Vec<String>,
    /// The derives of each struct and enum declared in this file.
    derives: Vec<DeriveDecl>,
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
fn leaves(n: Node<'_>) -> Vec<Node<'_>> {
    crate::fold::leaves(n, is_comment)
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
        opaque_aliases: Vec::new(),
        consts: HashMap::new(),
        impl_types: Vec::new(),
        derives: Vec::new(),
    };
    f.collect_consts(root, None);
    let kids = f.container(root, &Scope::default(), true)?;
    let root_id =
        f.cx.add(file_root_spec(&f.cx, input.size as usize), &kids)?;
    let Fold {
        cx,
        ord_nodes,
        sites,
        uses,
        fields,
        opaque_aliases,
        derives,
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
    for site in sites {
        if let Some(caller) = symref_of(site.caller) {
            push_site(&mut file, &scopes, site, caller);
        }
    }
    file.symbols = v.symbols;
    file.extras = v.extras;
    file.fields = fields;
    file.opaque_aliases = opaque_aliases;
    file.derives = derives;
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

/// Files `site` (found in `caller`) as a call or a value reference of `file`.
fn push_site(file: &mut FileSymbols, scopes: &ScopeGraph, s: Site, caller: Symref) {
    match s.kind {
        SiteKind::Call { method, in_macro } => {
            let local = local_binding(scopes, s.node, s.item_local);
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
                bound: s.bound,
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
                        bound: t.bound,
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
            bound: Vec::new(),
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
            bound: Vec::new(),
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
                    bound: Vec::new(),
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
                let bound_of: Vec<String> = qualifier
                    .as_ref()
                    .and_then(|q| self.bounds.iter().rev().find(|(n, _)| n == q))
                    .map(|(_, b)| b.clone())
                    .unwrap_or_default();
                CallTarget {
                    construct: upper_first(&leaf),
                    name: leaf,
                    qualifier,
                    method: false,
                    dynamic: false,
                    receiver: None,
                    opaque,
                    path: path.map(|p| split_path(self.t(p))).unwrap_or_default(),
                    bound: bound_of,
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
                    bound: Vec::new(),
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
            "identifier" => self.identifier_receiver(self.t(v)),
            "scoped_identifier" => self.scoped_receiver(v),
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
            "string_literal" | "raw_string_literal" => Receiver::Typed("str".to_owned()),
            "range_expression" => Receiver::Typed(crate::stdtypes::RANGE.to_owned()),
            "array_expression" => Receiver::Typed(crate::stdtypes::SLICE.to_owned()),
            "tuple_expression" => Receiver::Tuple(
                children(v)
                    .into_iter()
                    .filter(|c| c.is_named() && !is_comment(*c))
                    .map(|c| self.receiver_of(Some(c)))
                    .collect(),
            ),
            "struct_expression" => self.struct_literal_receiver(v),
            "macro_invocation" => match v
                .child_by_field_name("macro")
                .and_then(|m| self.t(m).rsplit("::").next())
            {
                Some("format") => Receiver::Typed("String".to_owned()),
                Some("vec") => Receiver::Typed("Vec".to_owned()),
                _ => Receiver::Expr,
            },
            "index_expression" => {
                let parts: Vec<Node<'_>> = children(v)
                    .into_iter()
                    .filter(|c| c.is_named() && !is_comment(*c))
                    .collect();
                match (parts.as_slice(), self.receiver_of(parts.first().copied())) {
                    (_, Receiver::Expr | Receiver::Bound(_)) => Receiver::Expr,
                    ([_, idx], b) if idx.kind() == "range_expression" => {
                        Receiver::Slice(Box::new(b))
                    }
                    ([_, _], b) => Receiver::Index(Box::new(b)),
                    _ => Receiver::Expr,
                }
            }
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

    /// The receiver of the bare name `name`: a typed local, a module-level constant, or a unit struct.
    fn identifier_receiver(&self, name: &str) -> Receiver {
        let local = self
            .env
            .borrow()
            .iter()
            .rev()
            .find(|(n, _)| n == name)
            .map(|(_, t)| t.clone());
        match local {
            Some(t) => t.unwrap_or(Receiver::Expr),
            None => self.consts.get(name).map_or_else(
                || {
                    if upper_first(name) && !self.locals.iter().any(|l| l == name) {
                        Receiver::Unit(name.to_owned())
                    } else {
                        Receiver::Expr
                    }
                },
                |t| t.clone().unwrap_or(Receiver::Expr),
            ),
        }
    }

    /// The receiver of a path value `Type::NAME` (an associated constant or unit variant).
    fn scoped_receiver(&self, v: Node<'_>) -> Receiver {
        let (Some(path), Some(name)) =
            (v.child_by_field_name("path"), v.child_by_field_name("name"))
        else {
            return Receiver::Expr;
        };
        let leaf = self.t(name);
        let base = match self.t(path) {
            "Self" => self.impl_types.last().cloned(),
            t if path.kind() == "identifier" && upper_first(t) => Some(t.to_owned()),
            _ => None,
        };
        match base {
            Some(b) if upper_first(leaf) => {
                Receiver::Assoc(Box::new(Receiver::Typed(b)), leaf.to_owned())
            }
            _ => Receiver::Expr,
        }
    }

    /// The collection a `source.collect::<C>()` call builds: the turbofish type, its `_` elements taken from the items of `source`.
    fn collect_receiver(&self, call: Node<'_>, source: &Receiver) -> Option<Receiver> {
        let f = call.child_by_field_name("function")?;
        let targs = (f.kind() == "generic_function")
            .then(|| f.child_by_field_name("type_arguments"))
            .flatten()?;
        let ty = children(targs)
            .into_iter()
            .find(|c| c.is_named() && c.kind() != "lifetime" && !is_comment(*c))?;
        self.collected(ty, source)
    }

    /// The receiver of the declared collection type `ty` filled from the iterator `source` (`Vec<_>`), or the type itself when fully written.
    fn collected(&self, ty: Node<'_>, source: &Receiver) -> Option<Receiver> {
        let shape = self.ret_type(ty)?;
        if shape.head == "String" && shape.arg.is_none() {
            return Some(Receiver::Typed("String".to_owned()));
        }
        if !crate::stdtypes::is_collection(&shape.head) {
            return None;
        }
        if shape.arg.as_deref() == Some("_") || (shape.arg.is_none() && shape.tuple.is_none()) {
            return Some(Receiver::Collected {
                shape: Box::new(shape),
                source: Box::new(source.clone()),
            });
        }
        Some(Receiver::Decl(Box::new(shape)))
    }

    /// The receiver standing for the value of the method call `v` (`t` its parsed head, `args` its argument count).
    fn method_receiver(&self, v: Node<'_>, t: CallTarget, args: usize) -> Receiver {
        if matches!(t.receiver, None | Some(Receiver::Expr | Receiver::Bound(_))) {
            return Receiver::Expr;
        }
        // `v.get(a..b)` is a slice, not an element.
        let range_arg = v
            .child_by_field_name("arguments")
            .and_then(|a| {
                children(a)
                    .into_iter()
                    .find(|c| c.is_named() && !is_comment(*c))
            })
            .is_some_and(|c| c.kind() == "range_expression");
        if range_arg && matches!(t.name.as_str(), "get" | "get_mut") {
            return Receiver::Expr;
        }
        let recv = t.receiver;
        if matches!(t.name.as_str(), "unwrap" | "expect") && args <= 1 {
            return recv.map_or(Receiver::Expr, |r| Receiver::Unwrap(Box::new(r)));
        }
        let kind = match t.name.as_str() {
            "map" => Some(MapKind::Map),
            "and_then" => Some(MapKind::AndThen),
            "filter_map" => Some(MapKind::FilterMap),
            _ => None,
        };
        if t.name == "collect"
            && args == 0
            && let Some(recv) = &recv
            && let Some(c) = self.collect_receiver(v, recv)
        {
            return c;
        }
        if let Some(kind) = kind
            && args == 1
            && let Some(recv) = &recv
            && let Some(result) = v
                .child_by_field_name("arguments")
                .and_then(|a| {
                    children(a)
                        .into_iter()
                        .find(|c| c.kind() == "closure_expression")
                })
                .and_then(|c| self.closure_result(c))
        {
            return Receiver::Mapped {
                recv: Box::new(recv.clone()),
                result: Box::new(result),
                kind,
            };
        }
        Receiver::Ret(Box::new(CallRef {
            name: t.name,
            path: Vec::new(),
            bound: Vec::new(),
            recv,
            args,
        }))
    }

    /// The receiver of a struct literal: its struct, or the enum of a struct-like variant (`Kind::A { .. }`).
    fn struct_literal_receiver(&self, v: Node<'_>) -> Receiver {
        let Some(name) = v.child_by_field_name("name") else {
            return Receiver::Expr;
        };
        let segs = split_path(self.t(name));
        let plain = || {
            self.plain_type(name)
                .map_or(Receiver::Expr, Receiver::Typed)
        };
        match segs.as_slice() {
            [s] if s == "Self" => self
                .impl_types
                .last()
                .cloned()
                .map_or(Receiver::Expr, Receiver::Typed),
            [.., ty, _] if upper_first(ty) => self
                .variant_owner(&segs[..segs.len() - 1])
                .map_or(Receiver::Expr, Receiver::Typed),
            _ => plain(),
        }
    }

    /// The enum type named by the path `owner` of a variant (`Kind`, `module::Kind`, `Self`).
    fn variant_owner(&self, owner: &[String]) -> Option<String> {
        match owner {
            [s] if s == "Self" => self.impl_types.last().cloned(),
            [] => None,
            _ => Some(owner.join("::")),
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
        if t.construct {
            // `Kind::A(..)`: the value of a tuple-variant constructor is the enum.
            return match t.path.as_slice() {
                [.., ty] if upper_first(ty) => self
                    .variant_owner(&t.path)
                    .map_or(Receiver::Expr, Receiver::Typed),
                _ => Receiver::Expr,
            };
        }
        if t.dynamic || (t.opaque && t.bound.is_empty()) {
            return Receiver::Expr;
        }
        if t.method {
            return self.method_receiver(v, t, args);
        }
        let bound =
            self.env.borrow().iter().any(|(n, _)| *n == t.name) || self.locals.contains(&t.name);
        if bound && t.path.is_empty() {
            return Receiver::Expr;
        }
        if let Some(std) = std_constructor(&t.path, &t.name) {
            return Receiver::Typed(std.to_owned());
        }
        // `Self::default()` is `Self` (`Default::default` returns `Self`; `new` is looked up by its signature).
        if t.name == "default" && args == 0 && t.path == ["Self"] {
            return self
                .impl_types
                .last()
                .cloned()
                .map_or(Receiver::Expr, Receiver::Typed);
        }
        Receiver::Ret(Box::new(CallRef {
            name: t.name,
            path: t.path,
            bound: t.bound,
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

    /// Records the declared types of the `const` and `static` items under `n` (not inside function bodies):
    /// module-level ones in `consts`, associated ones of an impl in the field table (`Type::NAME`).
    fn collect_consts(&mut self, n: Node<'_>, owner: Option<&str>) {
        for c in children(n) {
            match c.kind() {
                "const_item" | "static_item" => {
                    let (Some(name), ty) =
                        (c.child_by_field_name("name"), c.child_by_field_name("type"))
                    else {
                        continue;
                    };
                    let name = self.t(name).to_owned();
                    if let Some(owner) = owner {
                        if let Some(shape) = ty
                            .and_then(|t| self.ret_type(t))
                            .map(|r| self.subst_self(r))
                        {
                            self.push_field(owner, name, shape);
                        }
                    } else {
                        let recv = ty.and_then(|t| self.typed_receiver(t));
                        self.consts
                            .entry(name)
                            .and_modify(|e| *e = None)
                            .or_insert(recv);
                    }
                }
                "impl_item" => {
                    let owner = c.child_by_field_name("type").map(|t| self.type_name(t));
                    if let (Some(body), Some(owner)) = (c.child_by_field_name("body"), owner) {
                        let saved = self.enter_generics(c);
                        self.impl_types.push(owner.clone());
                        self.collect_consts(body, Some(&owner));
                        self.impl_types.pop();
                        self.leave_generics(saved);
                    }
                }
                "trait_item" | "function_item" | "closure_expression" | "macro_definition" => {}
                _ => self.collect_consts(c, owner),
            }
        }
    }

    /// `RefCell`, `Mutex` or `RwLock` when the generic type `t` is one: their lock/borrow methods are typed.
    fn cell_head(&self, t: Node<'_>) -> Option<&'static str> {
        let head = t.child_by_field_name("type")?;
        let name = self.t(head).rsplit("::").next().unwrap_or("");
        ["RefCell", "Mutex", "RwLock"]
            .into_iter()
            .find(|c| *c == name)
            .filter(|_| !self.generics.iter().any(|g| g == name))
    }

    /// The `T` of `impl Iterator<Item = T>` (also `IntoIterator`, `DoubleEndedIterator`, `ExactSizeIterator`), as a shape.
    fn iterator_item(&self, t: Node<'_>) -> Option<RetType> {
        let mut stack = vec![t];
        while let Some(n) = stack.pop() {
            if n.kind() == "generic_type"
                && let Some(head) = n.child_by_field_name("type")
                && matches!(
                    self.t(head),
                    "Iterator" | "IntoIterator" | "DoubleEndedIterator" | "ExactSizeIterator"
                )
                && let Some(args) = n.child_by_field_name("type_arguments")
            {
                let item = children(args).into_iter().find(|c| {
                    c.kind() == "type_binding"
                        && c.child_by_field_name("name")
                            .is_some_and(|b| self.t(b) == "Item")
                })?;
                return self.ret_type(item.child_by_field_name("type")?);
            }
            stack.extend(
                children(n)
                    .into_iter()
                    .filter(|c| c.kind() != "type_arguments"),
            );
        }
        None
    }

    /// `dyn:A+B` for a trait object type (`dyn A + B`, `Box<dyn A>`, `Arc<dyn A>`, `&dyn A`), else `None`.
    fn dyn_head(&self, t: Node<'_>) -> Option<String> {
        let obj = match t.kind() {
            "reference_type" => return self.dyn_head(t.child_by_field_name("type")?),
            "dynamic_type" => t,
            "generic_type" => {
                let head = self.t(t.child_by_field_name("type")?);
                if !matches!(head.rsplit("::").next(), Some("Box" | "Arc" | "Rc")) {
                    return None;
                }
                let args = t.child_by_field_name("type_arguments")?;
                let mut kids = children(args)
                    .into_iter()
                    .filter(|c| c.is_named() && c.kind() != "lifetime" && !is_comment(*c));
                let only = kids.next().filter(|_| kids.next().is_none())?;
                return self.dyn_head(only);
            }
            _ => return None,
        };
        let mut traits = self.trait_names(obj);
        traits.sort();
        traits.dedup();
        (!traits.is_empty()).then(|| format!("{}{}", crate::stdtypes::DYN, traits.join("+")))
    }

    /// A declared type reduced to its plain head, plain generic arguments and tuple elements.
    fn ret_type(&self, t: Node<'_>) -> Option<RetType> {
        let name = |n: Node<'_>| -> Option<String> {
            if n.kind() == "type_identifier" && self.t(n) == "Self" {
                return Some("Self".to_owned());
            }
            if self.t(n) == "_" {
                return Some("_".to_owned());
            }
            self.dyn_head(n).or_else(|| self.plain_type(n))
        };
        let tuple_elems = |n: Node<'_>| -> Option<Vec<Option<String>>> {
            let elems: Vec<Option<String>> = children(n)
                .into_iter()
                .filter(|c| c.is_named() && !is_comment(*c))
                .map(name)
                .collect();
            (n.kind() == "tuple_type" && !elems.is_empty()).then_some(elems)
        };
        match t.kind() {
            "reference_type" => self.ret_type(t.child_by_field_name("type")?),
            "abstract_type" => {
                let item = self.iterator_item(t)?;
                Some(crate::stdtypes::wrap(crate::stdtypes::ITER, &item))
            }
            "generic_type"
                if t.child_by_field_name("type")
                    .is_some_and(|h| self.t(h).rsplit("::").next() == Some("Cow")) =>
            {
                // `Cow<'_, str>` and `Cow<'_, [T]>` read as `str` and `[T]`: no repository type hides behind them.
                let arg = t.child_by_field_name("type_arguments").and_then(|a| {
                    children(a)
                        .into_iter()
                        .find(|c| c.is_named() && c.kind() != "lifetime" && !is_comment(*c))
                })?;
                self.ret_type(arg)
                    .filter(|r| r.head == "str" || r.head == crate::stdtypes::SLICE)
            }
            "generic_type" => {
                let head = self.cell_head(t).map_or_else(
                    || name(t.child_by_field_name("type")?),
                    |h| Some(h.to_owned()),
                )?;
                let mut args = t
                    .child_by_field_name("type_arguments")
                    .map(children)
                    .into_iter()
                    .flatten()
                    .filter(|c| c.is_named() && c.kind() != "lifetime" && !is_comment(*c));
                let first = args.next();
                let second = args.next();
                Some(RetType {
                    head,
                    arg: first.and_then(name),
                    arg2: second.and_then(name),
                    tuple: first.and_then(tuple_elems),
                })
            }
            "array_type" => {
                let elem = t.child_by_field_name("element")?;
                Some(RetType {
                    head: crate::stdtypes::SLICE.to_owned(),
                    arg: name(elem),
                    arg2: None,
                    tuple: tuple_elems(elem),
                })
            }
            "tuple_type" => tuple_elems(t).map(|elems| RetType {
                head: crate::stdtypes::TUPLE.to_owned(),
                arg: None,
                arg2: None,
                tuple: Some(elems),
            }),
            _ => Some(RetType {
                head: name(t)?,
                arg: None,
                arg2: None,
                tuple: None,
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
        let path = match t.kind() {
            "reference_type" => return self.plain_type(t.child_by_field_name("type")?),
            "type_identifier" | "primitive_type" => self.t(t).to_owned(),
            "scoped_type_identifier" => self.scoped_type_path(t)?,
            "generic_type" => {
                let head = t.child_by_field_name("type")?;
                match head.kind() {
                    "type_identifier" => self.t(head).to_owned(),
                    "scoped_type_identifier" => self.scoped_type_path(head)?,
                    _ => return None,
                }
            }
            _ => return None,
        };
        let name = path.rsplit("::").next().unwrap_or(&path);
        (name != "_" && !DEREF_WRAPPERS.contains(&name) && !self.generics.iter().any(|g| g == name))
            .then_some(path)
    }

    /// `module::Type` as written; `None` for associated types (`Self::Item`, `T::Output`), whose prefix is a type.
    fn scoped_type_path(&self, t: Node<'_>) -> Option<String> {
        let path = split_path(self.t(t.child_by_field_name("path")?));
        if !path.iter().all(|s| !upper_first(s)) {
            return None;
        }
        let name = self.t(t.child_by_field_name("name")?);
        Some(
            path.into_iter()
                .chain([name.to_owned()])
                .collect::<Vec<_>>()
                .join("::"),
        )
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
                if c.kind() == "type_parameter"
                    && let Some(l) = c.child_by_field_name("name")
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

    /// Types the binders of the pattern `p` (their slots are in `env[at..]`) as the parts of `value`.
    ///
    /// Plain binders take the value, tuple patterns its elements, `Some(x)`/`Ok(x)` its success value
    /// and enum-variant or struct patterns the declared field types. Or-patterns, slices, `@` bindings
    /// and anything after a `..` stay untyped.
    fn type_pattern(&self, at: usize, p: Node<'_>, value: &Receiver) {
        match p.kind() {
            "identifier" => self.set_slot(at, self.t(p), value),
            "mut_pattern" | "reference_pattern" | "ref_pattern" => {
                if let Some(inner) = named_children(p).into_iter().next() {
                    self.type_pattern(at, inner, value);
                }
            }
            "tuple_pattern" => {
                for (i, c) in pattern_elements(p).into_iter().enumerate() {
                    if is_rest_pattern(c) {
                        break;
                    }
                    let part = match value {
                        Receiver::Tuple(elems) => match elems.get(i) {
                            Some(Receiver::Expr) | None => continue,
                            Some(e) => e.clone(),
                        },
                        _ => Receiver::Elem(Box::new(value.clone()), i),
                    };
                    self.type_pattern(at, c, &part);
                }
            }
            "tuple_struct_pattern" => {
                let Some(path) = p.child_by_field_name("type") else {
                    return;
                };
                let segs = split_path(self.t(path));
                let elems: Vec<Node<'_>> = pattern_elements(p)
                    .into_iter()
                    .filter(|c| c.id() != path.id())
                    .collect();
                match (segs.as_slice(), elems.as_slice()) {
                    ([s], [one]) if s == "Some" || s == "Ok" => {
                        self.type_pattern(at, *one, &Receiver::Unwrap(Box::new(value.clone())));
                    }
                    (segs, _) if segs.len() >= 2 => {
                        for (i, c) in elems.into_iter().enumerate() {
                            if is_rest_pattern(c) {
                                break;
                            }
                            let field = Receiver::Variant {
                                path: segs.to_vec(),
                                field: i.to_string(),
                            };
                            self.type_pattern(at, c, &field);
                        }
                    }
                    _ => {}
                }
            }
            "struct_pattern" => {
                let Some(path) = p.child_by_field_name("type") else {
                    return;
                };
                let segs = split_path(self.t(path));
                for fp in named_children(p)
                    .into_iter()
                    .filter(|c| c.kind() == "field_pattern")
                {
                    let parts = named_children(fp);
                    let (name, sub) = match parts.as_slice() {
                        [n] => (*n, None),
                        [n, pat] => (*n, Some(*pat)),
                        _ => continue,
                    };
                    let field = self.t(name).to_owned();
                    let recv = match segs.as_slice() {
                        [s] if s == "Self" => {
                            Receiver::Field(Box::new(Receiver::SelfValue), field.clone())
                        }
                        [s] if upper_first(s) => {
                            Receiver::Field(Box::new(Receiver::Typed(s.clone())), field.clone())
                        }
                        segs if segs.len() >= 2 => Receiver::Variant {
                            path: segs.to_vec(),
                            field: field.clone(),
                        },
                        _ => continue,
                    };
                    match sub {
                        Some(pat) => self.type_pattern(at, pat, &recv),
                        None => self.set_slot(at, &field, &recv),
                    }
                }
            }
            _ => {}
        }
    }

    /// Declares the type of the variable `name` pushed at or after `env[at]`.
    fn set_slot(&self, at: usize, name: &str, ty: &Receiver) {
        if upper_first(name) {
            return;
        }
        let mut env = self.env.borrow_mut();
        if let Some(slot) = env.iter_mut().skip(at).find(|(n, _)| n == name) {
            slot.1 = Some(ty.clone());
        }
    }

    /// The receiver standing for the value of the `for`/closure/`if let` source `v`, when it is typed at all.
    fn typed_source(&self, v: Node<'_>) -> Option<Receiver> {
        match self.receiver_of(Some(v)) {
            Receiver::Expr | Receiver::Bound(_) => None,
            r => Some(r),
        }
    }

    /// The type of the body of closure `n` (an expression or a block holding only one), its parameters typed as in `closure`.
    fn closure_result(&self, n: Node<'_>) -> Option<Receiver> {
        let body = n.child_by_field_name("body")?;
        let tail = if body.kind() == "block" {
            let mut inner = children(body)
                .into_iter()
                .filter(|c| !matches!(c.kind(), "{" | "}") && !is_comment(*c));
            let only = inner.next()?;
            inner.next().is_none().then_some(only)?
        } else {
            body
        };
        let saved = self.env.borrow().len();
        if let Some(ps) = children(n)
            .into_iter()
            .find(|c| c.kind() == "closure_parameters")
        {
            self.bind_closure_params(n, ps);
        }
        let out = self.typed_source(tail);
        self.env.borrow_mut().truncate(saved);
        out
    }

    /// The receiver for the closure parameter `param` of closure `n`, when `n` is an argument of a method call
    /// whose receiver is typed and the method passes its item to the closure.
    fn closure_item(&self, n: Node<'_>, param: usize) -> Option<Receiver> {
        let args = n.parent().filter(|a| a.kind() == "arguments")?;
        let call = args.parent().filter(|c| c.kind() == "call_expression")?;
        let f = call.child_by_field_name("function")?;
        let f = if f.kind() == "generic_function" {
            f.child_by_field_name("function")?
        } else {
            f
        };
        if f.kind() != "field_expression" {
            return None;
        }
        let method = self.t(f.child_by_field_name("field")?);
        let pos = children(args)
            .into_iter()
            .filter(|c| c.is_named() && !is_comment(*c))
            .position(|c| c.id() == n.id())?;
        let arity = n.child_by_field_name("parameters").map_or(0, |ps| {
            children(ps)
                .into_iter()
                .filter(|x| x.is_named() && !is_comment(*x))
                .count()
        });
        let (_, _, params, want) = ITEM_CLOSURES
            .iter()
            .find(|(m, at, _, _)| *m == method && *at == pos)?;
        if !params.contains(&param) || (*want != 0 && *want != arity) {
            return None;
        }
        let recv = self.typed_source(f.child_by_field_name("value")?)?;
        Some(Receiver::Item(Box::new(recv)))
    }

    /// `shape` with `Self` replaced by the type of the impl being visited (a local declaration is read in the impl's own file).
    fn subst_self(&self, mut shape: RetType) -> RetType {
        let Some(me) = self.impl_types.last() else {
            return shape;
        };
        let fix = |s: &mut String| {
            if s == "Self" {
                me.clone_into(s);
            }
        };
        fix(&mut shape.head);
        shape.arg.iter_mut().for_each(fix);
        shape.arg2.iter_mut().for_each(fix);
        shape.tuple.iter_mut().flatten().flatten().for_each(fix);
        shape
    }

    /// The receiver that a declared type `t` stands for: a plain type (with its generic arguments), else its trait bounds.
    fn typed_receiver(&self, t: Node<'_>) -> Option<Receiver> {
        let mut peeled = t;
        while peeled.kind() == "reference_type" {
            peeled = peeled.child_by_field_name("type")?;
        }
        if peeled.kind() == "type_identifier" && self.t(peeled) == "Self" {
            return self.impl_types.last().cloned().map(Receiver::Typed);
        }
        let shape = self.ret_type(peeled).map(|r| self.subst_self(r));
        if matches!(peeled.kind(), "array_type" | "tuple_type") {
            return shape.map(|r| Receiver::Decl(Box::new(r)));
        }
        if let Some(r) = self.dyn_head(t) {
            return Some(Receiver::Decl(Box::new(RetType {
                head: r,
                arg: None,
                arg2: None,
                tuple: None,
            })));
        }
        if let Some(plain) = self.plain_type(t) {
            return Some(match shape {
                Some(r)
                    if r.head == plain
                        && (r.arg.is_some() || r.arg2.is_some() || r.tuple.is_some()) =>
                {
                    Receiver::Decl(Box::new(r))
                }
                _ => Receiver::Typed(plain),
            });
        }
        self.bound_receiver(t)
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
                bound: target.bound,
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
        let Some(synth) = self.synthetic_macro_text(name, tt) else {
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
        let a = tt.start_byte();
        let root = if name == "matches" {
            find_synthetic(tree.root(), "match_expression", a - 5)
        } else {
            find_synthetic(tree.root(), "call_expression", a - 1)
                .and_then(|c| c.child_by_field_name("arguments"))
        };
        let Some(root) = root else {
            return false;
        };
        let saved_env = self.env.borrow().len();
        self.macro_walk(root, caller, name);
        self.env.borrow_mut().truncate(saved_env);
        tracing::trace!(
            path = self.path,
            macro_name = name,
            "std macro arguments scanned as expressions"
        );
        true
    }

    /// The synthetic Rust text that re-parses the arguments of macro `name` (token tree `tt`) as expressions.
    ///
    /// Everything before the arguments is blanked so each node keeps its byte offset and line:
    /// `f(ARGS)` for most macros, `match E { P if G =>0 }` for `matches!(E, P if G)`, and `vec![x; n]`
    /// with its `;` read as a comma.
    fn synthetic_macro_text(&self, name: &str, tt: Node<'_>) -> Option<String> {
        let (a, b) = (tt.start_byte(), tt.end_byte());
        let bytes = self.cx.text.as_bytes();
        let is_matches = name == "matches";
        if a < if is_matches { 13 } else { 8 } || b > bytes.len() || b < a + 2 {
            return None;
        }
        let mut synth: Vec<u8> = bytes[..b]
            .iter()
            .enumerate()
            .map(|(i, &c)| if i < a { blank(c) } else { c })
            .collect();
        synth[..7].copy_from_slice(b"fn g(){");
        let top_level = |tok: &str| {
            children(tt)
                .into_iter()
                .find(|c| c.kind() == tok && c.child_count() == 0)
                .map(|c| c.start_byte())
        };
        if is_matches {
            // `matches!(E, P if G)` is `match E { P if G =>0 }`: the closing text lies past the real arguments.
            let comma = top_level(",")?;
            synth[a - 5..a].copy_from_slice(b"match");
            synth[a] = b' ';
            synth[comma] = b'{';
            synth[b - 1] = b' ';
        } else {
            synth[a - 1] = b'f';
            synth[a] = b'(';
            synth[b - 1] = b')';
            if name == "vec"
                && let Some(semi) = top_level(";")
            {
                synth[semi] = b',';
            }
        }
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
        synth.extend_from_slice(if is_matches { b"=>0};}" } else { b";}" });
        String::from_utf8(synth).ok()
    }

    /// Walks the parsed argument tree `x` of a std macro in scope order: records its call sites with
    /// the variables each pattern binds (typed where the source is typed) visible only where Rust scopes them.
    fn macro_walk(&mut self, x: Node<'_>, caller: usize, macro_name: &str) {
        match x.kind() {
            "closure_expression" => {
                let saved = self.env.borrow().len();
                for c in children(x) {
                    if c.kind() == "closure_parameters" {
                        self.bind_closure_params(x, c);
                    } else {
                        self.macro_walk(c, caller, macro_name);
                    }
                }
                self.env.borrow_mut().truncate(saved);
            }
            "match_expression" => {
                let scrutinee = x.child_by_field_name("value");
                if let Some(v) = scrutinee {
                    self.macro_walk(v, caller, macro_name);
                }
                let value = scrutinee.and_then(|v| self.typed_source(v));
                let Some(body) = x.child_by_field_name("body") else {
                    return;
                };
                for arm in children(body) {
                    let saved = self.env.borrow().len();
                    if arm.kind() == "match_arm" {
                        self.bind_arm(arm, value.as_ref());
                    }
                    for c in children(arm) {
                        self.macro_walk(c, caller, macro_name);
                    }
                    self.env.borrow_mut().truncate(saved);
                }
            }
            "for_expression" => {
                let source = x.child_by_field_name("value");
                if let Some(v) = source {
                    self.macro_walk(v, caller, macro_name);
                }
                let saved = self.env.borrow().len();
                if let Some(p) = x.child_by_field_name("pattern") {
                    let item = source
                        .and_then(|v| self.typed_source(v))
                        .map(|r| Receiver::Item(Box::new(r)));
                    let names = self.pattern_shape(p).0;
                    self.bind_typed(p, &names, item.as_ref());
                }
                if let Some(body) = x.child_by_field_name("body") {
                    self.macro_walk(body, caller, macro_name);
                }
                self.env.borrow_mut().truncate(saved);
            }
            "if_expression" | "while_expression" => {
                let saved = self.env.borrow().len();
                for c in children(x) {
                    if Some(c.id()) == x.child_by_field_name("alternative").map(|a| a.id()) {
                        self.env.borrow_mut().truncate(saved);
                    }
                    self.macro_walk(c, caller, macro_name);
                }
                self.env.borrow_mut().truncate(saved);
            }
            "let_condition" | "let_declaration" => {
                for c in children(x) {
                    if x.child_by_field_name("pattern")
                        .is_none_or(|p| p.id() != c.id())
                    {
                        self.macro_walk(c, caller, macro_name);
                    }
                }
                if let Some(p) = x.child_by_field_name("pattern") {
                    let value = x.child_by_field_name("value");
                    let declared = x
                        .child_by_field_name("type")
                        .and_then(|t| self.typed_receiver(t));
                    let ty = declared.or_else(|| value.and_then(|v| self.typed_source(v)));
                    let names = self.pattern_shape(p).0;
                    self.bind_typed(p, &names, ty.as_ref());
                }
            }
            "block" => {
                let saved = self.env.borrow().len();
                for c in children(x) {
                    self.macro_walk(c, caller, macro_name);
                }
                self.env.borrow_mut().truncate(saved);
            }
            _ => {
                self.exact_macro_node(x, caller, macro_name);
                if x.kind() != "macro_invocation" {
                    for c in children(x) {
                        self.macro_walk(c, caller, macro_name);
                    }
                }
            }
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
            bound: t.bound,
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
                            bound: Vec::new(),
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

    /// The variables a pattern binds (deduplicated, in order) and its shape text, without declaring them.
    fn pattern_shape(&self, p: Node<'_>) -> (Vec<String>, String) {
        let mut names: Vec<String> = Vec::new();
        let mut shape: Vec<String> = Vec::new();
        for l in leaves(p) {
            if self.is_binder_leaf(l) {
                let name = self.t(l).to_owned();
                if !names.contains(&name) {
                    names.push(name);
                }
                shape.push("_".to_owned());
            } else {
                shape.push(self.t(l).to_owned());
            }
        }
        (names, shape.join(" "))
    }

    /// Declares `names` as untyped variables in scope.
    fn declare(&self, names: &[String]) {
        let mut env = self.env.borrow_mut();
        env.extend(names.iter().map(|n| (n.clone(), None)));
    }

    /// Declares the binders of `p` and types them as the parts of `value` (when it is known).
    fn bind_typed(&self, p: Node<'_>, names: &[String], value: Option<&Receiver>) {
        let at = self.env.borrow().len();
        self.declare(names);
        if let Some(v) = value {
            self.type_pattern(at, p, v);
        }
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
        let pat = k.child_by_field_name("pattern");
        let (binders, shape) = pat.map_or((Vec::new(), String::new()), |p| self.pattern_shape(p));
        let mut rhs = vec![self.cx.lit("pattern", &shape, k)?];
        for field in ["type", "value", "alternative"] {
            if let Some(c) = k.child_by_field_name(field) {
                rhs.push(self.tr(c, depth + 1)?);
            }
        }
        // The value is typed against the variables in scope before the new ones shadow them.
        let declared = k
            .child_by_field_name("type")
            .and_then(|t| self.typed_receiver(t));
        let ty = self.collected_let(k).or(declared).or_else(|| {
            k.child_by_field_name("value")
                .and_then(|v| self.value_receiver(v))
        });
        match pat {
            Some(p) => self.bind_typed(p, &binders, ty.as_ref()),
            None => self.declare(&binders),
        }
        let rhs = self.cx.op(Operator::group(GroupOrder::Sequence), k, &rhs)?;
        let scope = self.rest_group(k, rest, depth)?;
        self.bind_node("let", k, &binders, scope, rhs)
    }

    /// For `let v: Vec<_> = it.collect();`, the collection filled from the items of `it`.
    fn collected_let(&self, k: Node<'_>) -> Option<Receiver> {
        let ty = k.child_by_field_name("type")?;
        let call = k.child_by_field_name("value")?;
        let f = call.child_by_field_name("function")?;
        if call.kind() != "call_expression"
            || f.kind() != "field_expression"
            || self.t(f.child_by_field_name("field")?) != "collect"
        {
            return None;
        }
        let source = self.typed_source(f.child_by_field_name("value")?)?;
        self.collected(ty, &source)
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
        let saved_env = self.env.borrow().len();
        for c in children(n) {
            if c.kind() == "closure_parameters" {
                for (names, shape, p) in self.bind_closure_params(n, c) {
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
        self.env.borrow_mut().truncate(saved_env);
        let names: Vec<&str> = binders.iter().map(String::as_str).collect();
        let spec = NodeSpec::new(Operator::anon("closure"), self.cx.node_loc(n)).binders(&names);
        self.cx.add(spec, &kids)
    }

    /// Declares the parameters `ps` of closure `n`, typed by their annotation or by the item the
    /// closure receives; returns each parameter's binders, pattern shape and node.
    fn bind_closure_params<'t>(
        &self,
        n: Node<'t>,
        ps: Node<'t>,
    ) -> Vec<(Vec<String>, String, Node<'t>)> {
        let params = children(ps)
            .into_iter()
            .filter(|x| x.is_named() && !is_comment(*x));
        let mut out = Vec::new();
        for (j, p) in params.enumerate() {
            let pat = if p.kind() == "parameter" {
                p.child_by_field_name("pattern").unwrap_or(p)
            } else {
                p
            };
            let (names, shape) = self.pattern_shape(pat);
            let annotated = p
                .child_by_field_name("type")
                .filter(|_| p.kind() == "parameter")
                .and_then(|t| self.typed_receiver(t));
            let ty = annotated.or_else(|| self.closure_item(n, j));
            self.bind_typed(pat, &names, ty.as_ref());
            out.push((names, shape, p));
        }
        out
    }

    /// Declares the binders of the match arm `arm` (typed from `value` when the arm has a single pattern); returns the binders and pattern shapes.
    fn bind_arm(&self, arm: Node<'_>, value: Option<&Receiver>) -> (Vec<String>, Vec<String>) {
        let mp = arm.child_by_field_name("pattern");
        let cond = mp.and_then(|m| m.child_by_field_name("condition"));
        let mut binders = Vec::new();
        let mut shapes = Vec::new();
        let Some(m) = mp else {
            return (binders, shapes);
        };
        let pats: Vec<Node<'_>> = children(m)
            .into_iter()
            .filter(|c| c.is_named() && cond.is_none_or(|x| x.id() != c.id()))
            .collect();
        for c in &pats {
            let (names, shape) = self.pattern_shape(*c);
            for nm in names {
                if !binders.contains(&nm) {
                    binders.push(nm);
                }
            }
            shapes.push(shape);
        }
        // One pattern types its binders; alternatives (`a | b`) leave them untyped.
        match pats.as_slice() {
            [only] => self.bind_typed(*only, &binders, value),
            _ => self.declare(&binders),
        }
        (binders, shapes)
    }

    fn match_expr(&mut self, n: Node<'_>, depth: usize) -> R<NodeId> {
        let mut kids = Vec::new();
        let scrutinee = n.child_by_field_name("value");
        if let Some(v) = scrutinee {
            kids.push(self.tr(v, depth + 1)?);
        }
        let value = scrutinee.and_then(|v| self.typed_source(v));
        if let Some(body) = n.child_by_field_name("body") {
            let mut arms = Vec::new();
            for c in children(body) {
                match c.kind() {
                    "match_arm" => arms.push(self.match_arm(c, value.as_ref(), depth + 2)?),
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

    fn match_arm(&mut self, arm: Node<'_>, value: Option<&Receiver>, depth: usize) -> R<NodeId> {
        let mp = arm.child_by_field_name("pattern");
        let cond = mp.and_then(|m| m.child_by_field_name("condition"));
        let saved_env = self.env.borrow().len();
        let (binders, shapes) = self.bind_arm(arm, value);
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
        self.env.borrow_mut().truncate(saved_env);
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
        let (binders, shape) = self.pattern_shape(p);
        let mut rhs = vec![self.cx.lit("pattern", &shape, p)?];
        let source = n.child_by_field_name("value");
        if let Some(v) = source {
            rhs.push(self.tr(v, depth + 1)?);
        }
        let item = source
            .and_then(|v| self.typed_source(v))
            .map(|r| Receiver::Item(Box::new(r)));
        let saved_env = self.env.borrow().len();
        self.bind_typed(p, &binders, item.as_ref());
        let rhs = self.cx.op(Operator::group(GroupOrder::Sequence), n, &rhs)?;
        let scope = self.tr(body, depth + 1)?;
        self.env.borrow_mut().truncate(saved_env);
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
                        for nm in self.pattern_shape(p).0 {
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
        let saved_env = self.env.borrow().len();
        let binders = self.cond_binders(cond);
        let body = n
            .child_by_field_name("consequence")
            .or_else(|| n.child_by_field_name("body"));
        let Some(body) = body.filter(|_| !binders.is_empty()) else {
            let out = self.generic(n, depth);
            self.env.borrow_mut().truncate(saved_env);
            return out;
        };
        let rhs = self.tr(cond, depth + 1)?;
        let scope = self.tr(body, depth + 1)?;
        // The `let` binders live in the consequence only.
        self.env.borrow_mut().truncate(saved_env);
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
        let pat = n.child_by_field_name("pattern");
        let names = pat.map(|p| {
            let (names, shape) = self.pattern_shape(p);
            (p, names, shape)
        });
        if let Some((p, _, shape)) = &names {
            kids.push(self.cx.lit("pattern", shape, *p)?);
        }
        let source = n.child_by_field_name("value");
        if let Some(v) = source {
            kids.push(self.tr(v, depth + 1)?);
        }
        if let Some((p, names, _)) = &names {
            let value = source.and_then(|v| self.typed_source(v));
            self.bind_typed(*p, names, value.as_ref());
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
                if let Some(a) = r.arg2 {
                    spec = spec.attr(ATTR_RET_ARG2, a.as_str());
                }
                if let Some(t) = r.tuple {
                    let joined: Vec<&str> = t.iter().map(|e| e.as_deref().unwrap_or("_")).collect();
                    spec = spec.attr(ATTR_RET_TUPLE, joined.join(",").as_str());
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
                        // frob:ticket 01M4FH86F1XAWKC7KQZSH5B4JE
                        // A plain comment (a `// frob:doc` line included) is whitespace to rustc: the
                        // `///` block above it still documents the item below.
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
            self.record_derives(&name, lead);
        }
        if kind == "type"
            && matches!(name.as_str(), "Result" | "Option")
            && !self.alias_keeps_first(node)
        {
            self.opaque_aliases.push(name.clone());
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

    /// True when the `type` item `node` is `type X<T, ..> = Result<T, ..>` (or `Option<T>`): its first parameter is the Ok/Some type.
    fn alias_keeps_first(&self, node: Node<'_>) -> bool {
        let param = node
            .child_by_field_name("type_parameters")
            .and_then(first_named)
            .and_then(|p| p.child_by_field_name("name").or(Some(p)))
            .map(|p| self.t(p).to_owned());
        let Some(rhs) = node.child_by_field_name("type") else {
            return false;
        };
        let head = (rhs.kind() == "generic_type")
            .then(|| rhs.child_by_field_name("type"))
            .flatten()
            .map(|h| self.t(h).rsplit("::").next().unwrap_or("").to_owned());
        let arg = rhs
            .child_by_field_name("type_arguments")
            .and_then(first_named)
            .map(|a| self.t(a).to_owned());
        matches!(head.as_deref(), Some("Result" | "Option")) && param.is_some() && param == arg
    }

    /// Records the `#[derive(..)]` traits among the attributes of the struct or enum `owner`.
    fn record_derives(&mut self, owner: &str, lead: &Lead<'_>) {
        let mut traits: Vec<String> = Vec::new();
        for a in &lead.attrs {
            let text = self.t(*a);
            let Some(start) = text.find("derive(") else {
                continue;
            };
            let inner = &text[start + "derive(".len()..];
            let Some(inner) = inner.split(')').next() else {
                continue;
            };
            traits.extend(
                inner
                    .split(',')
                    .filter_map(|t| t.trim().rsplit("::").next())
                    .filter(|t| !t.is_empty())
                    .map(str::to_owned),
            );
        }
        if !traits.is_empty() {
            tracing::trace!(path = self.path, owner, ?traits, "type derives");
            self.derives.push(DeriveDecl {
                owner: owner.to_owned(),
                traits,
            });
        }
    }

    /// Records the concrete-typed fields of the struct `node` named `owner` (the field type table).
    fn struct_fields(&mut self, node: Node<'_>, owner: &str) {
        let Some(list) = node.child_by_field_name("body") else {
            return;
        };
        let saved = self.enter_generics(node);
        self.record_fields(list, owner, "");
        self.leave_generics(saved);
    }

    /// Records the concrete-typed fields of every variant of the enum `node` named `owner` as `Variant.field`,
    /// and each unit variant as an associated value of the enum's own type (`Kind::Plain`).
    fn enum_fields(&mut self, node: Node<'_>, owner: &str) {
        let Some(list) = node.child_by_field_name("body") else {
            return;
        };
        let saved = self.enter_generics(node);
        for v in children(list)
            .into_iter()
            .filter(|c| c.kind() == "enum_variant")
        {
            let Some(name) = v.child_by_field_name("name") else {
                continue;
            };
            match v.child_by_field_name("body") {
                Some(body) => {
                    let prefix = format!("{}.", self.t(name));
                    self.record_fields(body, owner, &prefix);
                }
                None if self.generics.is_empty() => {
                    let own = RetType {
                        head: owner.to_owned(),
                        arg: None,
                        arg2: None,
                        tuple: None,
                    };
                    self.push_field(owner, self.t(name).to_owned(), own);
                }
                None => {}
            }
        }
        self.leave_generics(saved);
    }

    /// Records the typed fields of a named or tuple field list as `owner.<prefix><field>`.
    fn record_fields(&mut self, list: Node<'_>, owner: &str, prefix: &str) {
        match list.kind() {
            "field_declaration_list" => {
                for d in children(list)
                    .into_iter()
                    .filter(|c| c.kind() == "field_declaration")
                {
                    if let (Some(name), Some(ty)) = (
                        d.child_by_field_name("name"),
                        d.child_by_field_name("type").and_then(|t| self.ret_type(t)),
                    ) {
                        self.push_field(owner, format!("{prefix}{}", self.t(name)), ty);
                    }
                }
            }
            "ordered_field_declaration_list" => {
                let types = children(list)
                    .into_iter()
                    .filter(|c| c.is_named() && !is_comment(*c))
                    .filter(|c| !matches!(c.kind(), "attribute_item" | "visibility_modifier"));
                for (i, t) in types.enumerate() {
                    if let Some(ty) = self.ret_type(t) {
                        self.push_field(owner, format!("{prefix}{i}"), ty);
                    }
                }
            }
            _ => {}
        }
    }

    /// Adds one field to the field type table.
    fn push_field(&mut self, owner: &str, field: String, ty: RetType) {
        tracing::trace!(path = self.path, owner, %field, head = %ty.head, "field type");
        self.fields.push(FieldDecl {
            owner: owner.to_owned(),
            field,
            ty,
        });
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
                    let (names, mut shape) =
                        pat.map_or((Vec::new(), String::new()), |x| self.pattern_shape(x));
                    if children(p).iter().any(|c| c.kind() == "mutable_specifier") {
                        shape.insert_str(0, "mut ");
                    }
                    for nm in &names {
                        if !binders.contains(nm) {
                            binders.push(nm.clone());
                        }
                    }
                    let ty = p
                        .child_by_field_name("type")
                        .and_then(|t| self.typed_receiver(t));
                    match pat {
                        Some(x) => self.bind_typed(x, &names, ty.as_ref()),
                        None => self.declare(&names),
                    }
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
        self.enum_fields(node, &name);
        self.record_derives(&name, lead);
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
                self.impl_types.push(tname.clone());
                let out = self.container(b, &inner, false);
                self.impl_types.pop();
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
