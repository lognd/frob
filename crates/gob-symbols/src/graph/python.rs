//! Python call, import and reference resolution for the symbol graph.
//!
//! Python has no static types, so a call is Must only when the syntax and the imports
//! prove one target: a name defined in an enclosing scope or the module, a name bound
//! by a `from ... import`, a module attribute reached through `import`, or a method
//! through `self` that the enclosing class defines. A module found only by a path
//! suffix (the importing repository root differs from the package root), several
//! definitions of a name, an inherited method and every call on a value of unknown
//! type (`obj.m()` names every repository method `m`) are May. A callee that is a
//! parameter or assigned name is a local value, an expression callee is dynamic, and a
//! name nothing in the repository defines is external: both are Unknown edges, never
//! clean.

// frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF

use std::collections::{BTreeSet, HashMap};

use petgraph::graph::NodeIndex;

use super::{GapReason, Outcome, SymbolGraph, base_segment};
use crate::model::{
    CallSite, FileSymbols, LocalBinding, Receiver, RefSite, SymbolKind, UseBinding,
};
use crate::symref::Symref;
use gob_ir::Status;

/// Deepest chain of re-exports (`from .x import y` in an `__init__`) followed.
const MAX_REEXPORT: usize = 4;

/// True when `path` is a Python source file.
pub(super) fn is_python(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("py") || e.eq_ignore_ascii_case("pyi"))
}

/// Lookup tables over the repository's Python files.
#[derive(Debug, Default)]
pub(super) struct PyIndex {
    /// Every dotted suffix of a module name to the files it may name, with whether it is the full name.
    modules: HashMap<String, Vec<(String, bool)>>,
    /// (container node, simple name) to the units defined directly in it (a file node holds the module level).
    kids: HashMap<(NodeIndex, String), Vec<NodeIndex>>,
    /// Simple method name to every Python method so named.
    methods: HashMap<String, Vec<NodeIndex>>,
    /// Importing file to its use bindings.
    uses: HashMap<String, Vec<UseBinding>>,
    /// Python file path to its file node.
    file_nodes: HashMap<String, NodeIndex>,
}

/// The dotted module name of `path` (`src/` and `lib/` roots stripped, `__init__` dropped), empty for none.
fn module_name(path: &str) -> String {
    let stem = path.rsplit_once('.').map_or(path, |(s, _)| s);
    let mut parts: Vec<&str> = stem.split('/').collect();
    if parts.last() == Some(&"__init__") {
        parts.pop();
    }
    if parts.first().is_some_and(|p| matches!(*p, "src" | "lib")) && parts.len() > 1 {
        parts.remove(0);
    }
    parts.join(".")
}

/// Splits a use target into its leading-dot count and its name segments (`..a.b` is `(2, [a, b])`).
fn split_target(target: &str) -> (usize, Vec<String>) {
    let dots = target.chars().take_while(|c| *c == '.').count();
    let segs = target[dots..]
        .split('.')
        .filter(|s| !s.is_empty())
        .map(str::to_owned)
        .collect();
    (dots, segs)
}

impl PyIndex {
    /// Indexes the Python files in `files` against the node table of `g`.
    pub(super) fn build(g: &SymbolGraph, files: &[FileSymbols]) -> Self {
        let mut ix = Self::default();
        for f in files.iter().filter(|f| is_python(&f.path)) {
            let Some(&file_node) = g.index.get(&Symref::file(&f.path)) else {
                continue;
            };
            ix.file_nodes.insert(f.path.clone(), file_node);
            let full = module_name(&f.path);
            if !full.is_empty() {
                let segs: Vec<&str> = full.split('.').collect();
                for i in 0..segs.len() {
                    let key = segs[i..].join(".");
                    let exact = i == 0;
                    ix.modules
                        .entry(key)
                        .or_default()
                        .push((f.path.clone(), exact));
                }
            }
            ix.uses.insert(f.path.clone(), f.uses.clone());
            for s in &f.symbols {
                let Some(&node) = g.index.get(&s.symref) else {
                    continue;
                };
                let parent = s
                    .parent
                    .as_ref()
                    .and_then(|p| g.index.get(p).copied())
                    .unwrap_or(file_node);
                if let Some(name) = s.symref.name() {
                    ix.kids
                        .entry((parent, base_segment(name).to_owned()))
                        .or_default()
                        .push(node);
                    if s.kind == SymbolKind::Method {
                        ix.methods
                            .entry(base_segment(name).to_owned())
                            .or_default()
                            .push(node);
                    }
                }
            }
        }
        tracing::debug!(
            files = ix.file_nodes.len(),
            modules = ix.modules.len(),
            "python index built"
        );
        ix
    }

    fn kids_of(&self, parent: NodeIndex, name: &str) -> &[NodeIndex] {
        self.kids
            .get(&(parent, name.to_owned()))
            .map_or(&[], Vec::as_slice)
    }
}

/// How sure a set of targets is, and what they are.
struct Found {
    nodes: Vec<NodeIndex>,
    status: Status,
}

impl SymbolGraph {
    /// The files a module path may name: absolute dotted segments, or `dots` leading dots from `from`.
    fn py_module_files(
        py: &PyIndex,
        from: &str,
        dots: usize,
        segs: &[String],
    ) -> Vec<(String, bool)> {
        if dots == 0 {
            if segs.is_empty() {
                return Vec::new();
            }
            let found = py.modules.get(&segs.join(".")).cloned().unwrap_or_default();
            let exact: Vec<_> = found.iter().filter(|(_, e)| *e).cloned().collect();
            return if exact.is_empty() { found } else { exact };
        }
        let mut dir: Vec<&str> = from.split('/').collect();
        dir.pop();
        for _ in 1..dots {
            if dir.pop().is_none() {
                return Vec::new();
            }
        }
        let base = dir.join("/");
        let join = |tail: String| {
            if base.is_empty() {
                tail
            } else {
                format!("{base}/{tail}")
            }
        };
        let rel = segs.join("/");
        let candidates = if rel.is_empty() {
            vec![join("__init__.py".to_owned())]
        } else {
            vec![
                join(format!("{rel}.py")),
                join(format!("{rel}/__init__.py")),
            ]
        };
        candidates
            .into_iter()
            .filter(|p| py.file_nodes.contains_key(p))
            .map(|p| (p, true))
            .collect()
    }

    /// Resolves the name path `segs` (module segments then symbol names) relative to `dots` from `from`.
    ///
    /// `None` when no repository module is a prefix of it (an external name) or the module
    /// lacks the name (a re-export is followed). Class results are not mapped to `__init__` here.
    fn py_walk(
        &self,
        py: &PyIndex,
        (from, dots): (&str, usize),
        segs: &[String],
        depth: usize,
    ) -> Option<Found> {
        for k in (0..=segs.len()).rev() {
            let files = Self::py_module_files(py, from, dots, &segs[..k]);
            if files.is_empty() {
                continue;
            }
            let mut status = if files.iter().all(|(_, e)| *e) && files.len() == 1 {
                Status::Must
            } else {
                Status::May
            };
            let rest = &segs[k..];
            let mut nodes: Vec<NodeIndex> = Vec::new();
            for (path, _) in &files {
                let file_node = py.file_nodes[path];
                let mut cur = vec![file_node];
                for seg in rest {
                    cur = cur
                        .iter()
                        .flat_map(|&n| py.kids_of(n, seg).iter().copied())
                        .collect();
                    if cur.is_empty() {
                        break;
                    }
                }
                if cur.is_empty() && !rest.is_empty() && depth < MAX_REEXPORT {
                    cur = self.py_reexport(py, path, rest, depth);
                }
                nodes.extend(cur);
            }
            nodes.sort();
            nodes.dedup();
            if nodes.is_empty() {
                tracing::trace!(from, ?segs, "python module found, name missing");
                return None;
            }
            if nodes.len() > 1 {
                status = Status::May;
            }
            return Some(Found { nodes, status });
        }
        None
    }

    /// The units `rest` names in `path` through a re-export (`from .impl import name` in an `__init__`).
    fn py_reexport(
        &self,
        py: &PyIndex,
        path: &str,
        rest: &[String],
        depth: usize,
    ) -> Vec<NodeIndex> {
        let Some(head) = rest.first() else {
            return Vec::new();
        };
        let mut out = Vec::new();
        for u in py
            .uses
            .get(path)
            .into_iter()
            .flatten()
            .filter(|u| &u.local == head)
        {
            let (dots, mut segs) = split_target(&u.target);
            segs.extend(rest[1..].iter().cloned());
            if let Some(f) = self.py_walk(py, (path, dots), &segs, depth + 1) {
                out.extend(f.nodes);
            }
        }
        out
    }

    /// The innermost enclosing class of `n` (itself excluded), through nested functions.
    fn py_class_of(&self, n: NodeIndex) -> Option<NodeIndex> {
        let mut cur = self.parent_of(n);
        while let Some(p) = cur {
            if self.graph[p].kind == SymbolKind::Class {
                return Some(p);
            }
            cur = self.parent_of(p);
        }
        None
    }

    /// The units named `name` visible lexically from `caller`: nested defs, then module level (class scopes are skipped).
    fn py_lexical(&self, py: &PyIndex, caller: NodeIndex, name: &str) -> Vec<NodeIndex> {
        let mut cur = Some(caller);
        while let Some(n) = cur {
            if self.graph[n].kind != SymbolKind::Class {
                let found = py.kids_of(n, name);
                if !found.is_empty() {
                    return found.to_vec();
                }
            }
            cur = self.parent_of(n);
        }
        Vec::new()
    }

    /// The use bindings of `file` named `local` that are in scope at `caller`.
    fn py_uses<'a>(py: &'a PyIndex, caller: &Symref, local: &str) -> Vec<&'a UseBinding> {
        py.uses
            .get(caller.path())
            .into_iter()
            .flatten()
            .filter(|u| u.local == local)
            .filter(|u| {
                u.container.as_ref().is_none_or(|c| {
                    c.path() == caller.path() && caller.segments().starts_with(c.segments())
                })
            })
            .collect()
    }

    /// A class result becomes its `__init__` when it has one.
    fn py_construct(&self, py: &PyIndex, nodes: Vec<NodeIndex>) -> Vec<NodeIndex> {
        nodes
            .into_iter()
            .map(|n| {
                if self.graph[n].kind == SymbolKind::Class
                    && let Some(&init) = py.kids_of(n, "__init__").first()
                {
                    init
                } else {
                    n
                }
            })
            .collect()
    }

    /// The units a module-level or imported name `name` stands for at `caller`, or `None` when nothing in the repository does.
    fn py_name(&self, py: &PyIndex, caller: &Symref, node: NodeIndex, name: &str) -> Option<Found> {
        let lexical = self.py_lexical(py, node, name);
        if !lexical.is_empty() {
            let status = if lexical.len() == 1 {
                Status::Must
            } else {
                Status::May
            };
            return Some(Found {
                nodes: lexical,
                status,
            });
        }
        let mut nodes = Vec::new();
        let mut status = Status::Must;
        let from = caller.path();
        for u in Self::py_uses(py, caller, name) {
            let (dots, segs) = split_target(&u.target);
            if let Some(f) = self.py_walk(py, (from, dots), &segs, 0) {
                status = status.meet(f.status);
                nodes.extend(f.nodes);
            }
        }
        if nodes.is_empty() {
            let mut star = Vec::new();
            for u in Self::py_uses(py, caller, "*") {
                let (dots, mut segs) = split_target(&u.target);
                segs.pop();
                segs.push(name.to_owned());
                if let Some(f) = self.py_walk(py, (from, dots), &segs, 0) {
                    star.extend(f.nodes);
                }
            }
            if star.is_empty() {
                return None;
            }
            nodes = star;
            status = Status::May;
        }
        nodes.sort();
        nodes.dedup();
        if nodes.len() > 1 {
            status = Status::May;
        }
        Some(Found { nodes, status })
    }

    /// Every Python method named `name` as May candidates, or an external gap when none exists.
    fn py_unknown_receiver(py: &PyIndex, name: &str) -> Outcome {
        match py.methods.get(name) {
            Some(ms) if !ms.is_empty() => Outcome::Hit(ms.clone(), Status::May),
            _ => Outcome::Gap(GapReason::Unbound),
        }
    }

    /// Resolves the call `call` of a Python caller.
    pub(super) fn resolve_python(&self, py: &PyIndex, call: &CallSite) -> Outcome {
        let Some(&node) = self.index.get(&call.caller) else {
            return Outcome::Gap(GapReason::Unbound);
        };
        if call.callee.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        if call.method {
            if call.receiver == Some(Receiver::SelfValue)
                && let Some(class) = self.py_class_of(node)
            {
                let own = py.kids_of(class, &call.callee);
                if !own.is_empty() {
                    return Outcome::Hit(own.to_vec(), Status::Must);
                }
            }
            return Self::py_unknown_receiver(py, &call.callee);
        }
        let Some(head) = call.qual_path.first() else {
            if call.local != LocalBinding::None {
                return Outcome::Gap(GapReason::LocalValue);
            }
            return match self.py_name(py, &call.caller, node, &call.callee) {
                Some(f) => Outcome::Hit(self.py_construct(py, f.nodes), f.status),
                None => Outcome::Gap(GapReason::Unbound),
            };
        };
        let rest = &call.qual_path[1..];
        let lexical = self.py_lexical(py, node, head);
        if !lexical.is_empty() {
            return self.py_member_chain(py, lexical, rest, &call.callee);
        }
        let from = call.caller.path();
        let mut nodes = Vec::new();
        let mut status = Status::Must;
        for u in Self::py_uses(py, &call.caller, head) {
            let (dots, mut segs) = split_target(&u.target);
            segs.extend(rest.iter().cloned());
            segs.push(call.callee.clone());
            if let Some(f) = self.py_walk(py, (from, dots), &segs, 0) {
                status = status.meet(f.status);
                nodes.extend(f.nodes);
            } else if let Some(f) = self.py_walk(py, (from, dots), &segs[..segs.len() - 1], 0) {
                // The qualifier is a repository class that does not define the callee: inherited.
                let all_classes = f
                    .nodes
                    .iter()
                    .all(|&n| self.graph[n].kind == SymbolKind::Class);
                if all_classes {
                    return Self::py_unknown_receiver(py, &call.callee);
                }
            }
        }
        if nodes.is_empty() {
            return Outcome::Gap(GapReason::Unbound);
        }
        nodes.sort();
        nodes.dedup();
        if nodes.len() > 1 {
            status = Status::May;
        }
        Outcome::Hit(self.py_construct(py, nodes), status)
    }

    /// Follows `rest` then `callee` through the members of `start` (classes and functions defined in this repository).
    fn py_member_chain(
        &self,
        py: &PyIndex,
        start: Vec<NodeIndex>,
        rest: &[String],
        callee: &str,
    ) -> Outcome {
        let mut cur = start;
        for seg in rest.iter().map(String::as_str).chain([callee]) {
            let next: Vec<NodeIndex> = cur
                .iter()
                .flat_map(|&n| py.kids_of(n, seg).iter().copied())
                .collect();
            if next.is_empty() {
                return Self::py_unknown_receiver(py, callee);
            }
            cur = next;
        }
        let status = if cur.len() == 1 {
            Status::Must
        } else {
            Status::May
        };
        Outcome::Hit(self.py_construct(py, cur), status)
    }

    /// Resolves a function used as a value (`map(f, xs)`); only a Hit matters.
    pub(super) fn resolve_python_value(&self, py: &PyIndex, r: &RefSite) -> Option<Vec<NodeIndex>> {
        let node = *self.index.get(&r.from)?;
        self.py_name(py, &r.from, node, &r.name).map(|f| f.nodes)
    }

    /// Links each Python file to the modules and symbols its imports name.
    pub(super) fn link_python_imports(&mut self, py: &PyIndex, files: &[FileSymbols]) {
        let mut links: BTreeSet<(NodeIndex, NodeIndex, bool)> = BTreeSet::new();
        for f in files.iter().filter(|f| is_python(&f.path)) {
            let Some(&from) = py.file_nodes.get(&f.path) else {
                continue;
            };
            for u in &f.uses {
                let (dots, segs) = split_target(&u.target);
                if u.local == "*" {
                    let mut segs = segs;
                    segs.pop();
                    for (p, e) in Self::py_module_files(py, &f.path, dots, &segs) {
                        links.insert((from, py.file_nodes[&p], e));
                    }
                    continue;
                }
                for (p, e) in Self::py_module_files(py, &f.path, dots, &segs) {
                    links.insert((from, py.file_nodes[&p], e));
                }
                if let Some(found) = self.py_walk(py, (&f.path, dots), &segs, 0) {
                    let must = found.status == Status::Must;
                    for n in found.nodes {
                        links.insert((from, n, must));
                    }
                }
            }
        }
        for (a, b, must) in links {
            if a != b {
                let status = if must { Status::Must } else { Status::May };
                self.link(a, b, super::EdgeKind::Imports, status);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/gob-symbols/src/graph/python.rs::module_name
    fn module_names_strip_roots_and_init() {
        assert_eq!(module_name("src/pkg/a.py"), "pkg.a");
        assert_eq!(module_name("pkg/__init__.py"), "pkg");
        assert_eq!(module_name("__init__.py"), "");
        assert_eq!(module_name("tests/test_a.py"), "tests.test_a");
    }

    #[test]
    // frob:tests crates/gob-symbols/src/graph/python.rs::split_target
    fn targets_split_into_dots_and_segments() {
        assert_eq!(split_target("..a.b"), (2, vec!["a".into(), "b".into()]));
        assert_eq!(split_target(".x"), (1, vec!["x".into()]));
        assert_eq!(split_target("os"), (0, vec!["os".into()]));
    }
}
