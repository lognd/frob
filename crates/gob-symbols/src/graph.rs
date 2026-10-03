//! The repository-level symbol graph (petgraph) and its queries.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet, VecDeque};

pub use gob_ir::Status;

use gob_text::{TextRange, TextSize};
use petgraph::Direction;
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;

use crate::adapter::{Fidelity, ParseStatus};
use crate::model::{
    CallSite, Digests, FacetDigest, FileSymbols, ImportEdge, LocalBinding, Receiver, RefKind,
    RefSite, SymbolKind, SymbolRecord, UnitExtras, UseBinding, Visibility,
};
use crate::paths::crate_and_module;
use crate::qualifier::{Admit, CallQualifier};
use crate::symref::{Symref, Target, split_qual};

/// Kind of a graph edge.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum EdgeKind {
    /// Parent to child (file or container to member).
    Contains,
    /// Importing file to imported symbol or module file.
    Imports,
    /// Caller to callee.
    Calls,
    /// Any reference: a superset of [`EdgeKind::Calls`] that also holds functions
    /// used as values (G4).
    References,
    /// Markdown link from a section (or document) to a section or file.
    Links,
}

/// Edge payload.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Edge {
    kind: EdgeKind,
    /// Must, or May for a candidate among several or a dynamic target.
    status: Status,
}

/// Why a reference has no known target (an `Unknown` edge).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GapReason {
    /// No candidate in the crate: external or undeclared name.
    Unbound,
    /// The callee is an expression, not a name.
    Dynamic,
    /// The callee is a parameter, `let` binding or closure: a function value.
    LocalValue,
    /// A markdown link whose file or anchor does not exist.
    BrokenLink,
}

/// One edge with its resolution status; `to` is `None` for an `Unknown` edge.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StatusEdge {
    /// The referring symbol (a section or file for links).
    pub from: Symref,
    /// The target, `None` when nothing can be claimed.
    pub to: Option<Symref>,
    /// Edge kind (never `Contains`).
    pub kind: EdgeKind,
    /// Must, May or Unknown.
    pub status: Status,
    /// The spelled callee name or link destination (for `Unknown` edges).
    pub name: Option<String>,
    /// Why there is no target, for `Unknown` edges.
    pub reason: Option<GapReason>,
    /// What the unresolved call says about its callee; `None` when genuinely unknown.
    pub qualifier: Option<CallQualifier>,
    /// One-based source line of a call edge's site.
    pub line: Option<u32>,
    /// The callee expression as written at a call edge's site.
    pub text: Option<String>,
}

/// Facts about one walked file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileInfo {
    /// Adapter language tag; empty for an adapter-less file.
    pub language: String,
    /// Fidelity the file was folded at.
    pub fidelity: Fidelity,
    /// How completely it parsed (G11).
    pub parse_status: ParseStatus,
    /// True when no tree could be produced.
    pub degraded: bool,
}

impl FileInfo {
    /// True for an adapter-less file: one opaque unit at F0 (G19).
    pub fn is_opaque(&self) -> bool {
        self.fidelity == Fidelity::F0 && self.parse_status == ParseStatus::NotParsed
    }
}

/// A forward reachability result with statuses and poison.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct ReachSet {
    /// Everything reached, with the best status over all paths (the weakest edge of
    /// the strongest path); excludes the start symbol.
    pub reached: std::collections::BTreeMap<Symref, Status>,
    /// Symbols (the start included) whose own `Unknown` call edges poison the reach.
    pub poisoned_by: BTreeSet<Symref>,
}

impl ReachSet {
    /// True when no unresolved call can hide further reach.
    pub fn is_complete(&self) -> bool {
        self.poisoned_by.is_empty()
    }
}

/// A call after name resolution against the crate's symbols.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CallEdge {
    /// Exactly one candidate in the crate.
    Resolved {
        /// Calling function.
        caller: Symref,
        /// The single candidate.
        callee: Symref,
    },
    /// Several candidates (or one May candidate); all are kept as May edges.
    Ambiguous {
        /// Calling function.
        caller: Symref,
        /// Every candidate, sorted.
        candidates: Vec<Symref>,
    },
    /// No candidate in the crate (external or unknown).
    Unresolved {
        /// Calling function.
        caller: Symref,
        /// The simple callee name.
        name: String,
        /// What the call says about its callee; `None` when genuinely unknown.
        qualifier: Option<CallQualifier>,
    },
}

/// Failure of [`SymbolGraph::resolve`].
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ResolveError {
    /// Nothing matches.
    #[error("no symbol matches {0:?}")]
    NotFound(String),
    /// Several symbols match; the candidates are listed.
    #[error("ambiguous symbol, candidates: {}", .0.iter().map(ToString::to_string).collect::<Vec<_>>().join(", "))]
    Ambiguous(Vec<Symref>),
}

/// All symbols of a repository with Contains, Imports, Calls, References and
/// Links edges, each carrying a resolution [`Status`].
#[derive(Debug, Default)]
pub struct SymbolGraph {
    graph: DiGraph<SymbolRecord, Edge>,
    index: HashMap<Symref, NodeIndex>,
    imports: Vec<ImportEdge>,
    calls: Vec<CallEdge>,
    status_edges: Vec<StatusEdge>,
    files: BTreeMap<String, FileInfo>,
    extras: HashMap<Symref, UnitExtras>,
    /// Nodes owning at least one `Unknown` call edge (they poison forward reach).
    poisoned: HashSet<NodeIndex>,
    /// Nodes made public by a `pub use` re-export (G10).
    reexported: HashSet<NodeIndex>,
}

fn is_rust(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("rs"))
}

fn base_segment(s: &str) -> &str {
    s.split_once('[').map_or(s, |(b, _)| b)
}

/// Crate-level lookup tables shared by call, reference and link resolution.
struct Index {
    /// (crate dir, crate-relative item path) to nodes (files, modules, items).
    by_item: HashMap<(String, String), Vec<NodeIndex>>,
    /// (crate dir, simple name) to function and method nodes.
    by_name: HashMap<(String, String), Vec<NodeIndex>>,
    /// Importing file to its internal `use` bindings.
    uses: HashMap<String, Vec<UseBinding>>,
}

/// The outcome of resolving one reference site.
enum Outcome {
    /// Targets with the status of the edges to them.
    Hit(Vec<NodeIndex>, Status),
    /// Resolved inside the file (a nested item): no crate edge, no poison.
    Local,
    /// Nothing can be claimed.
    Gap(GapReason),
}

/// The crate-relative path of an internal import target (`crate::a::b` is `a::b`).
fn rel_path(target: &str) -> &str {
    let rel = target.strip_prefix("crate").unwrap_or("");
    rel.strip_prefix("::").unwrap_or(rel)
}

/// Normalizes a link destination against `file`; `None` for external links.
fn link_target(file: &str, dest: &str) -> Option<(String, Option<String>)> {
    let dest = dest.trim();
    if dest.contains("://") || dest.starts_with("mailto:") || dest.starts_with("tel:") {
        return None;
    }
    let dest = dest.split('?').next().unwrap_or(dest);
    let (path, frag) = match dest.split_once('#') {
        Some((p, f)) => (p, Some(f.to_lowercase())),
        None => (dest, None),
    };
    if path.is_empty() {
        return Some((file.to_owned(), frag));
    }
    let mut parts: Vec<&str> = if path.starts_with('/') {
        Vec::new()
    } else {
        let mut d: Vec<&str> = file.split('/').collect();
        d.pop();
        d
    };
    for seg in path.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop();
            }
            s => parts.push(s),
        }
    }
    Some((parts.join("/"), frag))
}

impl SymbolGraph {
    /// Builds the graph from per-file results (any order).
    pub fn from_files(mut files: Vec<FileSymbols>) -> Self {
        files.sort_by(|a, b| a.path.cmp(&b.path));
        let mut g = Self::default();
        for f in &files {
            g.add_file(f);
        }
        let idx = g.index_of(&files);
        g.link_imports(&idx);
        g.link_reexports(&files, &idx);
        g.link_calls(&files, &idx);
        g.link_refs(&files, &idx);
        tracing::debug!(
            nodes = g.graph.node_count(),
            edges = g.graph.edge_count(),
            unknown = g
                .status_edges
                .iter()
                .filter(|e| e.status == Status::Unknown)
                .count(),
            "symbol graph built"
        );
        g
    }

    fn add_node(&mut self, rec: SymbolRecord) -> NodeIndex {
        let key = rec.symref.clone();
        let idx = self.graph.add_node(rec);
        self.index.insert(key, idx);
        idx
    }

    fn link(&mut self, a: NodeIndex, b: NodeIndex, kind: EdgeKind, status: Status) {
        let existing = self
            .graph
            .edges_connecting(a, b)
            .find(|e| e.weight().kind == kind)
            .map(|e| e.id());
        match existing {
            Some(id) => {
                let w = &mut self.graph[id];
                w.status = w.status.max(status);
            }
            None => {
                self.graph.add_edge(a, b, Edge { kind, status });
            }
        }
    }

    fn add_file(&mut self, f: &FileSymbols) {
        let file_ref = Symref::file(&f.path);
        let digest = FacetDigest::of(f.file_digest.as_bytes());
        let empty = FacetDigest::of(b"");
        let file_node = self.add_node(SymbolRecord {
            symref: file_ref,
            kind: SymbolKind::Module,
            span: TextRange::new(TextSize::new(0), TextSize::new(f.size)),
            visibility: Visibility::Public,
            digests: Digests {
                sig: empty,
                body: digest,
                doc: empty,
                attr: empty,
                contract: empty,
            },
            parent: None,
            implements: None,
        });
        for s in &f.symbols {
            self.add_node(s.clone());
        }
        for s in &f.symbols {
            let child = self.index[&s.symref];
            let parent = s
                .parent
                .as_ref()
                .and_then(|p| self.index.get(p).copied())
                .unwrap_or(file_node);
            self.link(parent, child, EdgeKind::Contains, Status::Must);
        }
        for e in &f.extras {
            self.extras.insert(e.symref.clone(), e.clone());
        }
        self.files.insert(
            f.path.clone(),
            FileInfo {
                language: f.language.clone(),
                fidelity: f.fidelity,
                parse_status: f.parse_status.clone(),
                degraded: f.degraded,
            },
        );
        self.imports.extend(f.imports.iter().cloned());
    }

    fn index_of(&self, files: &[FileSymbols]) -> Index {
        let mut idx = Index {
            by_item: HashMap::new(),
            by_name: HashMap::new(),
            uses: HashMap::new(),
        };
        for f in files.iter().filter(|f| is_rust(&f.path)) {
            let (krate, module) = crate_and_module(&f.path);
            idx.by_item
                .entry((krate.clone(), module.join("::")))
                .or_default()
                .push(self.index[&Symref::file(&f.path)]);
            for s in &f.symbols {
                let mut segs = module.clone();
                segs.extend(
                    s.symref
                        .segments()
                        .iter()
                        .map(|g| base_segment(g).to_owned()),
                );
                let node = self.index[&s.symref];
                idx.by_item
                    .entry((krate.clone(), segs.join("::")))
                    .or_default()
                    .push(node);
                if matches!(s.kind, SymbolKind::Function | SymbolKind::Method)
                    && let Some(n) = s.symref.name()
                {
                    idx.by_name
                        .entry((krate.clone(), n.to_owned()))
                        .or_default()
                        .push(node);
                }
            }
            idx.uses.insert(
                f.path.clone(),
                f.uses.iter().filter(|u| u.is_internal()).cloned().collect(),
            );
        }
        idx
    }

    fn link_imports(&mut self, idx: &Index) {
        let edges = self.imports.clone();
        for imp in edges.iter().filter(|i| i.is_internal()) {
            let (krate, _) = crate_and_module(&imp.from_file);
            let rel = rel_path(&imp.target);
            let rel = rel
                .strip_suffix("::*")
                .unwrap_or(if rel == "*" { "" } else { rel });
            let Some(targets) = idx.by_item.get(&(krate, rel.to_owned())) else {
                tracing::trace!(target = %imp.target, "internal import unresolved");
                continue;
            };
            let from = self.index[&Symref::file(&imp.from_file)];
            for &t in targets {
                if t != from {
                    self.link(from, t, EdgeKind::Imports, Status::Must);
                }
            }
        }
    }

    /// Marks the targets of public `use` items as exported (G10).
    fn link_reexports(&mut self, files: &[FileSymbols], idx: &Index) {
        for f in files {
            let (krate, _) = crate_and_module(&f.path);
            for u in f.uses.iter().filter(|u| u.public && u.is_internal()) {
                let visible = u
                    .container
                    .as_ref()
                    .is_none_or(|c| self.index.get(c).is_some_and(|&n| self.chain_public(n)));
                if !visible {
                    continue;
                }
                let glob = u.target.ends_with("::*");
                let rel = rel_path(&u.target);
                let rel = rel.strip_suffix("::*").unwrap_or(rel);
                let Some(targets) = idx.by_item.get(&(krate.clone(), rel.to_owned())) else {
                    tracing::trace!(target = %u.target, "re-export target unresolved");
                    continue;
                };
                for &t in targets {
                    if glob {
                        let kids: Vec<NodeIndex> = self
                            .graph
                            .edges_directed(t, Direction::Outgoing)
                            .filter(|e| e.weight().kind == EdgeKind::Contains)
                            .map(|e| e.target())
                            .filter(|&k| self.graph[k].visibility == Visibility::Public)
                            .collect();
                        self.reexported.extend(kids);
                    } else {
                        self.reexported.insert(t);
                    }
                }
            }
        }
        tracing::debug!(roots = self.reexported.len(), "re-export roots");
    }

    /// True when `n` and all its containers are `pub` (no re-exports considered).
    fn chain_public(&self, mut n: NodeIndex) -> bool {
        loop {
            if self.graph[n].visibility != Visibility::Public {
                return false;
            }
            match self.parent_of(n) {
                Some(p) => n = p,
                None => return true,
            }
        }
    }

    /// Resolves a call or value reference by name, imports and qualifier.
    fn resolve_site(
        &self,
        idx: &Index,
        caller: &Symref,
        site: (&str, Option<&str>, bool),
        receiver: Option<&Receiver>,
        local: LocalBinding,
    ) -> Outcome {
        let (name, qualifier, method) = site;
        match local {
            LocalBinding::Item => return Outcome::Local,
            LocalBinding::Value => return Outcome::Gap(GapReason::LocalValue),
            LocalBinding::None => {}
        }
        if name.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        let file = caller.path();
        let (krate, _) = crate_and_module(file);
        let named: Vec<NodeIndex> = idx
            .by_name
            .get(&(krate.clone(), name.to_owned()))
            .cloned()
            .unwrap_or_default();
        let uses = idx.uses.get(file).map_or(&[][..], Vec::as_slice);
        if method {
            let own = match receiver {
                Some(Receiver::SelfValue) => self.enclosing_impl_type(caller),
                Some(Receiver::Typed(t)) => Some(t.clone()),
                _ => None,
            };
            if let Some(t) = own {
                let mine: Vec<NodeIndex> = named
                    .iter()
                    .copied()
                    .filter(|&n| {
                        let r = &self.graph[n];
                        let segs = r.symref.segments();
                        r.kind == SymbolKind::Method
                            && segs
                                .len()
                                .checked_sub(2)
                                .is_some_and(|i| base_segment(&segs[i]) == t)
                    })
                    .collect();
                if let [one] = mine.as_slice() {
                    let sure = self.graph[*one].implements.is_none();
                    return Outcome::Hit(mine, if sure { Status::Must } else { Status::May });
                }
                if !mine.is_empty() {
                    return Outcome::Hit(mine, Status::May);
                }
            }
            // Receiver type unknown (or not found): every method of that name may be it.
            let cands: Vec<NodeIndex> = named
                .into_iter()
                .filter(|&n| self.graph[n].kind == SymbolKind::Method)
                .collect();
            return if cands.is_empty() {
                Outcome::Gap(GapReason::Unbound)
            } else {
                Outcome::Hit(cands, Status::May)
            };
        }
        match qualifier {
            Some(q) => self.resolve_qualified(caller, q, named, uses),
            None => self.resolve_bare(idx, &krate, file, name, named, uses),
        }
    }

    /// `Q::name(..)`: candidates whose enclosing type or module is `Q`.
    fn resolve_qualified(
        &self,
        caller: &Symref,
        qualifier: &str,
        named: Vec<NodeIndex>,
        uses: &[UseBinding],
    ) -> Outcome {
        let q = if qualifier == "Self" {
            let segs = caller.segments();
            segs.len()
                .checked_sub(2)
                .map(|i| base_segment(&segs[i]).to_owned())
        } else {
            Some(
                uses.iter()
                    .find(|u| u.local == qualifier && !u.target.ends_with("::*"))
                    .and_then(|u| u.target.rsplit("::").next().map(str::to_owned))
                    .unwrap_or_else(|| qualifier.to_owned()),
            )
        };
        let cands: Vec<NodeIndex> = named
            .into_iter()
            .filter(|&n| {
                let r = &self.graph[n];
                let segs = r.symref.segments();
                let parent_seg = segs.len().checked_sub(2).map(|i| base_segment(&segs[i]));
                let (_, module) = crate_and_module(r.symref.path());
                match &q {
                    Some(q) => parent_seg == Some(q.as_str()) || module.last() == Some(q),
                    None => true,
                }
            })
            .collect();
        match cands.as_slice() {
            [] => Outcome::Gap(GapReason::Unbound),
            [one] => {
                let r = &self.graph[*one];
                let sure = r.kind == SymbolKind::Function || r.implements.is_none();
                let status = if sure { Status::Must } else { Status::May };
                Outcome::Hit(cands, status)
            }
            _ => Outcome::Hit(cands, Status::May),
        }
    }

    fn only_free(&self, nodes: Vec<NodeIndex>) -> Vec<NodeIndex> {
        nodes
            .into_iter()
            .filter(|&n| self.graph[n].kind == SymbolKind::Function)
            .collect()
    }

    /// `name(..)`: explicit import, same file, glob import, then the whole crate.
    fn resolve_bare(
        &self,
        idx: &Index,
        krate: &str,
        file: &str,
        name: &str,
        named: Vec<NodeIndex>,
        uses: &[UseBinding],
    ) -> Outcome {
        let one_or_many = |cands: Vec<NodeIndex>| {
            let st = if cands.len() == 1 {
                Status::Must
            } else {
                Status::May
            };
            Outcome::Hit(cands, st)
        };
        let item_key = |rel: &str| (krate.to_owned(), rel.to_owned());
        for u in uses.iter().filter(|u| u.local == name) {
            if let Some(nodes) = idx.by_item.get(&item_key(rel_path(&u.target))) {
                let cands = self.only_free(nodes.clone());
                if !cands.is_empty() {
                    return one_or_many(cands);
                }
            }
        }
        let same_file: Vec<NodeIndex> = self
            .only_free(named.clone())
            .into_iter()
            .filter(|&n| self.graph[n].symref.path() == file)
            .collect();
        if !same_file.is_empty() {
            return one_or_many(same_file);
        }
        let mut globbed = Vec::new();
        for u in uses.iter().filter(|u| u.target.ends_with("::*")) {
            let rel = rel_path(&u.target);
            let rel = rel.strip_suffix("::*").unwrap_or(rel);
            let key = if rel.is_empty() {
                name.to_owned()
            } else {
                format!("{rel}::{name}")
            };
            if let Some(nodes) = idx.by_item.get(&item_key(&key)) {
                globbed.extend(self.only_free(nodes.clone()));
            }
        }
        if !globbed.is_empty() {
            globbed.sort();
            globbed.dedup();
            return Outcome::Hit(globbed, Status::May);
        }
        let cands = self.only_free(named);
        if cands.is_empty() {
            Outcome::Gap(GapReason::Unbound)
        } else {
            one_or_many(cands)
        }
    }

    fn link_calls(&mut self, files: &[FileSymbols], idx: &Index) {
        let aliases: HashSet<String> = self
            .graph
            .node_weights()
            .filter(|r| r.kind == SymbolKind::TypeAlias)
            .filter_map(|r| r.symref.name().map(str::to_owned))
            .collect();
        for f in files {
            for call in &f.calls {
                let outcome = self.resolve_site(
                    idx,
                    &call.caller,
                    (&call.callee, call.qualifier.as_deref(), call.method),
                    call.receiver.as_ref(),
                    call.local,
                );
                let qualifier = self.call_qualifier(idx, call, &aliases);
                self.record_call(call, outcome, qualifier);
            }
        }
    }

    /// The type of the impl that directly contains `caller`, when it is a method of one.
    fn enclosing_impl_type(&self, caller: &Symref) -> Option<String> {
        let parent = self.parent_of(*self.index.get(caller)?)?;
        if self.graph[parent].kind != SymbolKind::Impl {
            return None;
        }
        let segs = caller.segments();
        let i = segs.len().checked_sub(2)?;
        Some(base_segment(&segs[i]).to_owned())
    }

    /// What an unresolved `call` says about its callee (`None` when genuinely unknown).
    fn call_qualifier(
        &self,
        idx: &Index,
        call: &CallSite,
        aliases: &HashSet<String>,
    ) -> Option<CallQualifier> {
        if call.opaque_qualifier || call.callee.is_empty() {
            return None;
        }
        if call.method {
            return Some(match &call.receiver {
                Some(Receiver::SelfValue) => self
                    .enclosing_impl_type(&call.caller)
                    .map_or(CallQualifier::Receiver, CallQualifier::SelfType),
                Some(Receiver::Typed(t)) if !aliases.contains(t) => CallQualifier::Typed(t.clone()),
                _ => CallQualifier::Receiver,
            });
        }
        let q = call.qualifier.as_deref()?;
        let real = match q {
            "crate" | "self" | "super" => return None,
            "Self" => self.enclosing_impl_type(&call.caller)?,
            _ => idx
                .uses
                .get(call.caller.path())
                .into_iter()
                .flatten()
                .find(|u| u.local == q && !u.target.ends_with("::*"))
                .and_then(|u| u.target.rsplit("::").next().map(str::to_owned))
                .unwrap_or_else(|| q.to_owned()),
        };
        (!aliases.contains(&real)).then_some(CallQualifier::Path(real))
    }

    /// Whether the qualified unresolved call `q` could be a call of `rec` (never guesses: doubt is `Maybe`).
    pub fn admits(&self, q: &CallQualifier, rec: &SymbolRecord) -> Admit {
        if !matches!(rec.kind, SymbolKind::Function | SymbolKind::Method) {
            return Admit::No;
        }
        let segs = rec.symref.segments();
        let parent = segs.len().checked_sub(2).map(|i| base_segment(&segs[i]));
        let parent_is_trait = self
            .index
            .get(&rec.symref)
            .and_then(|&n| self.parent_of(n))
            .is_some_and(|p| self.graph[p].kind == SymbolKind::Trait);
        match q {
            CallQualifier::Path(t) => {
                let (_, module) = crate_and_module(rec.symref.path());
                if parent == Some(t.as_str()) || module.last() == Some(t) {
                    Admit::Pinned
                } else if parent_is_trait
                    || (rec.kind == SymbolKind::Function && t.starts_with(char::is_lowercase))
                {
                    Admit::Maybe
                } else {
                    Admit::No
                }
            }
            CallQualifier::SelfType(t) | CallQualifier::Typed(t) => {
                if rec.kind != SymbolKind::Method {
                    Admit::No
                } else if parent == Some(t.as_str()) {
                    Admit::Pinned
                } else if parent_is_trait {
                    Admit::Maybe
                } else {
                    Admit::No
                }
            }
            CallQualifier::Receiver => {
                if rec.kind == SymbolKind::Method {
                    Admit::Maybe
                } else {
                    Admit::No
                }
            }
        }
    }

    fn record_call(&mut self, call: &CallSite, outcome: Outcome, qualifier: Option<CallQualifier>) {
        let caller = &call.caller;
        let from = self.index.get(caller).copied();
        match outcome {
            Outcome::Local => {}
            Outcome::Gap(reason) => {
                let name = if call.callee.is_empty() {
                    "<dynamic>".to_owned()
                } else {
                    call.callee.clone()
                };
                tracing::debug!(
                    caller = %caller,
                    name = %name,
                    ?qualifier,
                    line = call.line,
                    "unresolved call recorded with qualifier"
                );
                self.calls.push(CallEdge::Unresolved {
                    caller: caller.clone(),
                    name: name.clone(),
                    qualifier: qualifier.clone(),
                });
                self.status_edges.push(StatusEdge {
                    from: caller.clone(),
                    to: None,
                    kind: EdgeKind::Calls,
                    status: Status::Unknown,
                    name: Some(name),
                    reason: Some(reason),
                    qualifier,
                    line: Some(call.line),
                    text: Some(call.text.clone()),
                });
                if let Some(a) = from {
                    self.poisoned.insert(a);
                }
            }
            Outcome::Hit(nodes, status) => {
                let status = if call.in_macro {
                    status.meet(Status::May)
                } else {
                    status
                };
                let mut found: Vec<Symref> = nodes
                    .iter()
                    .map(|&n| self.graph[n].symref.clone())
                    .collect();
                found.sort();
                found.dedup();
                if let (Some(a), true) = (from, true) {
                    for &n in &nodes {
                        self.link(a, n, EdgeKind::Calls, status);
                        self.link(a, n, EdgeKind::References, status);
                    }
                }
                for to in &found {
                    self.status_edges.push(StatusEdge {
                        from: caller.clone(),
                        to: Some(to.clone()),
                        kind: EdgeKind::Calls,
                        status,
                        name: None,
                        reason: None,
                        qualifier: None,
                        line: Some(call.line),
                        text: Some(call.text.clone()),
                    });
                }
                self.calls.push(match (status, found.len()) {
                    (Status::Must, 1) => CallEdge::Resolved {
                        caller: caller.clone(),
                        callee: found.remove(0),
                    },
                    _ => CallEdge::Ambiguous {
                        caller: caller.clone(),
                        candidates: found,
                    },
                });
            }
        }
    }

    fn link_refs(&mut self, files: &[FileSymbols], idx: &Index) {
        for f in files {
            for r in &f.refs {
                match r.kind {
                    RefKind::Value => self.link_value(r, idx),
                    RefKind::Link => self.link_link(r),
                }
            }
        }
    }

    /// A function used as a value is a May reference edge (G4).
    fn link_value(&mut self, r: &RefSite, idx: &Index) {
        let outcome = self.resolve_site(
            idx,
            &r.from,
            (&r.name, r.qualifier.as_deref(), false),
            None,
            LocalBinding::None,
        );
        let (Outcome::Hit(nodes, _), Some(&from)) = (outcome, self.index.get(&r.from)) else {
            return;
        };
        for n in nodes {
            self.link(from, n, EdgeKind::References, Status::May);
            let to = self.graph[n].symref.clone();
            self.status_edges.push(StatusEdge {
                from: r.from.clone(),
                to: Some(to),
                kind: EdgeKind::References,
                status: Status::May,
                name: Some(r.name.clone()),
                reason: None,
                qualifier: None,
                line: None,
                text: None,
            });
        }
    }

    fn link_link(&mut self, r: &RefSite) {
        let Some((path, frag)) = link_target(r.from.path(), &r.name) else {
            return;
        };
        let target = match &frag {
            Some(f) => Symref::anchor(&path, f),
            None => Symref::file(&path),
        };
        let from = self.index.get(&r.from).copied();
        if let (Some(a), Some(b)) = (from, self.index.get(&target).copied()) {
            self.link(a, b, EdgeKind::Links, Status::Must);
            self.status_edges.push(StatusEdge {
                from: r.from.clone(),
                to: Some(target),
                kind: EdgeKind::Links,
                status: Status::Must,
                name: Some(r.name.clone()),
                reason: None,
                qualifier: None,
                line: None,
                text: None,
            });
        } else {
            tracing::debug!(from = %r.from, dest = %r.name, "broken link");
            self.status_edges.push(StatusEdge {
                from: r.from.clone(),
                to: None,
                kind: EdgeKind::Links,
                status: Status::Unknown,
                name: Some(r.name.clone()),
                reason: Some(GapReason::BrokenLink),
                qualifier: None,
                line: None,
                text: None,
            });
        }
    }

    /// Every record, file nodes included, in insertion order.
    pub fn records(&self) -> impl Iterator<Item = &SymbolRecord> {
        self.graph.node_weights()
    }

    /// Looks up a record by exact symref.
    pub fn get(&self, symref: &Symref) -> Option<&SymbolRecord> {
        self.index.get(symref).map(|&n| &self.graph[n])
    }

    /// Number of nodes (files included).
    pub fn node_count(&self) -> usize {
        self.graph.node_count()
    }

    /// All flattened imports (resolved or not).
    pub fn imports(&self) -> &[ImportEdge] {
        &self.imports
    }

    /// All resolved, ambiguous and unresolved calls.
    pub fn call_edges(&self) -> &[CallEdge] {
        &self.calls
    }

    /// Symbols visible outside their crate: `pub` items whose containers are
    /// all `pub` too, plus everything a `pub use` re-export makes public (G10),
    /// excluding files, impl blocks and headings; sorted.
    pub fn public_api(&self) -> Vec<&SymbolRecord> {
        let mut out: Vec<&SymbolRecord> = self
            .graph
            .node_indices()
            .filter(|&n| {
                let r = &self.graph[n];
                !matches!(r.kind, SymbolKind::Impl | SymbolKind::Heading)
                    && !matches!(r.symref.target(), Target::File)
                    && self.exported(n)
            })
            .map(|n| &self.graph[n])
            .collect();
        out.sort_by(|a, b| a.symref.cmp(&b.symref));
        out
    }

    /// True when `n` is public through its own container chain or because it, or a
    /// container below a public chain, is the target of a `pub use` (G10).
    fn exported(&self, mut n: NodeIndex) -> bool {
        loop {
            if self.reexported.contains(&n) {
                return true;
            }
            if self.graph[n].visibility != Visibility::Public {
                return false;
            }
            match self.parent_of(n) {
                Some(p) => n = p,
                None => return true,
            }
        }
    }

    fn parent_of(&self, n: NodeIndex) -> Option<NodeIndex> {
        self.graph
            .edges_directed(n, Direction::Incoming)
            .find(|e| e.weight().kind == EdgeKind::Contains)
            .map(|e| e.source())
    }

    /// Everything that may be affected by a change to `symref`: callers and
    /// referrers (transitively, May candidates and functions passed as values
    /// included) and containing symbols.
    /// Sorted, excluding `symref` itself; empty when the symref is unknown.
    pub fn affects(&self, symref: &Symref) -> Vec<Symref> {
        let Some(&start) = self.index.get(symref) else {
            return Vec::new();
        };
        let mut seen: HashSet<NodeIndex> = HashSet::from([start]);
        let mut queue = VecDeque::from([start]);
        while let Some(n) = queue.pop_front() {
            for e in self.graph.edges_directed(n, Direction::Incoming) {
                if matches!(
                    e.weight().kind,
                    EdgeKind::Calls | EdgeKind::References | EdgeKind::Contains
                ) && seen.insert(e.source())
                {
                    queue.push_back(e.source());
                }
            }
        }
        seen.remove(&start);
        let sorted: BTreeSet<Symref> = seen.iter().map(|&n| self.graph[n].symref.clone()).collect();
        sorted.into_iter().collect()
    }

    /// Everything reachable from `symref` along edges of `kind`
    /// (transitively); sorted, excluding `symref` itself.
    pub fn reach(&self, symref: &Symref, kind: EdgeKind) -> Vec<Symref> {
        let Some(&start) = self.index.get(symref) else {
            return Vec::new();
        };
        let mut seen: HashSet<NodeIndex> = HashSet::from([start]);
        let mut queue = VecDeque::from([start]);
        while let Some(n) = queue.pop_front() {
            for e in self.graph.edges_directed(n, Direction::Outgoing) {
                if e.weight().kind == kind && seen.insert(e.target()) {
                    queue.push_back(e.target());
                }
            }
        }
        seen.remove(&start);
        let sorted: BTreeSet<Symref> = seen.iter().map(|&n| self.graph[n].symref.clone()).collect();
        sorted.into_iter().collect()
    }

    /// [`SymbolGraph::affects`] with the status of the best path to each symbol
    /// (the weakest edge of the strongest path); containment counts as Must.
    pub fn affects_with_status(&self, symref: &Symref) -> BTreeMap<Symref, Status> {
        let Some(&start) = self.index.get(symref) else {
            return BTreeMap::new();
        };
        let best = self.propagate(
            start,
            Direction::Incoming,
            &[EdgeKind::Calls, EdgeKind::References, EdgeKind::Contains],
        );
        best.into_iter()
            .filter(|(n, _)| *n != start)
            .map(|(n, st)| (self.graph[n].symref.clone(), st))
            .collect()
    }

    /// Forward reach from `symref` over edges of `kinds`, with statuses and the
    /// symbols whose unresolved calls poison it: an `Unknown` call edge means the
    /// true reach may be larger, so [`ReachSet::is_complete`] is false (G1-G3).
    pub fn reach_with_status(&self, symref: &Symref, kinds: &[EdgeKind]) -> ReachSet {
        let Some(&start) = self.index.get(symref) else {
            return ReachSet::default();
        };
        let best = self.propagate(start, Direction::Outgoing, kinds);
        let poisoned_by = best
            .keys()
            .filter(|n| self.poisoned.contains(n))
            .map(|&n| self.graph[n].symref.clone())
            .collect();
        let reached = best
            .into_iter()
            .filter(|(n, _)| *n != start)
            .map(|(n, st)| (self.graph[n].symref.clone(), st))
            .collect();
        ReachSet {
            reached,
            poisoned_by,
        }
    }

    /// Best-path statuses from `start` (Must at the start) along `kinds`.
    fn propagate(
        &self,
        start: NodeIndex,
        dir: Direction,
        kinds: &[EdgeKind],
    ) -> HashMap<NodeIndex, Status> {
        let mut best: HashMap<NodeIndex, Status> = HashMap::from([(start, Status::Must)]);
        let mut queue = VecDeque::from([start]);
        while let Some(n) = queue.pop_front() {
            let here = best[&n];
            for e in self.graph.edges_directed(n, dir) {
                if !kinds.contains(&e.weight().kind) {
                    continue;
                }
                let next = if dir == Direction::Outgoing {
                    e.target()
                } else {
                    e.source()
                };
                let st = here.meet(e.weight().status);
                if best.get(&next).is_none_or(|b| st > *b) {
                    best.insert(next, st);
                    queue.push_back(next);
                }
            }
        }
        best
    }

    /// Every call, reference and link edge with its status, unresolved ones
    /// included as `Unknown` edges with no target (the old call shape stays in
    /// [`SymbolGraph::call_edges`]).
    pub fn edges_with_status(&self) -> &[StatusEdge] {
        &self.status_edges
    }

    /// Facts about a walked file: language, fidelity and parse status.
    pub fn file_info(&self, path: &str) -> Option<&FileInfo> {
        self.files.get(path)
    }

    /// Every walked file with its facts, sorted by path.
    pub fn files(&self) -> impl Iterator<Item = (&str, &FileInfo)> {
        self.files.iter().map(|(p, i)| (p.as_str(), i))
    }

    /// Extra facts of a symbol: unknown facets and the markdown subtree digest (G9).
    pub fn extras(&self, symref: &Symref) -> Option<&UnitExtras> {
        self.extras.get(symref)
    }

    /// blake3 over the sorted symrefs (with kind, visibility and sig digest)
    /// and sorted edges; the cache key component for repo-level rules.
    pub fn graph_digest(&self) -> FacetDigest {
        let mut nodes: Vec<String> = self
            .graph
            .node_weights()
            .map(|r| {
                format!(
                    "{}\0{:?}\0{:?}\0{}",
                    r.symref, r.kind, r.visibility, r.digests.sig
                )
            })
            .collect();
        nodes.sort();
        let mut edges: Vec<String> = self
            .graph
            .edge_references()
            .map(|e| {
                format!(
                    "{}\0{}\0{:?}\0{:?}",
                    self.graph[e.source()].symref,
                    self.graph[e.target()].symref,
                    e.weight().kind,
                    e.weight().status
                )
            })
            .chain(
                self.status_edges
                    .iter()
                    .filter(|e| e.to.is_none())
                    .map(|e| {
                        format!(
                            "{}\0?{}\0{:?}\0{:?}",
                            e.from,
                            e.name.as_deref().unwrap_or(""),
                            e.kind,
                            e.status
                        )
                    }),
            )
            .collect();
        edges.sort();
        let mut h = blake3::Hasher::new();
        for n in &nodes {
            h.update(b"N");
            h.update(n.as_bytes());
            h.update(b"\n");
        }
        for e in &edges {
            h.update(b"E");
            h.update(e.as_bytes());
            h.update(b"\n");
        }
        FacetDigest::from_bytes(*h.finalize().as_bytes())
    }

    /// Resolves a full symref or a unique name suffix (`Name`, `Qual.Name`,
    /// `path::Name`) to one record.
    ///
    /// # Errors
    ///
    /// [`ResolveError::NotFound`] or [`ResolveError::Ambiguous`] with all
    /// candidates.
    pub fn resolve(&self, input: &str) -> Result<&SymbolRecord, ResolveError> {
        let outside = strip_brackets(input);
        let bare = !outside.contains("::") && !outside.contains('#');
        let (path, want): (Option<String>, Vec<String>) = if bare {
            (None, split_qual(input))
        } else {
            let parsed =
                Symref::parse(input).map_err(|_| ResolveError::NotFound(input.to_owned()))?;
            if let Some(r) = self.get(&parsed) {
                return Ok(r);
            }
            match parsed.target() {
                Target::Symbol(segs) => (Some(parsed.path().to_owned()), segs.clone()),
                _ => return Err(ResolveError::NotFound(input.to_owned())),
            }
        };
        if want.iter().any(String::is_empty) {
            return Err(ResolveError::NotFound(input.to_owned()));
        }
        let mut found: Vec<&SymbolRecord> = self
            .graph
            .node_weights()
            .filter(|r| match r.symref.target() {
                Target::Symbol(have) => {
                    path.as_deref().is_none_or(|p| p == r.symref.path())
                        && suffix_match(have, &want, r.kind == SymbolKind::Impl)
                }
                _ => false,
            })
            .collect();
        found.sort_by(|a, b| a.symref.cmp(&b.symref));
        match found.len() {
            0 => Err(ResolveError::NotFound(input.to_owned())),
            1 => Ok(found[0]),
            _ => Err(ResolveError::Ambiguous(
                found.iter().map(|r| r.symref.clone()).collect(),
            )),
        }
    }
}

/// True when `want` matches the tail of `have`; an unbracketed wanted segment
/// also matches a bracketed one (`Foo` matches `Foo[Display]`), except that
/// impl blocks only match exactly.
fn suffix_match(have: &[String], want: &[String], exact_only: bool) -> bool {
    if want.len() > have.len() {
        return false;
    }
    let tail = &have[have.len() - want.len()..];
    tail.iter()
        .zip(want)
        .all(|(h, w)| h == w || (!exact_only && !w.contains('[') && base_segment(h) == w))
}

/// Removes `[...]` groups (nesting-aware).
fn strip_brackets(s: &str) -> String {
    let mut depth = 0u32;
    let mut out = String::new();
    for ch in s.chars() {
        match ch {
            '[' => depth += 1,
            ']' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(ch),
            _ => {}
        }
    }
    out
}
