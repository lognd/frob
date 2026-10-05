//! The repository-level symbol graph (petgraph) and its queries.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet, VecDeque};
use std::sync::Mutex;

pub use gob_ir::Status;

use gob_text::{TextRange, TextSize};
use petgraph::Direction;
use petgraph::graph::{DiGraph, EdgeIndex, NodeIndex};
use petgraph::visit::EdgeRef;
use rayon::prelude::*;

use crate::adapter::{Fidelity, ParseStatus};
use crate::crates::CrateDeps;
use crate::model::{
    CallRef, CallSite, Digests, FacetDigest, FieldDecl, FileSymbols, ImportEdge, LocalBinding,
    MapKind, Receiver, RefKind, RefSite, RetType, SymbolKind, SymbolRecord, UnitExtras, UseBinding,
    Visibility,
};
use crate::paths::crate_and_module;
use crate::qualifier::{Admit, CallQualifier};
use crate::stdtypes;
use crate::symref::{Symref, Target, split_qual};

mod python;

use python::{PyIndex, is_python};

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
    /// (from, to, kind) to its edge: `link` dedupes in O(1) instead of scanning a hub's adjacency list.
    edge_ix: HashMap<(NodeIndex, NodeIndex, EdgeKind), EdgeIndex>,
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
    /// Importing file to its external (non-`crate`) `use` bindings.
    ext_uses: HashMap<String, Vec<UseBinding>>,
    /// Source file to the directory of the crate that owns it (only with a manifest above it).
    file_crate: HashMap<String, String>,
    /// Crate directory to the directories of the crates it links transitively (unknown-receiver candidates).
    reach: HashMap<String, Vec<String>>,
    /// Crate directory to the extern crate names nameable inside it, with their directories.
    externs: HashMap<String, Vec<(String, String)>>,
    /// (crate dir, module path) to the file-level `pub use` bindings of that module.
    pubuses: HashMap<(String, String), Vec<UseBinding>>,
    /// (crate dir, struct or enum name) to its typed fields (the field type table; variant fields are `Variant.field`).
    fields: HashMap<(String, String), Vec<(FieldDecl, String)>>,
    /// (file, type name) to the number of structs and enums that file declares: a name declared once in the
    /// calling file is that file's type whatever else shares the name (integration tests are separate crates).
    file_types: HashMap<(String, String), usize>,
    /// (crate dir, type name) to the number of structs and enums declared so (a field table is only sound for one).
    struct_count: HashMap<(String, String), usize>,
    /// Names of structs and enums declared anywhere in the repository.
    declared_types: HashSet<String>,
    /// Names of types with an `impl Deref` or `impl DerefMut`: methods may come from the target.
    deref_types: HashSet<String>,
    /// Receiver types already worked out, per calling symbol (a method chain would otherwise be re-resolved at every link).
    memo: Vec<MemoShard>,
    /// Names of `Result`/`Option` aliases whose first parameter is not the Ok/Some type (`?` and `unwrap` cannot be trusted).
    opaque_aliases: HashSet<String>,
    /// Names of `macro_rules!` macros declared anywhere (they may shadow a std macro of the same name).
    declared_macros: HashSet<String>,
    /// (crate dir, name) of enums (a unit-struct value never names one).
    enums: HashSet<(String, String)>,
    /// (crate dir, type name) to the traits that type derives.
    derives: HashMap<(String, String), Vec<String>>,
    /// Names of every function and method declared anywhere in the repository.
    callable_names: HashSet<String>,
    /// (crate dir, name) of module-level type aliases: a declared type of these says nothing about the callee.
    aliases: HashSet<(String, String)>,
    /// Lookup tables of the Python files (their calls resolve by name and import, not by crate).
    py: PyIndex,
}

/// Lock shards of the receiver-type memo (parallel call resolution would otherwise queue on one lock).
const MEMO_SHARDS: usize = 64;

/// One lock shard of the receiver-type memo.
type MemoShard = Mutex<HashMap<(Symref, Receiver), Option<Ty>>>;

impl Index {
    /// The memo shard owning `caller`'s entries.
    fn memo_shard(&self, caller: &Symref) -> &MemoShard {
        use std::hash::{BuildHasher, BuildHasherDefault, DefaultHasher};
        let h = BuildHasherDefault::<DefaultHasher>::default().hash_one(caller);
        &self.memo[usize::try_from(h % MEMO_SHARDS as u64).expect("shard index fits usize")]
    }

    /// Every function and method called `name` in the caller's crate and the crates it links.
    fn callables_in_reach(&self, caller: &Symref, name: &str) -> Vec<NodeIndex> {
        let here = crate_and_module(caller.path()).0;
        let linked: Vec<String> = self
            .file_crate
            .get(caller.path())
            .and_then(|o| self.reach.get(o))
            .into_iter()
            .flatten()
            .filter(|d| **d != here)
            .cloned()
            .collect();
        std::iter::once(here)
            .chain(linked)
            .filter_map(|c| self.by_name.get(&(c, name.to_owned())))
            .flatten()
            .copied()
            .collect()
    }

    /// The crate-relative paths at which `segs` is defined in crate `dir`, following `pub use` re-exports.
    fn canonical_paths(&self, dir: &str, segs: &[String], depth: usize) -> Vec<(String, String)> {
        const MAX_HOPS: usize = 8;
        let joined = segs.join("::");
        // A module and a function may share a name (`mod ack` and `pub use ack::ack`): keep both.
        let mut out = Vec::new();
        if self.by_item.contains_key(&(dir.to_owned(), joined.clone())) {
            out.push((dir.to_owned(), joined));
        }
        let Some((last, parent)) = segs.split_last() else {
            return out;
        };
        if depth >= MAX_HOPS {
            return out;
        }
        let module = parent.join("::");
        for u in self
            .pubuses
            .get(&(dir.to_owned(), module))
            .into_iter()
            .flatten()
        {
            let internal = u.is_internal();
            let path = if internal {
                rel_path(&u.target)
            } else {
                u.target.as_str()
            };
            let next: Vec<String> = if let Some(glob) = path.strip_suffix("::*") {
                glob.split("::")
                    .filter(|s| !s.is_empty())
                    .map(str::to_owned)
                    .chain(std::iter::once(last.clone()))
                    .collect()
            } else if u.local == *last {
                path.split("::").map(str::to_owned).collect()
            } else {
                continue;
            };
            if internal {
                out.extend(self.canonical_paths(dir, &next, depth + 1));
            } else if let Some((head, rest)) = next.split_first()
                && let Some((_, other)) = self
                    .externs
                    .get(dir)
                    .and_then(|ext| ext.iter().find(|(n, _)| n == head))
            {
                // A `pub use other_crate::Item;` re-export: follow it into the other crate.
                out.extend(self.canonical_paths(other, rest, depth + 1));
            }
        }
        out.sort();
        out.dedup();
        out
    }

    /// `t` as `file` imports it: `use a::B as t` names type `B`.
    fn real_type_name(&self, file: &str, t: &str) -> String {
        self.uses
            .get(file)
            .into_iter()
            .chain(self.ext_uses.get(file))
            .flatten()
            .find(|u| u.local == t && !u.target.ends_with("::*"))
            .and_then(|u| u.target.rsplit("::").next().map(str::to_owned))
            .unwrap_or_else(|| t.to_owned())
    }

    /// True when the path call `path` written in `file` names the standard library (`std::fs`, an imported `fs`, `String`).
    fn is_std_path(&self, file: &str, path: &[String]) -> bool {
        let [first, rest @ ..] = path else {
            return false;
        };
        if matches!(first.as_str(), "std" | "core" | "alloc") {
            return true;
        }
        if !rest.is_empty() {
            return false;
        }
        let import = self
            .uses
            .get(file)
            .into_iter()
            .chain(self.ext_uses.get(file))
            .flatten()
            .find(|u| u.local == *first && !u.target.ends_with("::*"));
        match import {
            Some(u) => u.target.starts_with("std::") || u.target.starts_with("core::"),
            None => {
                first == "str"
                    || (first.starts_with(char::is_uppercase)
                        && !self.declared_types.contains(first)
                        && !self.is_alias(file, first))
            }
        }
    }

    /// `ty`, or the JSON-like value head when it names `serde_json::Value`, `toml::Value` and the like.
    fn canonical_ext(&self, ty: Ty) -> Ty {
        let path = match ty.qual.as_slice() {
            [] => self
                .uses
                .get(&ty.file)
                .into_iter()
                .chain(self.ext_uses.get(&ty.file))
                .flatten()
                .find(|u| u.local == ty.head && !u.target.ends_with("::*"))
                .map(|u| u.target.clone()),
            qual => Some(format!("{}::{}", qual.join("::"), ty.head)),
        };
        match path {
            Some(p) if stdtypes::is_json_path(&p) => Ty::plain(stdtypes::JSON.to_owned(), &ty.file),
            _ => ty,
        }
    }

    /// True when `ty` is written as a standard-library path (`std::process::Output`) or imported from one.
    fn is_std_type(&self, ty: &Ty) -> bool {
        let std = |p: &str| matches!(p, "std" | "core" | "alloc");
        if let Some(first) = ty.qual.first() {
            return std(first);
        }
        self.uses
            .get(&ty.file)
            .into_iter()
            .chain(self.ext_uses.get(&ty.file))
            .flatten()
            .find(|u| u.local == ty.head && !u.target.ends_with("::*"))
            .is_some_and(|u| std(u.target.split("::").next().unwrap_or("")))
    }

    /// True when the type name `written` in `file` may be a type alias.
    ///
    /// An alias declared in the file's own crate counts; one declared elsewhere only when the file
    /// imports the name (or has a glob import that could bring it in).
    fn is_alias(&self, file: &str, written: &str) -> bool {
        let krate = crate_and_module(file).0;
        let real = self.real_type_name(file, written);
        let named = |n: &str| self.aliases.iter().any(|(_, a)| a == n);
        if [written, real.as_str()]
            .iter()
            .any(|n| self.aliases.contains(&(krate.clone(), (*n).to_owned())))
        {
            return true;
        }
        let imports = self
            .uses
            .get(file)
            .into_iter()
            .chain(self.ext_uses.get(file))
            .flatten()
            .any(|u| u.local == written || u.target.ends_with("::*"));
        imports && (named(written) || named(&real))
    }

    /// Sorts every file's `use` bindings into internal, external and re-exported.
    ///
    /// A file-level `use inputs::Inputs;` names a module of the current module (2018 paths): when
    /// that item exists it is the internal `crate::..` binding, not an extern crate path.
    fn classify_uses(&mut self, files: &[FileSymbols]) {
        for f in files.iter().filter(|f| is_rust(&f.path)) {
            let (krate, module) = crate_and_module(&f.path);
            let mut internal = Vec::new();
            let mut external = Vec::new();
            for u in &f.uses {
                let mut u = u.clone();
                if !u.is_internal() && u.container.is_none() {
                    let rel = u.target.strip_suffix("::*").unwrap_or(&u.target);
                    let mut key = module.clone();
                    key.extend(rel.split("::").map(str::to_owned));
                    let mut head = module.clone();
                    head.extend(rel.split("::").next().map(str::to_owned));
                    if self.by_item.contains_key(&(krate.clone(), head.join("::"))) {
                        let glob = if u.target.ends_with("::*") { "::*" } else { "" };
                        u.target = format!("crate::{}{glob}", key.join("::"));
                    }
                }
                if u.public && u.container.is_none() {
                    self.pubuses
                        .entry((krate.clone(), module.join("::")))
                        .or_default()
                        .push(u.clone());
                }
                if u.is_internal() {
                    internal.push(u);
                } else {
                    external.push(u);
                }
            }
            self.uses.insert(f.path.clone(), internal);
            self.ext_uses.insert(f.path.clone(), external);
        }
    }

    /// Records what the declaration `s` in crate `krate` contributes to the type tables.
    fn note_symbol(&mut self, krate: &str, s: &SymbolRecord, assoc: bool) {
        match (s.kind, s.symref.name()) {
            (SymbolKind::Struct, Some(n)) => {
                let n = base_segment(n);
                *self
                    .file_types
                    .entry((s.symref.path().to_owned(), n.to_owned()))
                    .or_default() += 1;
                *self
                    .struct_count
                    .entry((krate.to_owned(), n.to_owned()))
                    .or_default() += 1;
                self.declared_types.insert(n.to_owned());
            }
            (SymbolKind::Enum, Some(n)) => {
                let n = base_segment(n);
                self.enums.insert((krate.to_owned(), n.to_owned()));
                *self
                    .file_types
                    .entry((s.symref.path().to_owned(), n.to_owned()))
                    .or_default() += 1;
                *self
                    .struct_count
                    .entry((krate.to_owned(), n.to_owned()))
                    .or_default() += 1;
                self.declared_types.insert(n.to_owned());
            }
            (SymbolKind::Macro, Some(n)) => {
                self.declared_macros.insert(n.to_owned());
            }
            (SymbolKind::TypeAlias, Some(n)) if !assoc => {
                self.aliases.insert((krate.to_owned(), n.to_owned()));
            }
            (SymbolKind::Impl, _) => {
                let tr = s.implements.as_deref().unwrap_or("");
                let tr = tr.split('<').next().unwrap_or(tr);
                if matches!(tr.rsplit("::").next(), Some("Deref" | "DerefMut"))
                    && let Some(seg) = s.symref.segments().last()
                {
                    self.deref_types.insert(base_segment(seg).to_owned());
                }
            }
            _ => {}
        }
    }

    /// The type of `owner.field` (and the file declaring it) when `owner` is the only struct so named in `krate`.
    fn field_type(&self, via: &Ty, krate: &str, owner: &str, field: &str) -> Option<Ty> {
        let key = (krate.to_owned(), owner.to_owned());
        let local = self.declared_once_in(&via.file, krate, owner);
        if !local && self.struct_count.get(&key) != Some(&1) {
            return None;
        }
        let mut hits = self
            .fields
            .get(&key)?
            .iter()
            .filter(|(d, f)| d.field == field && (!local || *f == via.file));
        let (first, file) = hits.next()?;
        hits.next()
            .is_none()
            .then(|| Ty::from_shape(&first.ty, file))
    }

    /// True when `file` (in crate `krate`) declares the type `name` exactly once: there it is that type.
    fn declared_once_in(&self, file: &str, krate: &str, name: &str) -> bool {
        crate_and_module(file).0 == krate
            && self.file_types.get(&(file.to_owned(), name.to_owned())) == Some(&1)
    }

    /// The directory of the extern crate named `name` in `file`'s crate (itself, or a direct dependency).
    fn extern_dir(&self, file: &str, name: &str) -> Option<String> {
        let externs = self.externs.get(self.file_crate.get(file)?)?;
        externs
            .iter()
            .find(|(n, _)| n == name)
            .map(|(_, d)| d.clone())
    }

    /// The extern crate directory and crate-relative path that `file` imports `local` from, by explicit `use`.
    fn explicit_extern(&self, file: &str, local: &str) -> Option<(String, Vec<String>)> {
        let externs = self.externs.get(self.file_crate.get(file)?)?;
        let u = self
            .ext_uses
            .get(file)?
            .iter()
            .find(|u| u.local == local && !u.target.ends_with("::*"))?;
        let mut segs = u.target.split("::").map(str::to_owned);
        let head = segs.next()?;
        let dir = externs.iter().find(|(n, _)| *n == head)?.1.clone();
        Some((dir, segs.collect()))
    }
}

impl Ty {
    /// The plain type `head` written in `file`.
    fn plain(head: String, file: &str) -> Self {
        Self {
            qual: Vec::new(),
            bound: None,
            tuple: None,
            head,
            arg: None,
            arg2: None,
            file: file.to_owned(),
        }
    }

    /// The type `shape` describes, its names written in `file`.
    fn from_shape(shape: &RetType, file: &str) -> Self {
        let known = |a: &Option<String>| a.clone().filter(|a| a != "_");
        Self {
            tuple: shape.tuple.clone(),
            arg: known(&shape.arg),
            arg2: known(&shape.arg2),
            ..Self::plain(shape.head.clone(), file)
        }
        .dyn_normalized()
    }

    /// A trait-object head (`dyn:A+B`) as `Self` known only by the traits `A` and `B`.
    fn dyn_normalized(mut self) -> Self {
        if let Some(traits) = self.head.strip_prefix(stdtypes::DYN) {
            self.bound = Some(traits.split('+').map(str::to_owned).collect());
            "Self".clone_into(&mut self.head);
        }
        self
    }

    /// The generic shape of `self` (head, arguments and tuple elements).
    fn shape(&self) -> RetType {
        RetType {
            head: self.head.clone(),
            arg: self.arg.clone(),
            arg2: self.arg2.clone(),
            tuple: self.tuple.clone(),
        }
    }

    /// `self` with a path written in `head` (`gob_ir::Ctx`) split into `qual` and the bare name.
    fn with_split_path(mut self) -> Self {
        if self.head.contains("::") {
            let mut segs: Vec<String> = self.head.split("::").map(str::to_owned).collect();
            self.head = segs.pop().unwrap_or_default();
            self.qual = segs;
        }
        self
    }
}

/// A receiver type proven for a call.
#[derive(Debug, Clone)]
struct Ty {
    /// The module path written before `head` (`gob_ir` in `gob_ir::Ctx`).
    qual: Vec<String>,
    /// The traits `Self` stands for, when `head` is `Self` returned through trait bounds.
    bound: Option<Vec<String>>,
    /// The element types of a tuple value.
    tuple: Option<Vec<Option<String>>>,
    /// The type name as written (`written` in `use a::B as written`).
    head: String,
    /// The first generic argument, for `Result<T, _>`, `Option<T>` and `Vec<T>`.
    arg: Option<String>,
    /// The second generic argument, for `HashMap<K, V>`.
    arg2: Option<String>,
    /// The file whose imports the names are written against.
    file: String,
}

/// What a call site asks the resolver, independent of how it was written.
struct Query<'a> {
    /// Simple callee name.
    name: &'a str,
    /// Last qualifying path segment.
    qualifier: Option<&'a str>,
    /// All qualifying path segments.
    path: &'a [String],
    /// Trait bounds of a generic qualifier (`C::new(..)` with `C: Command`).
    bound: &'a [String],
    /// True for method-call syntax.
    method: bool,
    /// Argument count of a call, receiver excluded.
    args: Option<usize>,
}

/// The outcome of resolving one reference site.
enum Outcome {
    /// Targets with the status of the edges to them.
    Hit(Vec<NodeIndex>, Status),
    /// A call through a trait bound: Must to the trait's method, May to its implementations.
    Dispatch(NodeIndex, Vec<NodeIndex>),
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

/// Call sites per parallel task in `link_calls` (small enough that one huge file cannot serialize the pass).
const CALL_CHUNK: usize = 256;

/// One chunk's call-resolution output, merged into the graph in file order.
#[derive(Default)]
struct CallSink {
    links: Vec<(NodeIndex, NodeIndex, EdgeKind, Status)>,
    calls: Vec<CallEdge>,
    status_edges: Vec<StatusEdge>,
    poisoned: Vec<NodeIndex>,
}

impl SymbolGraph {
    /// Builds the graph from per-file results (any order), without crate manifests: calls resolve within a crate only.
    pub fn from_files(files: Vec<FileSymbols>) -> Self {
        Self::build(files, None)
    }

    /// Builds the graph like [`Self::from_files`], resolving path calls across workspace crates
    /// through `use` imports and the dependency closure read by `deps`.
    pub fn from_files_with_deps(files: Vec<FileSymbols>, deps: &mut CrateDeps) -> Self {
        Self::build(files, Some(deps))
    }

    fn build(mut files: Vec<FileSymbols>, deps: Option<&mut CrateDeps>) -> Self {
        let t = std::time::Instant::now();
        let lap = |phase: &str| {
            tracing::debug!(
                phase,
                ms = t.elapsed().as_millis(),
                "graph assembly phase done"
            );
        };
        files.sort_by(|a, b| a.path.cmp(&b.path));
        // frob:ticket 01M44YQSZ3YEXRDW9RKER9HRA2
        crate::model::merge_partials(&mut files);
        let mut g = Self::default();
        for f in &files {
            g.add_file(f);
        }
        lap("add_file");
        let idx = g.index_of(&files, deps);
        lap("index_of");
        g.link_imports(&idx);
        g.link_python_imports(&idx.py, &files);
        g.link_reexports(&files, &idx);
        lap("imports");
        g.link_calls(&files, &idx);
        lap("calls");
        g.link_refs(&files, &idx);
        lap("refs");
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
        if let Some(&id) = self.edge_ix.get(&(a, b, kind)) {
            let w = &mut self.graph[id];
            w.status = w.status.max(status);
        } else {
            let id = self.graph.add_edge(a, b, Edge { kind, status });
            self.edge_ix.insert((a, b, kind), id);
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
            signature: None,
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

    fn index_of(&self, files: &[FileSymbols], mut deps: Option<&mut CrateDeps>) -> Index {
        let mut idx = Index {
            by_item: HashMap::new(),
            by_name: HashMap::new(),
            uses: HashMap::new(),
            ext_uses: HashMap::new(),
            file_crate: HashMap::new(),
            externs: HashMap::new(),
            reach: HashMap::new(),
            pubuses: HashMap::new(),
            fields: HashMap::new(),
            struct_count: HashMap::new(),
            declared_types: HashSet::new(),
            deref_types: HashSet::new(),
            aliases: HashSet::new(),
            declared_macros: HashSet::new(),
            opaque_aliases: HashSet::new(),
            memo: (0..MEMO_SHARDS).map(|_| Mutex::default()).collect(),
            callable_names: HashSet::new(),
            derives: HashMap::new(),
            file_types: HashMap::new(),
            enums: HashSet::new(),
            py: PyIndex::build(self, files),
        };
        for f in files.iter().filter(|f| is_rust(&f.path)) {
            let (krate, module) = crate_and_module(&f.path);
            if let Some(d) = deps.as_deref_mut()
                && let Some(owner) = d.crate_of(&f.path)
            {
                if !idx.externs.contains_key(&owner) {
                    let named = d.extern_crates(&owner);
                    idx.externs.insert(owner.clone(), named);
                    idx.reach.insert(owner.clone(), d.transitive_deps(&owner));
                }
                idx.file_crate.insert(f.path.clone(), owner);
            }
            idx.opaque_aliases.extend(f.opaque_aliases.iter().cloned());
            for d in &f.derives {
                idx.derives
                    .entry((krate.clone(), d.owner.clone()))
                    .or_default()
                    .extend(d.traits.iter().cloned());
            }
            for d in &f.fields {
                idx.fields
                    .entry((krate.clone(), d.owner.clone()))
                    .or_default()
                    .push((d.clone(), f.path.clone()));
            }
            idx.by_item
                .entry((krate.clone(), module.join("::")))
                .or_default()
                .push(self.index[&Symref::file(&f.path)]);
            for s in &f.symbols {
                let assoc = s
                    .parent
                    .as_ref()
                    .and_then(|p| self.index.get(p))
                    .is_some_and(|&p| {
                        matches!(self.graph[p].kind, SymbolKind::Impl | SymbolKind::Trait)
                    });
                idx.note_symbol(&krate, s, assoc);
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
                    idx.callable_names.insert(n.to_owned());
                    idx.by_name
                        .entry((krate.clone(), n.to_owned()))
                        .or_default()
                        .push(node);
                }
            }
        }
        idx.classify_uses(files);
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

    /// The declared type a method receiver has, when the syntax, the field table and return types prove it.
    ///
    /// `self` is the enclosing impl's type, a typed local is its annotation, `a.f` is the table type
    /// of field `f` of `a`'s type, a call is its callee's declared return type (only when the callee
    /// resolves to exactly one Must target) and `?`/`unwrap` open a `Result` or `Option`. Aliases and
    /// anything unproven give `None`.
    fn receiver_ty(&self, idx: &Index, caller: &Symref, r: &Receiver) -> Option<Ty> {
        let ty = self.receiver_ty_raw(idx, caller, r)?;
        (!idx.is_alias(&ty.file, &ty.head)).then_some(ty)
    }

    /// [`Self::receiver_ty`] without the final alias check (`Result` may be an alias that `?` still opens).
    fn receiver_ty_raw(&self, idx: &Index, caller: &Symref, r: &Receiver) -> Option<Ty> {
        let key = (caller.clone(), r.clone());
        // The lock is never held across the (recursive) computation; a race only repeats a pure result.
        if let Some(hit) = idx.memo_shard(caller).lock().expect("memo lock").get(&key) {
            return hit.clone();
        }
        let out = self.receiver_ty_uncached(idx, caller, r);
        idx.memo_shard(caller)
            .lock()
            .expect("memo lock")
            .insert(key, out.clone());
        out
    }

    /// [`Self::receiver_ty_raw`] without the memo.
    fn receiver_ty_uncached(&self, idx: &Index, caller: &Symref, r: &Receiver) -> Option<Ty> {
        let file = caller.path();
        let ty = match r {
            Receiver::SelfValue => Ty::plain(self.enclosing_impl_type(caller)?, file),
            Receiver::Typed(t) => Ty::plain(t.clone(), file),
            Receiver::Decl(shape) => Ty::from_shape(shape, file),
            Receiver::Field(base, field) => {
                let b = self.receiver_ty(idx, caller, base)?;
                let (krate, real) = self.type_home(idx, &b);
                match idx.field_type(&b, &krate, &real, field) {
                    Some(t) => t,
                    None if idx.is_std_type(&b) => {
                        Ty::from_shape(&stdtypes::ext_field(&b.head, field)?, &b.file)
                    }
                    None => return None,
                }
            }
            Receiver::Variant { path, field } => self.variant_field_ty(idx, caller, path, field)?,
            Receiver::Ret(call) => self.ret_ty(idx, caller, call)?,
            Receiver::Unwrap(inner) => {
                let t = self.receiver_ty_raw(idx, caller, inner)?;
                if !matches!(t.head.as_str(), "Result" | "Option")
                    || idx.opaque_aliases.contains(&t.head)
                {
                    return None;
                }
                match (t.arg, t.tuple) {
                    (Some(head), _) => {
                        let bound = t.bound.filter(|_| head == "Self");
                        Ty {
                            bound,
                            ..Ty::plain(head, &t.file)
                        }
                    }
                    (None, Some(elems)) => Ty {
                        tuple: Some(elems),
                        ..Ty::plain(stdtypes::TUPLE.to_owned(), &t.file)
                    },
                    (None, None) => return None,
                }
            }
            Receiver::Elem(inner, i) => {
                let t = self.receiver_ty_raw(idx, caller, inner)?;
                if t.head != stdtypes::TUPLE {
                    return None;
                }
                Ty::plain(t.tuple?.get(*i)?.clone()?, &t.file)
            }
            Receiver::Mapped { recv, result, kind } => {
                self.mapped_ty(idx, caller, recv, result, *kind)?
            }
            Receiver::Collected { shape, source } => {
                let t = self.std_ty(idx, caller, source)?;
                let item = stdtypes::item_of(&t.shape())?;
                Ty::from_shape(&stdtypes::collect_into(&shape.head, &item)?, &t.file)
            }
            Receiver::Item(inner) => {
                let t = self.std_ty(idx, caller, inner)?;
                Ty::from_shape(&stdtypes::item_of(&t.shape())?, &t.file)
            }
            Receiver::Index(inner) => {
                let t = self.std_ty(idx, caller, inner)?;
                Ty::from_shape(&stdtypes::index_of(&t.shape())?, &t.file)
            }
            Receiver::Slice(inner) => {
                let t = self.std_ty(idx, caller, inner)?;
                match t.head.as_str() {
                    "String" | "str" => Ty::plain("str".to_owned(), &t.file),
                    "Vec" | "[]" | "VecDeque" => Ty {
                        arg: t.arg,
                        tuple: t.tuple,
                        ..Ty::plain(stdtypes::SLICE.to_owned(), &t.file)
                    },
                    _ => return None,
                }
            }
            Receiver::Assoc(base, name) => {
                let b = self.receiver_ty(idx, caller, base)?;
                let (krate, real) = self.type_home(idx, &b);
                idx.field_type(&b, &krate, &real, name)?
            }
            Receiver::Unit(name) => {
                let t = Ty::plain(name.clone(), file);
                let (krate, real) = self.type_home(idx, &t);
                let key = (krate, real);
                if idx.struct_count.get(&key) != Some(&1) || idx.enums.contains(&key) {
                    return None;
                }
                t
            }
            Receiver::Bound(_) | Receiver::Tuple(_) | Receiver::Expr => return None,
        };
        Some(idx.canonical_ext(ty.dyn_normalized().with_split_path()))
    }

    /// The declared type of field `field` of the enum variant named by the pattern `path` (`Kind::A`, `Self::A`).
    fn variant_field_ty(
        &self,
        idx: &Index,
        caller: &Symref,
        path: &[String],
        field: &str,
    ) -> Option<Ty> {
        let file = caller.path();
        let (variant, owner) = path.split_last()?;
        let enum_ty = match owner {
            [] => return None,
            [only] if only == "Self" => Ty::plain(self.enclosing_impl_type(caller)?, file),
            _ => Ty::plain(owner.join("::"), file),
        };
        let b = enum_ty.with_split_path();
        if idx.is_alias(&b.file, &b.head) {
            return None;
        }
        let (krate, real) = self.type_home(idx, &b);
        idx.field_type(&b, &krate, &real, &format!("{variant}.{field}"))
    }

    /// The type of `recv.map(|x| body)` where `recv` is a standard iterator, `Option` or `Result` and `result` types `body`.
    fn mapped_ty(
        &self,
        idx: &Index,
        caller: &Symref,
        recv: &Receiver,
        result: &Receiver,
        kind: MapKind,
    ) -> Option<Ty> {
        let t = self.std_ty(idx, caller, recv)?;
        let r = self.receiver_ty(idx, caller, result)?;
        if r.bound.is_some() || !r.qual.is_empty() {
            return None;
        }
        let head = match (kind, t.head.as_str()) {
            (MapKind::Map | MapKind::FilterMap, stdtypes::ITER) => stdtypes::ITER,
            (MapKind::Map | MapKind::AndThen, "Option") => "Option",
            (MapKind::Map | MapKind::AndThen, "Result") => "Result",
            _ => return None,
        };
        let item = match kind {
            MapKind::Map => r.shape(),
            // The closure returns the `Option`/`Result` (or `Option` of the item) itself.
            MapKind::AndThen | MapKind::FilterMap => {
                if !matches!(r.head.as_str(), "Option" | "Result")
                    || idx.opaque_aliases.contains(&r.head)
                {
                    return None;
                }
                stdtypes::inner(&r.shape())?
            }
        };
        Some(Ty::from_shape(&stdtypes::wrap(head, &item), &r.file))
    }

    /// The type of `r` when it is a standard type this repository does not shadow (so the standard method tables apply).
    fn std_ty(&self, idx: &Index, caller: &Symref, r: &Receiver) -> Option<Ty> {
        let t = self.receiver_ty_raw(idx, caller, r)?;
        let real = idx.real_type_name(&t.file, &t.head);
        // `Result` and `Option` aliases keep the Ok/Some type first unless recorded as opaque.
        let alias = !matches!(real.as_str(), "Result" | "Option") && idx.is_alias(&t.file, &t.head);
        let std = t.qual.is_empty()
            && stdtypes::is_std_head(&t.head)
            && !idx.declared_types.contains(&real)
            && !alias
            && !idx.opaque_aliases.contains(&real);
        std.then_some(t)
    }

    /// The return type of a call whose callee is the standard library's, not looked up in the repository.
    ///
    /// A standard receiver's method (`v.iter()`, `m.get(..)`); `Clone::clone` returns `Self`;
    /// `ToString::to_string` returns `String` unless the repository declares a method of that name
    /// that could shadow it; and standard functions (`fs::read_to_string`, `Path::new`).
    fn known_ret_ty(&self, idx: &Index, caller: &Symref, call: &CallRef) -> Option<Ty> {
        // frob:ticket 01M3ZVQAA1DNM1BJ5TZG5B3CFR
        if let Some(recv) = &call.recv {
            if let Some(t) = self.std_ty(idx, caller, recv)
                && let Some(shape) = stdtypes::step(&t.shape(), &call.name, call.args)
            {
                return Some(Ty::from_shape(&shape, &t.file));
            }
            if call.args == 0 {
                if call.name == "clone"
                    && let Some(t) = self.receiver_ty(idx, caller, recv)
                    && t.bound.is_none()
                {
                    return Some(t);
                }
                if call.name == "to_string" && !idx.callable_names.contains("to_string") {
                    return Some(Ty::plain("String".to_owned(), caller.path()));
                }
            }
            return None;
        }
        let module = call.path.last()?;
        let shape = stdtypes::assoc_fn(module, &call.name)?;
        idx.is_std_path(caller.path(), &call.path)
            .then(|| Ty::from_shape(&shape, caller.path()))
    }

    /// `Type::from(x)` is `Type` whichever `From` impl it picks: the type of the one impl type among `nodes`.
    fn impl_owner_ty(&self, nodes: &[NodeIndex]) -> Option<Ty> {
        let from_impl = |n: NodeIndex| {
            self.graph[n].implements.as_deref().is_some_and(|t| {
                t.rsplit("::")
                    .next()
                    .is_some_and(|l| l.starts_with("From<"))
            })
        };
        if nodes.is_empty() || !nodes.iter().all(|&n| from_impl(n)) {
            return None;
        }
        let owners: BTreeSet<String> = nodes
            .iter()
            .filter_map(|&n| self.enclosing_impl_type(&self.graph[n].symref))
            .collect();
        let (Some(owner), 1) = (owners.first(), owners.len()) else {
            return None;
        };
        Some(Ty::plain(owner.clone(), self.graph[nodes[0]].symref.path()))
    }

    /// The declared return type of the one concrete callee that `call` resolves to.
    fn ret_ty(&self, idx: &Index, caller: &Symref, call: &CallRef) -> Option<Ty> {
        if let Some(t) = self.known_ret_ty(idx, caller, call) {
            return Some(t);
        }
        let q = Query {
            name: &call.name,
            qualifier: call.path.last().map(String::as_str),
            path: &call.path,
            bound: &call.bound,
            method: call.recv.is_some(),
            args: Some(call.args),
        };
        let outcome = self.resolve_site(idx, caller, &q, call.recv.as_ref(), LocalBinding::None);
        if call.name == "from"
            && call.recv.is_none()
            && let Outcome::Hit(nodes, _) = &outcome
            && let Some(t) = self.impl_owner_ty(nodes)
        {
            return Some(t);
        }
        let (n, bounds) = match outcome {
            Outcome::Hit(nodes, Status::Must) => {
                let [n] = nodes[..] else { return None };
                (n, None)
            }
            // A call through trait bounds: the trait's declaration says what comes back.
            Outcome::Dispatch(decl, _) => {
                let bounds = if call.bound.is_empty() {
                    self.receiver_bounds(idx, caller, call.recv.as_ref())?
                } else {
                    call.bound.clone()
                };
                (decl, Some(bounds))
            }
            _ => return None,
        };
        let rec = &self.graph[n];
        let ret = rec.signature.as_ref()?.ret.as_ref()?;
        // A trait declaration says what comes back unless it says `Self`, which only the implementing type knows.
        let says_self = [Some(&ret.head), ret.arg.as_ref(), ret.arg2.as_ref()]
            .into_iter()
            .flatten()
            .any(|h| h == "Self");
        if bounds.is_none() && self.is_trait_member(n) && says_self {
            return None;
        }
        let sub = |s: &str| match (s, &bounds) {
            ("Self", None) => self.enclosing_impl_type(&rec.symref),
            _ => Some(s.to_owned()),
        };
        let ty = Ty {
            tuple: ret.tuple.clone(),
            head: sub(&ret.head)?,
            arg: ret.arg.as_deref().and_then(sub),
            arg2: ret.arg2.as_deref().and_then(sub),
            bound: bounds,
            qual: Vec::new(),
            file: rec.symref.path().to_owned(),
        };
        Some(if ty.bound.is_none() {
            ty.dyn_normalized()
        } else {
            ty
        })
    }

    /// Resolves a call or value reference by name, imports and qualifier.
    fn resolve_site(
        &self,
        idx: &Index,
        caller: &Symref,
        q: &Query<'_>,
        receiver: Option<&Receiver>,
        local: LocalBinding,
    ) -> Outcome {
        let (name, qualifier, method) = (q.name, q.qualifier, q.method);
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
            return self.resolve_method(idx, caller, q, receiver, named);
        }
        if !q.bound.is_empty() {
            return self.resolve_bound_assoc(q, &named);
        }
        match qualifier {
            Some(qual) => {
                if let Some(o) = self.resolve_crate_path(idx, file, q) {
                    return o;
                }
                if let Some(o) = self.resolve_extern(idx, file, q) {
                    return o;
                }
                let o = self.resolve_qualified(caller, qual, named, uses);
                if matches!(o, Outcome::Gap(GapReason::Unbound))
                    && let Some(d) = self.derived_path_call(idx, caller, qual, name)
                {
                    return d;
                }
                o
            }
            None => self
                .resolve_extern(idx, file, q)
                .unwrap_or_else(|| self.resolve_bare(idx, &krate, file, name, named, uses)),
        }
    }

    /// `name` called on the type `ty` (declared once in crate `home`) that derives it rather than declaring it.
    ///
    /// A standard derive (`Clone`, `Default`, ..) generates code outside the repository: nothing to link and
    /// nothing unknown. A derive named like a repository trait that declares `name` reaches that declaration (Must).
    fn derived_call(
        &self,
        idx: &Index,
        caller: &Symref,
        home: &str,
        ty: &str,
        name: &str,
    ) -> Option<Outcome> {
        // frob:ticket 01M3ZVQAA1DNM1BJ5TZG5B3CFR
        let key = (home.to_owned(), ty.to_owned());
        if idx.struct_count.get(&key) != Some(&1) {
            return None;
        }
        let derives = idx.derives.get(&key)?;
        if derives
            .iter()
            .any(|d| stdtypes::std_derive_methods(d).contains(&name))
        {
            tracing::debug!(
                ty,
                name,
                "call generated by a standard derive: no callee to link"
            );
            return Some(Outcome::Local);
        }
        let decls: BTreeSet<NodeIndex> = idx
            .callables_in_reach(caller, name)
            .into_iter()
            .filter(|&n| {
                self.is_trait_member(n)
                    && self.graph[n]
                        .symref
                        .segments()
                        .len()
                        .checked_sub(2)
                        .is_some_and(|i| {
                            derives
                                .iter()
                                .any(|d| d == base_segment(&self.graph[n].symref.segments()[i]))
                        })
            })
            .collect();
        tracing::debug!(
            ty,
            name,
            declarations = decls.len(),
            "call through a repository derive"
        );
        match decls.len() {
            0 => None,
            1 => Some(Outcome::Hit(decls.into_iter().collect(), Status::Must)),
            _ => Some(Outcome::Hit(decls.into_iter().collect(), Status::May)),
        }
    }

    /// `Type::name(..)` where `Type` derives the trait that declares or generates `name` (`FrontmatterSchema::describe()`).
    fn derived_path_call(
        &self,
        idx: &Index,
        caller: &Symref,
        qual: &str,
        name: &str,
    ) -> Option<Outcome> {
        let written = if qual == "Self" {
            self.enclosing_impl_type(caller)?
        } else {
            qual.to_owned()
        };
        let t = Ty::plain(written, caller.path());
        if idx.is_alias(&t.file, &t.head) {
            return None;
        }
        let (home, real) = self.type_home(idx, &t);
        self.derived_call(idx, caller, &home, &real, name)
    }

    /// `x.name(..)`: the receiver's own methods when its type is proven, else every method that fits the call shape.
    fn resolve_method(
        &self,
        idx: &Index,
        caller: &Symref,
        q: &Query<'_>,
        receiver: Option<&Receiver>,
        named: Vec<NodeIndex>,
    ) -> Outcome {
        let fits = |n: NodeIndex| {
            let r = &self.graph[n];
            r.kind == SymbolKind::Method
                && r.signature
                    .as_ref()
                    .is_none_or(|s| s.accepts_method_call(q.args))
        };
        let parent_seg = |n: NodeIndex| {
            let segs = self.graph[n].symref.segments();
            segs.len()
                .checked_sub(2)
                .map(|i| base_segment(&segs[i]).to_owned())
        };
        if let Some(traits) = self.receiver_bounds(idx, caller, receiver) {
            return self.resolve_bound_method(&traits, &named, &fits, &parent_seg);
        }
        if let Some(ty) = receiver.and_then(|r| self.receiver_ty(idx, caller, r)) {
            let (home, t) = self.type_home(idx, &ty);
            let here = crate_and_module(caller.path()).0;
            // The type's methods live in its home crate; impls written in the caller's crate add trait impls.
            let pool: Vec<NodeIndex> = if home == here {
                named.clone()
            } else {
                let mut p = idx
                    .by_name
                    .get(&(home.clone(), q.name.to_owned()))
                    .cloned()
                    .unwrap_or_default();
                p.extend(
                    named
                        .iter()
                        .copied()
                        .filter(|&n| self.graph[n].implements.is_some()),
                );
                p
            };
            let mine: Vec<NodeIndex> = pool
                .iter()
                .copied()
                .filter(|&n| fits(n) && parent_seg(n).as_deref() == Some(t.as_str()))
                .collect();
            if let [one] = mine.as_slice() {
                let own_file = self.graph[*one].symref.path() == caller.path();
                let unique = idx
                    .struct_count
                    .get(&(home.clone(), t.clone()))
                    .is_none_or(|&c| c <= 1)
                    || (own_file && idx.declared_once_in(caller.path(), &home, &t));
                let sure = self.graph[*one].implements.is_none() && unique;
                return Outcome::Hit(mine, if sure { Status::Must } else { Status::May });
            }
            if !mine.is_empty() {
                return Outcome::Hit(mine, Status::May);
            }
            if !idx.deref_types.contains(&t)
                && let Some(o) = self.derived_call(idx, caller, &home, &t, q.name)
            {
                return o;
            }
            if !idx.deref_types.contains(&t) {
                // The type has no such method of its own: only trait-provided methods remain
                // (a trait declaration or default, or an impl for a type we cannot name).
                let cands: Vec<NodeIndex> = pool
                    .iter()
                    .copied()
                    .filter(|&n| {
                        fits(n)
                            && (self.is_trait_member(n)
                                || (self.graph[n].implements.is_some()
                                    && parent_seg(n)
                                        .is_none_or(|p| !idx.declared_types.contains(&p))))
                    })
                    .collect();
                return if cands.is_empty() {
                    Outcome::Gap(GapReason::Unbound)
                } else {
                    Outcome::Hit(cands, Status::May)
                };
            }
        }
        // Receiver type unknown: every method of that name that `x.m(args)` can call may be it.
        // frob:ticket 01M3ZVQA77ZEK9DXEN5Z0XMZEG
        // A dependency crate's method of that name is as possible as the caller's own (soundness).
        let here = crate_and_module(caller.path()).0;
        let linked = idx
            .file_crate
            .get(caller.path())
            .and_then(|o| idx.reach.get(o))
            .into_iter()
            .flatten()
            .filter(|d| **d != here)
            .filter_map(|d| idx.by_name.get(&(d.clone(), q.name.to_owned())))
            .flatten()
            .copied();
        let mut cands: Vec<NodeIndex> = named
            .into_iter()
            .chain(linked)
            .filter(|&n| fits(n))
            .collect();
        cands.sort();
        cands.dedup();
        if cands.is_empty() {
            Outcome::Gap(GapReason::Unbound)
        } else {
            Outcome::Hit(cands, Status::May)
        }
    }

    /// `G::name(..)` where `G` is a generic bounded by traits: the trait's function (Must) and its implementations (May).
    fn resolve_bound_assoc(&self, q: &Query<'_>, named: &[NodeIndex]) -> Outcome {
        let fits = |n: NodeIndex| self.graph[n].kind == SymbolKind::Method;
        let parent_seg = |n: NodeIndex| {
            let segs = self.graph[n].symref.segments();
            segs.len()
                .checked_sub(2)
                .map(|i| base_segment(&segs[i]).to_owned())
        };
        self.resolve_bound_method(q.bound, named, &fits, &parent_seg)
    }

    /// The trait names bounding a receiver: its declared bounds, or the enclosing trait for `self` in a trait body.
    fn receiver_bounds(
        &self,
        idx: &Index,
        caller: &Symref,
        receiver: Option<&Receiver>,
    ) -> Option<Vec<String>> {
        match receiver? {
            Receiver::Bound(t) => Some(t.clone()),
            Receiver::SelfValue => {
                let parent = self.parent_of(*self.index.get(caller)?)?;
                if self.graph[parent].kind != SymbolKind::Trait {
                    return None;
                }
                let segs = self.graph[parent].symref.segments();
                segs.last().map(|t| vec![base_segment(t).to_owned()])
            }
            r => {
                let ty = self.receiver_ty_raw(idx, caller, r)?;
                ty.bound.filter(|_| ty.head == "Self")
            }
        }
    }

    /// `x.name(..)` where `x` is known only by trait bounds: the trait's method (Must) and its implementations (May).
    ///
    /// Inherent methods of concrete types cannot be called on such a receiver. A method none of the
    /// bound traits declares comes from a supertrait, an external trait or a blanket extension: May.
    fn resolve_bound_method(
        &self,
        traits: &[String],
        named: &[NodeIndex],
        fits: &dyn Fn(NodeIndex) -> bool,
        parent_seg: &dyn Fn(NodeIndex) -> Option<String>,
    ) -> Outcome {
        let in_bounds = |name: &str| traits.iter().any(|t| t == name);
        let decls: Vec<NodeIndex> = named
            .iter()
            .copied()
            .filter(|&n| {
                fits(n) && self.is_trait_member(n) && parent_seg(n).is_some_and(|p| in_bounds(&p))
            })
            .collect();
        let implements_bound = |n: NodeIndex| {
            self.graph[n].implements.as_deref().is_some_and(|tr| {
                let tr = tr.split('<').next().unwrap_or(tr);
                tr.rsplit("::").next().is_some_and(in_bounds)
            })
        };
        let impls: Vec<NodeIndex> = named
            .iter()
            .copied()
            .filter(|&n| fits(n) && implements_bound(n))
            .collect();
        match decls.as_slice() {
            [one] => Outcome::Dispatch(*one, impls),
            [] => {
                let broad: Vec<NodeIndex> = named
                    .iter()
                    .copied()
                    .filter(|&n| {
                        fits(n)
                            && (self.is_trait_member(n)
                                || self.graph[n].implements.is_some()
                                || parent_seg(n).is_some_and(|p| p.starts_with("dyn")))
                    })
                    .collect();
                if broad.is_empty() {
                    Outcome::Gap(GapReason::Unbound)
                } else {
                    Outcome::Hit(broad, Status::May)
                }
            }
            _ => Outcome::Hit([decls, impls].concat(), Status::May),
        }
    }

    /// The crate directory declaring the type `written` in `file`, and its name there.
    ///
    /// A name imported from another crate follows `pub use` re-exports to the crate that declares it.
    fn type_home(&self, idx: &Index, ty: &Ty) -> (String, String) {
        let (file, written) = (ty.file.as_str(), ty.head.as_str());
        let real = idx.real_type_name(file, written);
        let here = crate_and_module(file).0;
        if ty.qual.is_empty() && idx.struct_count.contains_key(&(here.clone(), real.clone())) {
            return (here, real);
        }
        let named_from = match ty.qual.split_first() {
            None => idx.explicit_extern(file, written),
            Some((head, rest)) => idx
                .extern_dir(file, head)
                .map(|dir| (dir, rest.iter().cloned().chain([ty.head.clone()]).collect())),
        };
        let Some((dir, within)) = named_from else {
            return (here, real);
        };
        let homes: BTreeSet<(String, String)> =
            idx.canonical_paths(&dir, &within, 0)
                .into_iter()
                .filter(|key| {
                    idx.by_item.get(key).into_iter().flatten().any(|&n| {
                        matches!(self.graph[n].kind, SymbolKind::Struct | SymbolKind::Enum)
                    })
                })
                .map(|(d, path)| {
                    let name = path.rsplit("::").next().unwrap_or(&path).to_owned();
                    (d, name)
                })
                .collect();
        let mut it = homes.into_iter();
        match (it.next(), it.next()) {
            (Some(one), None) => one,
            _ => (dir, within.last().cloned().unwrap_or(real)),
        }
    }

    /// True when `n` is declared directly inside a trait (a declaration or default method).
    fn is_trait_member(&self, n: NodeIndex) -> bool {
        self.parent_of(n)
            .is_some_and(|p| self.graph[p].kind == SymbolKind::Trait)
    }

    /// The (callee parent path, callee name) candidates of a path call through extern crates.
    ///
    /// Also whether the head is certain (explicit import or crate name, or the file's only glob)
    /// and whether it came from an explicit import or crate name rather than a glob.
    #[allow(
        clippy::type_complexity,
        reason = "a private three-part result used once"
    )]
    fn extern_candidates(
        idx: &Index,
        file: &str,
        q: &Query<'_>,
    ) -> Option<(Vec<(Vec<String>, String)>, bool, bool)> {
        let owner = idx.file_crate.get(file)?;
        let externs = idx.externs.get(owner)?;
        let ext_uses = idx.ext_uses.get(file).map_or(&[][..], Vec::as_slice);
        let segs = |t: &str| t.split("::").map(str::to_owned).collect::<Vec<_>>();
        // Each candidate is (path of the callee's parent, callee name).
        let direct: Option<(Vec<String>, String)> = match q.path.first() {
            None => ext_uses
                .iter()
                .find(|u| u.local == q.name && !u.target.ends_with("::*"))
                .and_then(|u| {
                    let mut v = segs(&u.target);
                    let name = v.pop()?;
                    Some((v, name))
                }),
            Some(head) => ext_uses
                .iter()
                .find(|u| u.local == *head && !u.target.ends_with("::*"))
                .map(|u| {
                    let mut v = segs(&u.target);
                    v.extend(q.path[1..].iter().cloned());
                    (v, q.name.to_owned())
                })
                .or_else(|| {
                    externs
                        .iter()
                        .any(|(n, _)| n == head)
                        .then(|| (q.path.to_vec(), q.name.to_owned()))
                }),
        };
        let explicit = direct.is_some();
        let (cands, sure_head): (Vec<(Vec<String>, String)>, bool) = if let Some(c) = direct {
            (vec![c], true)
        } else {
            let globs: Vec<(Vec<String>, String)> = ext_uses
                .iter()
                .filter_map(|u| u.target.strip_suffix("::*"))
                .map(|t| {
                    let mut v = segs(t);
                    v.extend(q.path.iter().cloned());
                    (v, q.name.to_owned())
                })
                .collect();
            let all_globs = idx
                .uses
                .get(file)
                .into_iter()
                .flatten()
                .chain(ext_uses.iter())
                .filter(|u| u.target.ends_with("::*"))
                .count();
            let sole = all_globs == 1 && globs.len() == 1;
            (globs, sole)
        };
        Some((cands, sure_head, explicit))
    }

    /// `Q::name(..)` where `Q` is reached through an extern crate: resolved through `use` imports and `pub use` re-exports.
    ///
    /// `None` when the path does not start at an extern crate (the caller falls back to in-crate
    /// resolution). A single concrete callee is Must; a trait method, an ambiguity or a glob import
    /// that could be shadowed stays May; no such item anywhere is a gap.
    fn resolve_extern(&self, idx: &Index, file: &str, q: &Query<'_>) -> Option<Outcome> {
        let (cands, sure_head, explicit) = Self::extern_candidates(idx, file, q)?;
        let externs = idx.externs.get(idx.file_crate.get(file)?)?;
        let mut found: Vec<NodeIndex> = Vec::new();
        let mut any_extern = false;
        for (parent, name) in &cands {
            let Some(dir) = parent
                .first()
                .and_then(|h| externs.iter().find(|(n, _)| n == h))
                .map(|(_, d)| d.clone())
            else {
                continue;
            };
            any_extern = true;
            let rel = &parent[1..];
            let mut keys: Vec<(String, String)> = idx
                .canonical_paths(&dir, rel, 0)
                .into_iter()
                .map(|(d, c)| {
                    if c.is_empty() {
                        (d, name.clone())
                    } else {
                        (d, format!("{c}::{name}"))
                    }
                })
                .collect();
            let mut full = rel.to_vec();
            full.push(name.clone());
            keys.extend(idx.canonical_paths(&dir, &full, 0));
            keys.sort();
            keys.dedup();
            for key in keys {
                found.extend(
                    idx.by_item
                        .get(&key)
                        .into_iter()
                        .flatten()
                        .copied()
                        .filter(|&n| {
                            matches!(
                                self.graph[n].kind,
                                SymbolKind::Function | SymbolKind::Method
                            )
                        }),
                );
            }
        }
        if !any_extern || (found.is_empty() && !explicit) {
            return None;
        }
        found.sort();
        found.dedup();
        tracing::debug!(
            file,
            name = q.name,
            candidates = found.len(),
            "cross-crate call resolved"
        );
        Some(match found.as_slice() {
            [] => Outcome::Gap(GapReason::Unbound),
            [one] => {
                let r = &self.graph[*one];
                let concrete = !self.is_trait_member(*one)
                    && (r.kind == SymbolKind::Function || r.implements.is_none());
                let status = if concrete && sure_head {
                    Status::Must
                } else {
                    Status::May
                };
                Outcome::Hit(found, status)
            }
            _ => Outcome::Hit(found, Status::May),
        })
    }

    /// `crate::a::name(..)` and `crate::Type::name(..)` in a library or binary source file: the items at that
    /// absolute path of the file's own crate (following `pub use` re-exports); `None` when nothing is found there.
    ///
    /// `self::` and `super::` are not resolved: an inline `mod` changes what they mean and the file alone cannot say.
    fn resolve_crate_path(&self, idx: &Index, file: &str, q: &Query<'_>) -> Option<Outcome> {
        let [first, rest @ ..] = q.path else {
            return None;
        };
        let in_src = file.starts_with("src/") || file.contains("/src/");
        if first != "crate" || !in_src {
            return None;
        }
        let krate = crate_and_module(file).0;
        let mut full = rest.to_vec();
        full.push(q.name.to_owned());
        let mut found: Vec<NodeIndex> = idx
            .canonical_paths(&krate, &full, 0)
            .into_iter()
            .filter_map(|key| idx.by_item.get(&key))
            .flatten()
            .copied()
            .filter(|&n| {
                matches!(
                    self.graph[n].kind,
                    SymbolKind::Function | SymbolKind::Method
                )
            })
            .collect();
        found.sort();
        found.dedup();
        tracing::debug!(
            file,
            name = q.name,
            candidates = found.len(),
            "crate-relative path call"
        );
        match found.as_slice() {
            [] => None,
            [one] => {
                let r = &self.graph[*one];
                let concrete = !self.is_trait_member(*one)
                    && (r.kind == SymbolKind::Function || r.implements.is_none());
                let status = if concrete { Status::Must } else { Status::May };
                Some(Outcome::Hit(found, status))
            }
            _ => Some(Outcome::Hit(found, Status::May)),
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

    // frob:ticket 01M421PY49MQ5WX8RGQ36ZXTMR
    /// Resolves and records every call site per file in parallel (read-only), then merges the results in call order.
    ///
    /// Resolution reads only the graph's `Contains` edges and the index, never what the merge
    /// adds, so the result equals a sequential pass; `par_iter().map().collect()` keeps file and
    /// call order, which keeps the merged edges deterministic at any thread count.
    fn link_calls(&mut self, files: &[FileSymbols], idx: &Index) {
        let t0 = std::time::Instant::now();
        let all: Vec<&CallSite> = files.iter().flat_map(|f| f.calls.iter()).collect();
        let sinks: Vec<CallSink> = all
            .par_chunks(CALL_CHUNK)
            .map(|chunk| {
                let mut sink = CallSink::default();
                for &call in chunk {
                    if is_python(call.caller.path()) {
                        let outcome = self.resolve_python(&idx.py, call);
                        self.record_call(&mut sink, call, outcome, None, false);
                        continue;
                    }
                    let outcome = self.resolve_site(
                        idx,
                        &call.caller,
                        &Query {
                            name: &call.callee,
                            qualifier: call.qualifier.as_deref(),
                            path: &call.qual_path,
                            bound: &call.bound,
                            method: call.method,
                            args: call.args,
                        },
                        call.receiver.as_ref(),
                        call.local,
                    );
                    let qualifier = self.call_qualifier(idx, call);
                    let capped = call.in_macro
                        && call
                            .macro_exact
                            .as_deref()
                            .is_none_or(|m| idx.declared_macros.contains(m));
                    self.record_call(&mut sink, call, outcome, qualifier, capped);
                }
                sink
            })
            .collect();
        tracing::debug!(ms = t0.elapsed().as_millis(), "calls resolved");
        for sink in sinks {
            for (a, b, kind, status) in sink.links {
                self.link(a, b, kind, status);
            }
            self.calls.extend(sink.calls);
            self.status_edges.extend(sink.status_edges);
            self.poisoned.extend(sink.poisoned);
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
    fn call_qualifier(&self, idx: &Index, call: &CallSite) -> Option<CallQualifier> {
        if call.opaque_qualifier || call.callee.is_empty() {
            return None;
        }
        if call.method {
            let unknown = CallQualifier::Receiver { args: call.args };
            let typed = call
                .receiver
                .as_ref()
                .and_then(|r| self.receiver_ty(idx, &call.caller, r))
                .filter(|t| t.bound.is_none())
                .map(|t| idx.real_type_name(&t.file, &t.head))
                .filter(|t| !idx.deref_types.contains(t));
            return Some(match (&call.receiver, typed) {
                (Some(Receiver::SelfValue), Some(t)) => CallQualifier::SelfType(t),
                (Some(_), Some(t)) => CallQualifier::Typed(t),
                _ => unknown,
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
        (!idx.is_alias(call.caller.path(), &real)).then_some(CallQualifier::Path(real))
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
            CallQualifier::Receiver { args } => {
                if rec.kind == SymbolKind::Method
                    && rec
                        .signature
                        .as_ref()
                        .is_none_or(|s| s.accepts_method_call(*args))
                {
                    Admit::Maybe
                } else {
                    Admit::No
                }
            }
        }
    }

    fn record_call(
        &self,
        sink: &mut CallSink,
        call: &CallSite,
        outcome: Outcome,
        qualifier: Option<CallQualifier>,
        capped: bool,
    ) {
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
                sink.calls.push(CallEdge::Unresolved {
                    caller: caller.clone(),
                    name: name.clone(),
                    qualifier: qualifier.clone(),
                });
                sink.status_edges.push(StatusEdge {
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
                    sink.poisoned.push(a);
                }
            }
            Outcome::Hit(nodes, status) => self.record_hit(sink, call, &nodes, status, capped),
            Outcome::Dispatch(decl, impls) => {
                self.record_hit(sink, call, &[decl], Status::Must, capped);
                if !impls.is_empty() {
                    self.record_hit(sink, call, &impls, Status::May, capped);
                }
            }
        }
    }

    /// Records the call edges from `call` to `nodes`, all with `status` (May when `capped`).
    fn record_hit(
        &self,
        sink: &mut CallSink,
        call: &CallSite,
        nodes: &[NodeIndex],
        status: Status,
        capped: bool,
    ) {
        let caller = &call.caller;
        let from = self.index.get(caller).copied();
        let status = if capped {
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
        if let Some(a) = from {
            for &n in nodes {
                sink.links.push((a, n, EdgeKind::Calls, status));
                sink.links.push((a, n, EdgeKind::References, status));
            }
        }
        for to in &found {
            sink.status_edges.push(StatusEdge {
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
        sink.calls.push(match (status, found.len()) {
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
        if is_python(r.from.path()) {
            let (Some(nodes), Some(&from)) = (
                self.resolve_python_value(&idx.py, r),
                self.index.get(&r.from),
            ) else {
                return;
            };
            self.record_value_edges(r, from, nodes);
            return;
        }
        let outcome = self.resolve_site(
            idx,
            &r.from,
            &Query {
                name: &r.name,
                qualifier: r.qualifier.as_deref(),
                path: &[],
                bound: &[],
                method: false,
                args: None,
            },
            None,
            LocalBinding::None,
        );
        let (Outcome::Hit(nodes, _), Some(&from)) = (outcome, self.index.get(&r.from)) else {
            return;
        };
        self.record_value_edges(r, from, nodes);
    }

    /// Records the May reference edges of the value reference `r` (in `from`) to `nodes`.
    fn record_value_edges(&mut self, r: &RefSite, from: NodeIndex, nodes: Vec<NodeIndex>) {
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
