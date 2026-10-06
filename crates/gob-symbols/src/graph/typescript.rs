//! TypeScript and JavaScript import, call and reference resolution for the symbol graph.
//!
//! The module graph follows the Python one (`graph/python.rs`): an import is Must when the specifier names
//! exactly one repository file (or a symbol that file declares or re-exports), May when the import runs only
//! sometimes (a literal dynamic `import("m")`, a `require` under a condition or inside a function) or several
//! files or symbols answer, and Unknown when nothing can be claimed: a computed specifier, a relative
//! specifier that names no file, and every bare specifier the project model cannot place. With the project
//! model (`CrateDeps::js_resolve`, ~C3DEAQX) a bare specifier resolves in this order: a `#` import of the
//! owning package, a tsconfig `paths` alias, tsconfig `baseUrl`, a workspace package (its `exports`, `types`,
//! `module` or `main`), then a declared, installed or builtin dependency, which is Unknown with
//! [`GapReason::External`] (no repository target, so nothing is claimed). An Unknown import is kept as a
//! status edge with no target, never dropped.
//!
//! Relative specifiers resolve in the order TypeScript tries them: the `.js` family mapped to its source
//! extension, the path itself, the path plus each extension, then `index` inside the directory.
//!
//! A call is Must when the syntax and the imports prove one target (a name in an enclosing scope or the
//! module, a named import followed through re-exports, a member of a namespace import, `this.m()` of the
//! enclosing class); several definitions, an inherited method and every call on a value of unknown type
//! (`obj.m()` names every repository method `m`) are May; a local value called, an expression callee and a
//! name no repository file defines are Unknown, never clean.

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80
// frob:ticket 01M47QKTN549397AFFSC3DEAQX
// frob:ticket 01M43ARXVD5PXP6ZBVFC2F4ZMQ

use std::collections::{BTreeMap, HashMap, HashSet};

use petgraph::Direction;
use petgraph::graph::NodeIndex;
use petgraph::visit::EdgeRef;

use super::{EdgeKind, GapReason, Outcome, StatusEdge, SymbolGraph, base_segment};
use crate::crates::CrateDeps;
use crate::model::{
    CallSite, FileSymbols, ImportEdge, LocalBinding, Receiver, RefSite, SymbolKind, UseBinding,
    Visibility,
};
use crate::nodejs::JsResolution;
use crate::symref::Symref;
use crate::typescript::imports::{ImportMode, decode_edge, decode_use};
use gob_ir::Status;

/// Deepest chain of re-exports followed.
const MAX_REEXPORT: usize = 6;

/// Extensions tried after a specifier, in TypeScript's order.
const EXTENSIONS: [&str; 9] = ["ts", "tsx", "d.ts", "js", "jsx", "mts", "cts", "mjs", "cjs"];

/// True when `path` is a TypeScript or JavaScript source file.
pub(super) fn is_ts(path: &str) -> bool {
    crate::typescript::is_typescript_path(path)
}

/// What a module specifier names, seen from the importing file.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Module {
    /// A file of the repository.
    Local(String),
    /// A relative specifier that names no file.
    Missing,
    /// Not relative and not placed by the project model: an undeclared package or an unmatched alias.
    Bare,
    /// A dependency outside the repository: declared, installed under `node_modules`, or a Node builtin.
    External,
}

/// Lookup tables over the repository's TypeScript and JavaScript files.
#[derive(Debug, Default)]
pub(super) struct TsIndex {
    /// Every walked file path (a relative import of `./a.css` or `./data.json` resolves too).
    files: HashSet<String>,
    /// File path to its node, for every walked file.
    file_nodes: HashMap<String, NodeIndex>,
    /// (container node, simple name) to the units defined directly in it.
    kids: HashMap<(NodeIndex, String), Vec<NodeIndex>>,
    /// Simple method name to every TypeScript method so named.
    methods: HashMap<String, Vec<NodeIndex>>,
    /// Importing file to its use bindings.
    uses: HashMap<String, Vec<UseBinding>>,
    /// TypeScript file path to its import edges, in source order.
    imports: Vec<(String, Vec<ImportEdge>)>,
    /// (importing file, bare specifier) to what the project model says it names.
    bare: HashMap<(String, String), JsResolution>,
}

/// The directory of `from` joined with the relative `spec`, normalised; `None` above the root.
fn join_relative(from: &str, spec: &str) -> Option<String> {
    let mut parts: Vec<&str> = from.split('/').collect();
    parts.pop();
    for seg in spec.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

/// True for `.`, `..`, `./x` and `../x`.
fn is_relative(spec: &str) -> bool {
    spec == "." || spec == ".." || spec.starts_with("./") || spec.starts_with("../")
}

impl TsIndex {
    /// Indexes the TypeScript files in `files` against the node table of `g`, placing bare specifiers with `deps`.
    pub(super) fn build(
        g: &SymbolGraph,
        files: &[FileSymbols],
        mut deps: Option<&mut CrateDeps>,
    ) -> Self {
        let mut ix = Self::default();
        for f in files {
            ix.files.insert(f.path.clone());
            if let Some(&n) = g.index.get(&Symref::file(&f.path)) {
                ix.file_nodes.insert(f.path.clone(), n);
            }
        }
        for f in files.iter().filter(|f| is_ts(&f.path)) {
            let Some(&file_node) = ix.file_nodes.get(&f.path) else {
                continue;
            };
            ix.uses.insert(f.path.clone(), f.uses.clone());
            ix.imports.push((f.path.clone(), f.imports.clone()));
            if let Some(d) = deps.as_deref_mut() {
                ix.place_bare(d, f);
            }
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
                    let base = base_segment(name).to_owned();
                    ix.kids
                        .entry((parent, base.clone()))
                        .or_default()
                        .push(node);
                    if s.kind == SymbolKind::Method {
                        ix.methods.entry(base).or_default().push(node);
                    }
                }
            }
        }
        tracing::debug!(
            files = ix.imports.len(),
            bare = ix.bare.len(),
            "typescript index built"
        );
        ix
    }

    /// Asks the project model about every literal bare specifier `f` imports or re-exports.
    fn place_bare(&mut self, deps: &mut CrateDeps, f: &FileSymbols) {
        let specs = f
            .imports
            .iter()
            .map(|e| decode_edge(&e.target))
            .chain(f.uses.iter().map(|u| decode_use(&u.target)))
            .filter(|r| r.mode != ImportMode::Unknown)
            .map(|r| r.spec)
            .filter(|s| !s.is_empty() && !is_relative(s));
        for spec in specs {
            let key = (f.path.clone(), spec.to_owned());
            if self.bare.contains_key(&key) {
                continue;
            }
            let r = deps.js_resolve(&f.path, spec);
            tracing::debug!(
                from = %f.path,
                spec,
                candidates = r.candidates.len(),
                external = r.external,
                "bare specifier placed"
            );
            self.bare.insert(key, r);
        }
    }

    fn kids_of(&self, parent: NodeIndex, name: &str) -> &[NodeIndex] {
        self.kids
            .get(&(parent, name.to_owned()))
            .map_or(&[], Vec::as_slice)
    }

    /// What `spec` names from `from`; an empty specifier is the file itself.
    fn resolve(&self, from: &str, spec: &str) -> Module {
        if spec.is_empty() {
            return Module::Local(from.to_owned());
        }
        if !is_relative(spec) {
            let Some(r) = self.bare.get(&(from.to_owned(), spec.to_owned())) else {
                return Module::Bare;
            };
            if let Some(hit) = r.candidates.iter().find_map(|c| self.probe(c)) {
                return Module::Local(hit);
            }
            return if r.external {
                Module::External
            } else {
                Module::Bare
            };
        }
        let Some(base) = join_relative(from, spec) else {
            return Module::Missing;
        };
        self.probe(&base).map_or(Module::Missing, Module::Local)
    }

    /// The walked file `base` names, trying TypeScript's orders: source mapped from `.js`, the path, an extension, `index`.
    fn probe(&self, base: &str) -> Option<String> {
        let base = base.to_owned();
        let mut candidates: Vec<String> = Vec::new();
        if let Some((stem, ext)) = base.rsplit_once('.') {
            let mapped: &[&str] = match ext {
                "js" => &["ts", "tsx"],
                "jsx" => &["tsx"],
                "mjs" => &["mts"],
                "cjs" => &["cts"],
                _ => &[],
            };
            candidates.extend(mapped.iter().map(|m| format!("{stem}.{m}")));
        }
        candidates.push(base.clone());
        candidates.extend(EXTENSIONS.iter().map(|e| format!("{base}.{e}")));
        let dir = if base.is_empty() {
            "index".to_owned()
        } else {
            format!("{base}/index")
        };
        candidates.extend(EXTENSIONS.iter().map(|e| format!("{dir}.{e}")));
        candidates.into_iter().find(|c| self.files.contains(c))
    }
}

/// How sure a set of targets is, and what they are.
struct Found {
    nodes: Vec<NodeIndex>,
    status: Status,
}

impl Found {
    fn one_or_many(nodes: Vec<NodeIndex>) -> Option<Self> {
        let status = match nodes.len() {
            0 => return None,
            1 => Status::Must,
            _ => Status::May,
        };
        Some(Self { nodes, status })
    }
}

/// The import status edge of `from`.
fn import_edge(
    from: &str,
    to: Option<Symref>,
    status: Status,
    name: &str,
    reason: Option<GapReason>,
) -> StatusEdge {
    StatusEdge {
        from: Symref::file(from),
        to,
        kind: EdgeKind::Imports,
        status,
        name: Some(name.to_owned()),
        reason,
        qualifier: None,
        line: None,
        text: None,
    }
}

/// Records the module edge of the import of `spec` by `path` at `status`: a link and Must/May edge to a file, or an Unknown edge.
fn link_module(
    ts: &TsIndex,
    path: &str,
    from: NodeIndex,
    spec: &str,
    status: Status,
    links: &mut BTreeMap<(NodeIndex, NodeIndex), Status>,
    edges: &mut Vec<StatusEdge>,
) {
    match ts.resolve(path, spec) {
        Module::Local(p) => {
            let Some(&to) = ts.file_nodes.get(&p) else {
                return;
            };
            if to != from {
                let w = links.entry((from, to)).or_insert(status);
                *w = (*w).max(status);
            }
            edges.push(import_edge(
                path,
                Some(Symref::file(&p)),
                status,
                spec,
                None,
            ));
        }
        Module::External => {
            tracing::debug!(from = %path, spec, "typescript import external");
            edges.push(import_edge(
                path,
                None,
                Status::Unknown,
                spec,
                Some(GapReason::External),
            ));
        }
        Module::Missing | Module::Bare => {
            tracing::debug!(from = %path, spec, "typescript import unresolved");
            edges.push(import_edge(
                path,
                None,
                Status::Unknown,
                spec,
                Some(GapReason::Unbound),
            ));
        }
    }
}

impl SymbolGraph {
    /// The units the import binding `local` of TypeScript file `from` names, each with how sure the module graph is.
    ///
    /// Empty when `local` is not an import of `from` or nothing in the repository answers it (a package, a
    /// missing file); several entries are a May answer (an ambiguous re-export).
    pub fn ts_import_targets(&self, from: &str, local: &str) -> Vec<(Symref, Status)> {
        let mut out = Vec::new();
        for u in Self::ts_uses(&self.ts, &Symref::file(from), local) {
            if let Some(f) = self.ts_binding(&self.ts, from, u, None, 0) {
                out.extend(
                    f.nodes
                        .iter()
                        .map(|&n| (self.graph[n].symref.clone(), f.status)),
                );
            }
        }
        tracing::trace!(
            from,
            local,
            targets = out.len(),
            "typescript import binding resolved"
        );
        out
    }

    /// The module specifier and imported member (`default`, `*` or a name) of the import binding `local` in `from`.
    pub fn ts_import_source(&self, from: &str, local: &str) -> Option<(String, String)> {
        let u = *Self::ts_uses(&self.ts, &Symref::file(from), local).first()?;
        let r = decode_use(&u.target);
        (r.mode != ImportMode::Unknown)
            .then(|| (r.spec.to_owned(), r.member.unwrap_or_default().to_owned()))
    }

    /// The units `name` exports from `path`: its own public declarations, an alias or re-export binding, then `export *`.
    fn ts_export(&self, ts: &TsIndex, path: &str, name: &str, depth: usize) -> Option<Found> {
        let &file_node = ts.file_nodes.get(path)?;
        let own: Vec<NodeIndex> = ts
            .kids_of(file_node, name)
            .iter()
            .copied()
            .filter(|&n| self.graph[n].visibility == Visibility::Public)
            .collect();
        if let Some(f) = Found::one_or_many(own) {
            return Some(f);
        }
        if depth >= MAX_REEXPORT {
            return None;
        }
        let bindings = ts.uses.get(path).map_or(&[][..], Vec::as_slice);
        let mut nodes = Vec::new();
        let mut all_must = true;
        let mut sources = 0usize;
        for u in bindings
            .iter()
            .filter(|u| u.public && u.container.is_none() && u.local == name)
        {
            if let Some(f) = self.ts_binding(ts, path, u, None, depth + 1) {
                sources += 1;
                all_must &= f.status == Status::Must;
                nodes.extend(f.nodes);
            }
        }
        if nodes.is_empty() && name != "default" {
            for u in bindings
                .iter()
                .filter(|u| u.public && u.container.is_none() && u.local == "*")
            {
                let r = decode_use(&u.target);
                let Module::Local(p) = ts.resolve(path, r.spec) else {
                    continue;
                };
                if let Some(f) = self.ts_export(ts, &p, name, depth + 1) {
                    sources += 1;
                    all_must &= f.status == Status::Must;
                    nodes.extend(f.nodes);
                }
            }
        }
        nodes.sort();
        nodes.dedup();
        let status = if sources == 1 && all_must && nodes.len() == 1 {
            Status::Must
        } else {
            Status::May
        };
        (!nodes.is_empty()).then_some(Found { nodes, status })
    }

    /// The units a binding of `from` stands for; `member_as` replaces a `*` member (a direct call of a `require`d module).
    fn ts_binding(
        &self,
        ts: &TsIndex,
        from: &str,
        u: &UseBinding,
        member_as: Option<&str>,
        depth: usize,
    ) -> Option<Found> {
        let r = decode_use(&u.target);
        let mut member = r.member?;
        if member == "*" {
            member = member_as.unwrap_or("*");
        }
        let Module::Local(p) = ts.resolve(from, r.spec) else {
            return None;
        };
        let mut found = if member == "*" {
            Found {
                nodes: vec![*ts.file_nodes.get(&p)?],
                status: Status::Must,
            }
        } else if r.spec.is_empty() {
            let file_node = *ts.file_nodes.get(&p)?;
            match Found::one_or_many(ts.kids_of(file_node, member).to_vec()) {
                Some(f) => f,
                // `import { a as v } from "./a"; export { v };` re-exports an import of this file.
                None if depth < MAX_REEXPORT => ts
                    .uses
                    .get(&p)
                    .into_iter()
                    .flatten()
                    .filter(|b| !b.public && b.container.is_none() && b.local == member)
                    .find_map(|b| self.ts_binding(ts, &p, b, None, depth + 1))?,
                None => return None,
            }
        } else {
            self.ts_export(ts, &p, member, depth)?
        };
        if r.mode == ImportMode::May {
            found.status = found.status.meet(Status::May);
        }
        Some(found)
    }

    /// The innermost enclosing class of `n` (itself excluded), through nested functions.
    fn ts_class_of(&self, n: NodeIndex) -> Option<NodeIndex> {
        let mut cur = self.parent_of(n);
        while let Some(p) = cur {
            if self.graph[p].kind == SymbolKind::Class {
                return Some(p);
            }
            cur = self.parent_of(p);
        }
        None
    }

    /// The units named `name` visible lexically from `caller`: nested declarations, then module level (class scopes are skipped).
    fn ts_lexical(&self, ts: &TsIndex, caller: NodeIndex, name: &str) -> Vec<NodeIndex> {
        let mut cur = Some(caller);
        while let Some(n) = cur {
            if self.graph[n].kind != SymbolKind::Class {
                let found = ts.kids_of(n, name);
                if !found.is_empty() {
                    return found.to_vec();
                }
            }
            cur = self.parent_of(n);
        }
        Vec::new()
    }

    /// The use bindings of the caller's file named `local` that are in scope at `caller`.
    fn ts_uses<'a>(ts: &'a TsIndex, caller: &Symref, local: &str) -> Vec<&'a UseBinding> {
        ts.uses
            .get(caller.path())
            .into_iter()
            .flatten()
            .filter(|u| !u.public && u.local == local)
            .filter(|u| {
                u.container.as_ref().is_none_or(|c| {
                    c.path() == caller.path() && caller.segments().starts_with(c.segments())
                })
            })
            .collect()
    }

    /// A class result becomes its `constructor` when it has one.
    fn ts_construct(&self, ts: &TsIndex, nodes: Vec<NodeIndex>) -> Vec<NodeIndex> {
        nodes
            .into_iter()
            .map(|n| {
                if self.graph[n].kind == SymbolKind::Class
                    && let Some(&ctor) = ts.kids_of(n, "constructor").first()
                {
                    ctor
                } else {
                    n
                }
            })
            .collect()
    }

    /// The units a bare name stands for at `caller`, or `None` when nothing in the repository does.
    fn ts_name(&self, ts: &TsIndex, caller: &Symref, node: NodeIndex, name: &str) -> Option<Found> {
        let lexical = self.ts_lexical(ts, node, name);
        if let Some(f) = Found::one_or_many(lexical) {
            return Some(f);
        }
        let mut nodes = Vec::new();
        let mut status = Status::Must;
        for u in Self::ts_uses(ts, caller, name) {
            if let Some(f) = self.ts_binding(ts, caller.path(), u, Some("default"), 0) {
                status = status.meet(f.status);
                nodes.extend(f.nodes);
            }
        }
        nodes.sort();
        nodes.dedup();
        if nodes.is_empty() {
            return None;
        }
        if nodes.len() > 1 {
            status = Status::May;
        }
        Some(Found { nodes, status })
    }

    /// Every TypeScript method named `name` as May candidates, or an external gap when none exists.
    fn ts_unknown_receiver(ts: &TsIndex, name: &str) -> Outcome {
        match ts.methods.get(name) {
            Some(ms) if !ms.is_empty() => Outcome::Hit(ms.clone(), Status::May),
            _ => Outcome::Gap(GapReason::Unbound),
        }
    }

    /// Follows `segs` from the binding `u`: the module's export `segs[0]` for a namespace import, else the
    /// imported name then `segs` as members.
    fn ts_path(&self, ts: &TsIndex, from: &str, u: &UseBinding, segs: &[String]) -> Option<Found> {
        let r = decode_use(&u.target);
        let member = r.member?;
        let (mut found, rest) = if member == "*" {
            let Module::Local(p) = ts.resolve(from, r.spec) else {
                return None;
            };
            let first = segs.first()?;
            (self.ts_export(ts, &p, first, 0)?, &segs[1..])
        } else {
            (self.ts_binding(ts, from, u, None, 0)?, segs)
        };
        if r.mode == ImportMode::May {
            found.status = found.status.meet(Status::May);
        }
        for seg in rest {
            let next: Vec<NodeIndex> = found
                .nodes
                .iter()
                .flat_map(|&n| ts.kids_of(n, seg).iter().copied())
                .collect();
            if next.is_empty() {
                return None;
            }
            if next.len() > 1 {
                found.status = Status::May;
            }
            found.nodes = next;
        }
        Some(found)
    }

    /// Resolves the call `call` of a TypeScript or JavaScript caller.
    pub(super) fn resolve_typescript(&self, ts: &TsIndex, call: &CallSite) -> Outcome {
        let Some(&node) = self.index.get(&call.caller) else {
            return Outcome::Gap(GapReason::Unbound);
        };
        if call.callee.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        if call.method {
            if call.receiver == Some(Receiver::SelfValue)
                && let Some(class) = self.ts_class_of(node)
            {
                let own = ts.kids_of(class, &call.callee);
                if !own.is_empty() {
                    return Outcome::Hit(own.to_vec(), Status::Must);
                }
            }
            return Self::ts_unknown_receiver(ts, &call.callee);
        }
        let Some(head) = call.qual_path.first() else {
            if call.local != LocalBinding::None {
                return Outcome::Gap(GapReason::LocalValue);
            }
            return match self.ts_name(ts, &call.caller, node, &call.callee) {
                Some(f) => Outcome::Hit(self.ts_construct(ts, f.nodes), f.status),
                None => Outcome::Gap(GapReason::Unbound),
            };
        };
        let mut segs: Vec<String> = call.qual_path[1..].to_vec();
        segs.push(call.callee.clone());
        let lexical = self.ts_lexical(ts, node, head);
        if !lexical.is_empty() {
            return self.ts_chain(ts, lexical, &segs);
        }
        let from = call.caller.path();
        let mut nodes = Vec::new();
        let mut status = Status::Must;
        for u in Self::ts_uses(ts, &call.caller, head) {
            if let Some(f) = self.ts_path(ts, from, u, &segs) {
                status = status.meet(f.status);
                nodes.extend(f.nodes);
            } else if let Some(f) = self.ts_path(ts, from, u, &segs[..segs.len() - 1])
                && f.nodes
                    .iter()
                    .all(|&n| self.graph[n].kind == SymbolKind::Class)
            {
                // The qualifier is a repository class that does not declare the callee: inherited.
                return Self::ts_unknown_receiver(ts, &call.callee);
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
        Outcome::Hit(self.ts_construct(ts, nodes), status)
    }

    /// Follows `segs` through the members of `start` (classes, namespaces and functions of this repository).
    fn ts_chain(&self, ts: &TsIndex, start: Vec<NodeIndex>, segs: &[String]) -> Outcome {
        let mut cur = start;
        for seg in segs {
            let next: Vec<NodeIndex> = cur
                .iter()
                .flat_map(|&n| ts.kids_of(n, seg).iter().copied())
                .collect();
            if next.is_empty() {
                return Self::ts_unknown_receiver(ts, segs.last().map_or("", String::as_str));
            }
            cur = next;
        }
        let status = if cur.len() == 1 {
            Status::Must
        } else {
            Status::May
        };
        Outcome::Hit(self.ts_construct(ts, cur), status)
    }

    /// Resolves a function used as a value (`onClick={handler}`, `map(f, xs)`); only a Hit matters.
    pub(super) fn resolve_typescript_value(
        &self,
        ts: &TsIndex,
        r: &RefSite,
    ) -> Option<Vec<NodeIndex>> {
        let node = *self.index.get(&r.from)?;
        self.ts_name(ts, &r.from, node, &r.name).map(|f| f.nodes)
    }

    /// Links each TypeScript file to the modules and symbols its imports name, keeps an Unknown edge for
    /// every import nothing can be claimed about, and marks re-exported symbols as public API roots.
    pub(super) fn link_typescript_imports(&mut self, ts: &TsIndex) {
        let mut links: BTreeMap<(NodeIndex, NodeIndex), Status> = BTreeMap::new();
        let mut edges: Vec<StatusEdge> = Vec::new();
        let mut roots: Vec<NodeIndex> = Vec::new();
        for (path, imports) in &ts.imports {
            let Some(&from) = ts.file_nodes.get(path) else {
                continue;
            };
            for e in imports {
                let r = decode_edge(&e.target);
                let status = match r.mode {
                    ImportMode::Static => Status::Must,
                    ImportMode::May => Status::May,
                    ImportMode::Unknown => {
                        edges.push(import_edge(
                            path,
                            None,
                            Status::Unknown,
                            r.spec,
                            Some(GapReason::Dynamic),
                        ));
                        continue;
                    }
                };
                link_module(ts, path, from, r.spec, status, &mut links, &mut edges);
            }
            for u in ts.uses.get(path).into_iter().flatten() {
                let r = decode_use(&u.target);
                if u.public && u.container.is_none() {
                    let Module::Local(p) = ts.resolve(path, r.spec) else {
                        continue;
                    };
                    if r.member == Some("*") && u.local == "*" {
                        if let Some(&target) = ts.file_nodes.get(&p) {
                            roots.extend(
                                self.graph
                                    .edges_directed(target, Direction::Outgoing)
                                    .filter(|e| e.weight().kind == EdgeKind::Contains)
                                    .map(|e| e.target())
                                    .filter(|&k| self.graph[k].visibility == Visibility::Public),
                            );
                        }
                    } else if let Some(f) = self.ts_binding(ts, path, u, None, 0) {
                        roots.extend(f.nodes);
                    }
                }
                if r.spec.is_empty() || r.member.is_none_or(|m| m == "*") {
                    continue;
                }
                if let Some(f) = self.ts_binding(ts, path, u, None, 0) {
                    for n in f.nodes {
                        if n != from {
                            let w = links.entry((from, n)).or_insert(f.status);
                            *w = (*w).max(f.status);
                        }
                        edges.push(import_edge(
                            path,
                            Some(self.graph[n].symref.clone()),
                            f.status,
                            r.member.unwrap_or_default(),
                            None,
                        ));
                    }
                }
            }
        }
        for ((a, b), status) in links {
            self.link(a, b, EdgeKind::Imports, status);
        }
        self.reexported.extend(roots);
        self.status_edges.extend(edges);
    }
}
