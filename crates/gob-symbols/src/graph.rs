//! The repository-level symbol graph (petgraph) and its queries.

use std::collections::{BTreeSet, HashMap, HashSet, VecDeque};

use gob_text::{TextRange, TextSize};
use petgraph::Direction;
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;

use crate::model::{
    CallSite, Digests, FacetDigest, FileSymbols, ImportEdge, SymbolKind, SymbolRecord, Visibility,
};
use crate::paths::crate_and_module;
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
}

/// Edge payload.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Edge {
    kind: EdgeKind,
    /// False for call edges that are one of several candidates.
    resolved: bool,
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
    /// Several candidates; all are kept (`resolved: false` edges).
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

/// All symbols of a repository with Contains, Imports and Calls edges.
#[derive(Debug, Default)]
pub struct SymbolGraph {
    graph: DiGraph<SymbolRecord, Edge>,
    index: HashMap<Symref, NodeIndex>,
    imports: Vec<ImportEdge>,
    calls: Vec<CallEdge>,
}

fn is_rust(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("rs"))
}

fn base_segment(s: &str) -> &str {
    s.split_once('[').map_or(s, |(b, _)| b)
}

impl SymbolGraph {
    /// Builds the graph from per-file results (any order).
    pub fn from_files(mut files: Vec<FileSymbols>) -> Self {
        files.sort_by(|a, b| a.path.cmp(&b.path));
        let mut g = Self::default();
        for f in &files {
            g.add_file(f);
        }
        g.link_imports(&files);
        g.link_calls(&files);
        tracing::debug!(
            nodes = g.graph.node_count(),
            edges = g.graph.edge_count(),
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
            self.graph.add_edge(
                parent,
                child,
                Edge {
                    kind: EdgeKind::Contains,
                    resolved: true,
                },
            );
        }
        self.imports.extend(f.imports.iter().cloned());
    }

    fn link_imports(&mut self, files: &[FileSymbols]) {
        // (crate dir, crate-relative item path) -> nodes.
        let mut by_item: HashMap<(String, String), Vec<NodeIndex>> = HashMap::new();
        for f in files.iter().filter(|f| is_rust(&f.path)) {
            let (krate, module) = crate_and_module(&f.path);
            by_item
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
                by_item
                    .entry((krate.clone(), segs.join("::")))
                    .or_default()
                    .push(self.index[&s.symref]);
            }
        }
        let edges = self.imports.clone();
        for imp in edges.iter().filter(|i| i.is_internal()) {
            let (krate, _) = crate_and_module(&imp.from_file);
            let rel = imp.target.strip_prefix("crate").unwrap_or("");
            let rel = rel.strip_prefix("::").unwrap_or(rel);
            let rel = rel
                .strip_suffix("::*")
                .unwrap_or(if rel == "*" { "" } else { rel });
            let Some(targets) = by_item.get(&(krate, rel.to_owned())) else {
                tracing::trace!(target = %imp.target, "internal import unresolved");
                continue;
            };
            let from = self.index[&Symref::file(&imp.from_file)];
            for &t in targets {
                if t != from {
                    self.graph.update_edge(
                        from,
                        t,
                        Edge {
                            kind: EdgeKind::Imports,
                            resolved: true,
                        },
                    );
                }
            }
        }
    }

    fn link_calls(&mut self, files: &[FileSymbols]) {
        let mut by_name: HashMap<(String, String), Vec<NodeIndex>> = HashMap::new();
        for f in files.iter().filter(|f| is_rust(&f.path)) {
            let (krate, _) = crate_and_module(&f.path);
            for s in &f.symbols {
                if matches!(s.kind, SymbolKind::Function | SymbolKind::Method)
                    && let Some(n) = s.symref.name()
                {
                    by_name
                        .entry((krate.clone(), n.to_owned()))
                        .or_default()
                        .push(self.index[&s.symref]);
                }
            }
        }
        for f in files {
            for call in &f.calls {
                let edge = self.resolve_call(call, &by_name);
                self.add_call(edge);
            }
        }
    }

    fn resolve_call(
        &self,
        call: &CallSite,
        by_name: &HashMap<(String, String), Vec<NodeIndex>>,
    ) -> CallEdge {
        let (krate, _) = crate_and_module(call.caller.path());
        let unresolved = || CallEdge::Unresolved {
            caller: call.caller.clone(),
            name: call.callee.clone(),
        };
        let Some(all) = by_name.get(&(krate, call.callee.clone())) else {
            return unresolved();
        };
        let qualifier = match call.qualifier.as_deref() {
            Some("Self") => {
                let segs = call.caller.segments();
                segs.len()
                    .checked_sub(2)
                    .map(|i| base_segment(&segs[i]).to_owned())
            }
            Some(q) => Some(q.to_owned()),
            None => None,
        };
        let mut cands: Vec<&SymbolRecord> = all.iter().map(|&n| &self.graph[n]).collect();
        cands.retain(|r| {
            if call.method {
                r.kind == SymbolKind::Method
            } else if call.qualifier.is_none() {
                r.kind == SymbolKind::Function
            } else {
                true
            }
        });
        if let Some(q) = &qualifier {
            cands.retain(|r| {
                let segs = r.symref.segments();
                let parent_seg = segs.len().checked_sub(2).map(|i| base_segment(&segs[i]));
                let (_, module) = crate_and_module(r.symref.path());
                parent_seg == Some(q.as_str()) || module.last() == Some(q)
            });
        }
        let mut found: Vec<Symref> = cands.iter().map(|r| r.symref.clone()).collect();
        found.sort();
        found.dedup();
        match found.len() {
            0 => unresolved(),
            1 => CallEdge::Resolved {
                caller: call.caller.clone(),
                callee: found.remove(0),
            },
            _ => CallEdge::Ambiguous {
                caller: call.caller.clone(),
                candidates: found,
            },
        }
    }

    fn add_call(&mut self, edge: CallEdge) {
        let mut link = |caller: &Symref, callee: &Symref, resolved: bool| {
            if let (Some(&a), Some(&b)) = (self.index.get(caller), self.index.get(callee)) {
                self.graph.update_edge(
                    a,
                    b,
                    Edge {
                        kind: EdgeKind::Calls,
                        resolved,
                    },
                );
            }
        };
        match &edge {
            CallEdge::Resolved { caller, callee } => link(caller, callee, true),
            CallEdge::Ambiguous { caller, candidates } => {
                for c in candidates {
                    link(caller, c, false);
                }
            }
            CallEdge::Unresolved { .. } => {}
        }
        self.calls.push(edge);
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
    /// all `pub` too, excluding files, impl blocks and headings; sorted.
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

    fn exported(&self, mut n: NodeIndex) -> bool {
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

    fn parent_of(&self, n: NodeIndex) -> Option<NodeIndex> {
        self.graph
            .edges_directed(n, Direction::Incoming)
            .find(|e| e.weight().kind == EdgeKind::Contains)
            .map(|e| e.source())
    }

    /// Everything that may be affected by a change to `symref`: callers
    /// (transitively, ambiguous candidates included) and containing symbols.
    /// Sorted, excluding `symref` itself; empty when the symref is unknown.
    pub fn affects(&self, symref: &Symref) -> Vec<Symref> {
        let Some(&start) = self.index.get(symref) else {
            return Vec::new();
        };
        let mut seen: HashSet<NodeIndex> = HashSet::from([start]);
        let mut queue = VecDeque::from([start]);
        while let Some(n) = queue.pop_front() {
            for e in self.graph.edges_directed(n, Direction::Incoming) {
                if matches!(e.weight().kind, EdgeKind::Calls | EdgeKind::Contains)
                    && seen.insert(e.source())
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
                    "{}\0{}\0{:?}\0{}",
                    self.graph[e.source()].symref,
                    self.graph[e.target()].symref,
                    e.weight().kind,
                    e.weight().resolved
                )
            })
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
