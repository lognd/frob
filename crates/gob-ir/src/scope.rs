//! The scope graph with resolution status (universal-model.md 2.2 item 3).
//!
//! Scopes, declarations, references and labelled edges; every edge and
//! declaration carries a [`Status`]. Lexical nesting is one derived view
//! ([`ScopeGraph::from_term`]); adapters add imports, member and dispatch edges
//! at lower status with the builder methods. Opaque regions carry
//! [`OpaqueHint`]s that downgrade surrounding resolution.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fmt::Write as _;
use std::sync::OnceLock;
use std::sync::atomic::{AtomicBool, Ordering};

use tracing::{debug, trace};

use crate::Truth;
use crate::attrs::{AttrValue, reserved};
use crate::operator::{Operator, Universal};
use crate::term::{NodeId, Term};

/// How sure a resolution edge or declaration is; ordered `Unknown < May < Must`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Status {
    /// The edge may or may not exist; nothing is claimed.
    Unknown,
    /// The edge is in an over-approximation.
    May,
    /// The adapter proves the edge.
    Must,
}

impl Status {
    /// The weaker of two statuses (status of a path through two edges).
    #[must_use]
    pub fn meet(self, other: Self) -> Self {
        self.min(other)
    }
}

macro_rules! id_type {
    ($(#[$m:meta])* $name:ident) => {
        $(#[$m])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
        pub struct $name(pub(crate) u32);
        impl $name {
            /// The dense index.
            pub const fn index(self) -> usize { self.0 as usize }
        }
    };
}
id_type!(/// A scope.
    ScopeId);
id_type!(/// A declaration.
    DeclId);
id_type!(/// A reference (use site).
    RefId);

/// The label of a scope edge; lower labels are searched first and shadow later ones.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Label {
    /// Names brought in by an import.
    Import,
    /// Names inherited from a parent type or trait.
    Extends,
    /// An adapter-declared edge label (member, dispatch, ...).
    Custom(String),
    /// Lexical nesting: to the enclosing scope.
    Lexical,
}

impl Label {
    fn name(&self) -> &str {
        match self {
            Self::Import => "import",
            Self::Extends => "extends",
            Self::Custom(s) => s,
            Self::Lexical => "lexical",
        }
    }
}

/// What introduced a declaration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DeclKind {
    /// A `unit`: its name is part of its identity.
    Unit,
    /// A bound variable: its name is not significant (alpha-renamable).
    Binder,
    /// Any other adapter declaration.
    Other,
}

/// A declaration of a name in a scope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Decl {
    /// The declared name.
    pub name: String,
    /// Opaque qualifier distinguishing same-named declarations.
    pub qualifier: Option<String>,
    /// What introduced it.
    pub kind: DeclKind,
    /// The scope it lives in.
    pub scope: ScopeId,
    /// Whether the declaration certainly exists.
    pub status: Status,
    /// The term nodes that make up the declaration (several for a multi-part unit).
    pub nodes: Vec<NodeId>,
    /// A later binder of the same name in the same abstractor hides this one.
    pub shadowed: bool,
}

/// A use of a name in a scope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reference {
    /// The spelled name.
    pub name: String,
    /// The scope the use occurs in.
    pub scope: ScopeId,
    /// The `ref` node, when the reference comes from a term.
    pub node: Option<NodeId>,
}

/// A labelled edge between scopes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edge {
    /// Edge label.
    pub label: Label,
    /// Target scope.
    pub target: ScopeId,
    /// Edge status.
    pub status: Status,
}

/// Which names an opaque region may define.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum MayDefine {
    /// Nothing is claimed to be defined.
    #[default]
    Nothing,
    /// These names may be defined.
    Names(BTreeSet<String>),
    /// Any name may be defined (`eval`, a Template Haskell splice).
    Any,
}

impl MayDefine {
    fn covers(&self, name: &str) -> bool {
        match self {
            Self::Nothing => false,
            Self::Names(n) => n.contains(name),
            Self::Any => true,
        }
    }
}

/// Hints carried by an opaque region about its effect on the surrounding scope.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct OpaqueHint {
    /// Names the region may define in the scope.
    pub may_define: MayDefine,
    /// Whether the region may read any name of the scope.
    pub may_read_scope: bool,
    /// The opaque node, when it comes from a term.
    pub node: Option<NodeId>,
}

#[derive(Debug, Clone, Default)]
struct Scope {
    node: Option<NodeId>,
    edges: Vec<Edge>,
    decls: Vec<DeclId>,
    hints: Vec<OpaqueHint>,
}

/// The result of resolving a reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Resolution {
    /// Exactly this declaration, proven.
    Must(DeclId),
    /// The referent is one of these (an over-approximation).
    May(BTreeSet<DeclId>),
    /// Nothing can be claimed (undeclared, external, or poisoned).
    Unknown,
}

impl Resolution {
    /// The status of the resolution as a single value.
    pub fn status(&self) -> Status {
        match self {
            Self::Must(_) => Status::Must,
            Self::May(_) => Status::May,
            Self::Unknown => Status::Unknown,
        }
    }
}

/// The scope graph of one term (or one adapter run).
#[derive(Debug, Clone, Default)]
pub struct ScopeGraph {
    scopes: Vec<Scope>,
    decls: Vec<Decl>,
    refs: Vec<Reference>,
    ref_of_node: HashMap<NodeId, RefId>,
    decl_of_node: HashMap<NodeId, DeclId>,
    scope_of_node: HashMap<NodeId, ScopeId>,
    decl_index: HashMap<(ScopeId, String, Option<String>, bool), DeclId>,
    memo: Memo,
}

/// Per-reference resolution cache, keyed by `RefId` (one cell per reference).
///
/// Cells fill lazily on the first [`ScopeGraph::resolve`]; any graph mutation that can change a
/// resolution (an edge, a declaration, an opaque hint) empties them again.
#[derive(Debug, Default)]
struct Memo {
    cells: Vec<OnceLock<Resolution>>,
    /// Set once any cell was filled, so a mutation only pays to clear after a resolve.
    filled: AtomicBool,
}

impl Clone for Memo {
    fn clone(&self) -> Self {
        Self {
            cells: self.cells.clone(),
            filled: AtomicBool::new(self.filled.load(Ordering::Relaxed)),
        }
    }
}

impl Memo {
    /// Drop every cached resolution if any exist.
    fn invalidate(&mut self) {
        if *self.filled.get_mut() {
            trace!(cells = self.cells.len(), "resolution cache invalidated");
            for c in &mut self.cells {
                *c = OnceLock::new();
            }
            *self.filled.get_mut() = false;
        }
    }
}

#[derive(Default)]
struct Acc {
    cands: BTreeMap<DeclId, Status>,
    unknown: bool,
    downgraded: bool,
}

/// What entering a scope during a resolution search yielded.
enum Entered<'g> {
    /// The scope was already visited on this search.
    Seen,
    /// A proven declaration was found: end the search.
    Stop,
    /// Continue through these outgoing edges.
    Frame(Frame<'g>),
}

/// One scope on the search stack: its unvisited edges (next one last) and the path status.
struct Frame<'g> {
    edges: Vec<&'g Edge>,
    path: Status,
}

impl ScopeGraph {
    /// An empty graph.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a scope, optionally tied to a term node.
    pub fn add_scope(&mut self, node: Option<NodeId>) -> ScopeId {
        let id = ScopeId(crate::idx32(self.scopes.len()));
        self.scopes.push(Scope {
            node,
            ..Scope::default()
        });
        if let Some(n) = node {
            self.scope_of_node.insert(n, id);
        }
        id
    }

    /// Add a labelled edge `from -> to`.
    pub fn add_edge(&mut self, from: ScopeId, label: Label, to: ScopeId, status: Status) {
        trace!(
            from = from.0,
            to = to.0,
            label = label.name(),
            ?status,
            "scope edge"
        );
        self.memo.invalidate();
        self.scopes[from.index()].edges.push(Edge {
            label,
            target: to,
            status,
        });
    }

    /// Declare `name` in `scope`; a repeat of the same (scope, name, qualifier, kind) joins the
    /// existing declaration (multi-part units are one identity).
    pub fn declare(
        &mut self,
        scope: ScopeId,
        name: &str,
        qualifier: Option<&str>,
        kind: DeclKind,
        status: Status,
        node: Option<NodeId>,
    ) -> DeclId {
        self.memo.invalidate();
        let key = (
            scope,
            name.to_owned(),
            qualifier.map(str::to_owned),
            kind == DeclKind::Binder,
        );
        let id = if kind == DeclKind::Binder {
            None
        } else {
            self.decl_index.get(&key).copied()
        };
        let id = if let Some(id) = id {
            let d = &mut self.decls[id.index()];
            d.status = d.status.max(status);
            id
        } else {
            let id = DeclId(crate::idx32(self.decls.len()));
            if kind == DeclKind::Binder {
                for &prev in &self.scopes[scope.index()].decls {
                    let d = &mut self.decls[prev.index()];
                    if d.kind == DeclKind::Binder && d.name == name {
                        d.shadowed = true;
                    }
                }
            }
            self.decls.push(Decl {
                name: name.to_owned(),
                qualifier: qualifier.map(str::to_owned),
                kind,
                scope,
                status,
                nodes: Vec::new(),
                shadowed: false,
            });
            self.scopes[scope.index()].decls.push(id);
            self.decl_index.insert(key, id);
            id
        };
        if let Some(n) = node {
            self.decls[id.index()].nodes.push(n);
            self.decl_of_node.insert(n, id);
        }
        id
    }

    /// Record a use of `name` in `scope`.
    pub fn reference(&mut self, scope: ScopeId, name: &str, node: Option<NodeId>) -> RefId {
        let id = RefId(crate::idx32(self.refs.len()));
        self.refs.push(Reference {
            name: name.to_owned(),
            scope,
            node,
        });
        self.memo.cells.push(OnceLock::new());
        if let Some(n) = node {
            self.ref_of_node.insert(n, id);
        }
        id
    }

    /// Attach an opaque-region hint to `scope`.
    pub fn add_opaque(&mut self, scope: ScopeId, hint: OpaqueHint) {
        debug!(scope = scope.0, ?hint, "opaque region hint");
        self.memo.invalidate();
        self.scopes[scope.index()].hints.push(hint);
    }

    /// Number of scopes.
    pub fn scope_count(&self) -> usize {
        self.scopes.len()
    }
    /// All declarations in id order.
    pub fn decls(&self) -> &[Decl] {
        &self.decls
    }
    /// All references in id order.
    pub fn refs(&self) -> &[Reference] {
        &self.refs
    }
    /// The declaration with id `id`.
    pub fn decl(&self, id: DeclId) -> &Decl {
        &self.decls[id.index()]
    }
    /// The reference with id `id`.
    pub fn reference_of(&self, id: RefId) -> &Reference {
        &self.refs[id.index()]
    }
    /// The term node that opened `scope`, if any.
    pub fn scope_node(&self, scope: ScopeId) -> Option<NodeId> {
        self.scopes[scope.index()].node
    }
    /// Edges leaving `scope`.
    pub fn edges(&self, scope: ScopeId) -> &[Edge] {
        &self.scopes[scope.index()].edges
    }
    /// Opaque hints of `scope`.
    pub fn hints(&self, scope: ScopeId) -> &[OpaqueHint] {
        &self.scopes[scope.index()].hints
    }
    /// The reference made by a `ref` node.
    pub fn ref_at(&self, node: NodeId) -> Option<RefId> {
        self.ref_of_node.get(&node).copied()
    }
    /// The declaration a node belongs to.
    pub fn decl_at(&self, node: NodeId) -> Option<DeclId> {
        self.decl_of_node.get(&node).copied()
    }
    /// The scope opened by a node.
    pub fn scope_at(&self, node: NodeId) -> Option<ScopeId> {
        self.scope_of_node.get(&node).copied()
    }

    /// Resolve `name` as seen from `scope` (uncached; see [`Self::resolve`] for references).
    ///
    /// # Panics
    ///
    /// Never; the internal `expect` is guarded by a length check.
    pub fn resolve_name(&self, scope: ScopeId, name: &str) -> Resolution {
        let mut acc = Acc::default();
        self.search(scope, name, &mut acc);
        let res = if acc.unknown || acc.cands.is_empty() {
            Resolution::Unknown
        } else if !acc.downgraded
            && acc.cands.len() == 1
            && acc.cands.values().all(|s| *s == Status::Must)
        {
            Resolution::Must(*acc.cands.keys().next().expect("one candidate"))
        } else {
            Resolution::May(acc.cands.keys().copied().collect())
        };
        trace!(scope = scope.0, name, ?res, "resolved");
        res
    }

    /// Resolve a reference; the result is cached per reference until the graph next changes.
    pub fn resolve(&self, r: RefId) -> Resolution {
        let reference = &self.refs[r.index()];
        let cell = &self.memo.cells[r.index()];
        if let Some(hit) = cell.get() {
            trace!(reference = r.0, "resolution cache hit");
            return hit.clone();
        }
        let res = self.resolve_name(reference.scope, &reference.name);
        self.memo.filled.store(true, Ordering::Relaxed);
        cell.get_or_init(|| res).clone()
    }

    /// Enter `scope` on a path of status `path`: record its declarations and hints.
    fn enter(
        &self,
        scope: ScopeId,
        name: &str,
        path: Status,
        acc: &mut Acc,
        seen: &mut BTreeSet<ScopeId>,
    ) -> Entered<'_> {
        if !seen.insert(scope) {
            return Entered::Seen;
        }
        let sc = &self.scopes[scope.index()];
        if sc.hints.iter().any(|h| h.may_define.covers(name)) {
            acc.downgraded = true;
        }
        let mut stop = false;
        for &d in &sc.decls {
            let decl = &self.decls[d.index()];
            if decl.name != name || decl.shadowed {
                continue;
            }
            let st = path.meet(decl.status);
            if st == Status::Unknown {
                acc.unknown = true;
            } else {
                let e = acc.cands.entry(d).or_insert(st);
                *e = (*e).max(st);
                stop |= st == Status::Must;
            }
        }
        if stop {
            return Entered::Stop;
        }
        let mut edges: Vec<&Edge> = sc.edges.iter().collect();
        edges.sort_by(|a, b| a.label.cmp(&b.label).then(a.target.cmp(&b.target)));
        Entered::Frame(Frame {
            edges: edges.into_iter().rev().collect(),
            path,
        })
    }

    /// Depth-first search over edges with an explicit stack of frames; a proven (`Must`)
    /// declaration ends the whole search, as the recursive version did.
    fn search(&self, start: ScopeId, name: &str, acc: &mut Acc) {
        let mut seen = BTreeSet::new();
        let mut stack: Vec<Frame<'_>> = Vec::new();
        match self.enter(start, name, Status::Must, acc, &mut seen) {
            Entered::Frame(f) => stack.push(f),
            Entered::Stop | Entered::Seen => return,
        }
        while let Some(top) = stack.last_mut() {
            let Some(e) = top.edges.pop() else {
                stack.pop();
                continue;
            };
            let st = top.path.meet(e.status);
            if st == Status::Unknown {
                acc.unknown = true;
                continue;
            }
            match self.enter(e.target, name, st, acc, &mut seen) {
                Entered::Frame(f) => stack.push(f),
                Entered::Stop => return,
                Entered::Seen => {}
            }
        }
    }

    /// Whether some opaque region with `may_read_scope` can observe `decl`.
    ///
    /// `No` when no region sees the declaration's scope, `Unknown` otherwise (an opaque
    /// reader means the declaration may be used).
    pub fn may_be_read_by_opaque(&self, decl: DeclId) -> Truth {
        let target = self.decls[decl.index()].scope;
        for (i, sc) in self.scopes.iter().enumerate() {
            if !sc.hints.iter().any(|h| h.may_read_scope) {
                continue;
            }
            let mut cur = ScopeId(crate::idx32(i));
            let mut seen = BTreeSet::new();
            loop {
                if cur == target {
                    return Truth::Unknown;
                }
                if !seen.insert(cur) {
                    break;
                }
                let next = self.scopes[cur.index()]
                    .edges
                    .iter()
                    .find(|e| e.label == Label::Lexical)
                    .map(|e| e.target);
                match next {
                    Some(n) => cur = n,
                    None => break,
                }
            }
        }
        Truth::No
    }

    /// The lexical view of `term`: scopes from `unit`, `anon`, `bind` and binder-carrying
    /// adapter nodes, binder declarations, unit declarations, `ref` references, and opaque
    /// hints from reserved attributes. Every lexical edge is `Must`.
    pub fn from_term(term: &Term) -> Self {
        let mut g = Self::new();
        let root_scope = g.add_scope(None);
        g.walk(term, term.root(), root_scope);
        debug!(
            scopes = g.scopes.len(),
            decls = g.decls.len(),
            refs = g.refs.len(),
            "lexical scope graph derived"
        );
        g
    }

    /// Derive scopes, declarations, references and hints with an explicit-stack preorder walk.
    fn walk(&mut self, term: &Term, root: NodeId, root_scope: ScopeId) {
        let mut stack = vec![(root, root_scope)];
        while let Some((id, scope)) = stack.pop() {
            let node = term.node(id);
            let scopes_here = match &node.op {
                Operator::Universal(
                    Universal::Unit { .. } | Universal::Anon { .. } | Universal::Bind { .. },
                ) => true,
                Operator::Adapter(_) => !node.binders.is_empty(),
                Operator::Universal(_) => false,
            };
            if let Operator::Universal(Universal::Ref { name }) = &node.op {
                self.reference(scope, name, Some(id));
            }
            if matches!(
                node.op,
                Operator::Universal(Universal::Opaque { .. } | Universal::Phase { .. })
            ) && let Some(hint) = hint_from_attrs(node, id)
            {
                self.add_opaque(scope, hint);
            }
            let inner = if scopes_here {
                if matches!(node.op, Operator::Universal(Universal::Unit { .. }))
                    && let Some(name) = &node.name
                {
                    self.declare(
                        scope,
                        name,
                        node.attrs.get_str(reserved::QUALIFIER),
                        DeclKind::Unit,
                        Status::Must,
                        Some(id),
                    );
                }
                let s = self.add_scope(Some(id));
                self.add_edge(s, Label::Lexical, scope, Status::Must);
                for b in &node.binders {
                    self.declare(s, b, None, DeclKind::Binder, Status::Must, None);
                }
                s
            } else {
                scope
            };
            for (i, &c) in node.children.iter().enumerate().rev() {
                let sub = if node.op.binds_over(i) { inner } else { scope };
                stack.push((c, sub));
            }
        }
    }

    /// Deterministic text of the graph, alpha-invariant: binder names are erased and
    /// resolved references print declaration indices instead of names.
    pub fn canonical_stream(&self) -> String {
        let mut out = String::new();
        for (i, sc) in self.scopes.iter().enumerate() {
            let _ = write!(out, "S{i}");
            let mut edges: Vec<&Edge> = sc.edges.iter().collect();
            edges.sort_by(|a, b| a.label.cmp(&b.label).then(a.target.cmp(&b.target)));
            for e in edges {
                let _ = write!(out, " {}>S{}:{:?}", e.label.name(), e.target.0, e.status);
            }
            for h in &sc.hints {
                let _ = write!(out, " hint({:?},{})", h.may_define, h.may_read_scope);
            }
            out.push('\n');
        }
        for (i, d) in self.decls.iter().enumerate() {
            let name = if d.kind == DeclKind::Binder {
                "_"
            } else {
                d.name.as_str()
            };
            let _ = writeln!(
                out,
                "D{i} S{} {:?} {name:?} {:?}",
                d.scope.0, d.kind, d.status
            );
        }
        for (i, r) in self.refs.iter().enumerate() {
            let res = match self.resolve(RefId(crate::idx32(i))) {
                Resolution::Must(d) => format!("must D{}", d.0),
                Resolution::May(s) => {
                    let v: Vec<String> = s.iter().map(|d| format!("D{}", d.0)).collect();
                    format!("may {}", v.join(","))
                }
                Resolution::Unknown => format!("unknown {:?}", r.name),
            };
            let _ = writeln!(out, "R{i} S{} {res}", r.scope.0);
        }
        out
    }
}

fn hint_from_attrs(node: &crate::term::Node, id: NodeId) -> Option<OpaqueHint> {
    let may_define = match node.attrs.get(reserved::MAY_DEFINE) {
        Some(AttrValue::Str(s)) if s == "*" => MayDefine::Any,
        Some(AttrValue::List(items)) => MayDefine::Names(
            items
                .iter()
                .filter_map(|v| match v {
                    AttrValue::Str(s) => Some(s.clone()),
                    _ => None,
                })
                .collect(),
        ),
        _ => MayDefine::Nothing,
    };
    let may_read_scope = matches!(
        node.attrs.get(reserved::MAY_READ_SCOPE),
        Some(AttrValue::Bool(true))
    );
    if may_define == MayDefine::Nothing && !may_read_scope {
        return None;
    }
    Some(OpaqueHint {
        may_define,
        may_read_scope,
        node: Some(id),
    })
}
