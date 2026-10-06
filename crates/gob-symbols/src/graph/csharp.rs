//! C# call and import resolution for the symbol graph.
//!
//! C# names resolve through namespaces, enclosing types and `using` directives. A call is Must
//! when the syntax and the usings prove one target: an unqualified name found in an enclosing
//! type, namespace or `using static`, a `Type.Member` chain, `this.M`, an object creation of a
//! repository type, or a receiver of a syntactically evident type. Several overloads of a name
//! are May. A call on a receiver whose type is not known (`expr.M()`, a `var` local, a field of
//! unknown type), a name nothing in the repository defines and a member inherited from an
//! external base type are Unknown edges, never clean. A call whose callee is a known .NET core
//! library type (`Console`, `string`, `List`) reached through `using System...` is external and
//! clean: it leaves no edge. Implicit usings declared in a `.csproj` are not read here, so a name
//! they would bring into scope stays unresolved until the project model supplies them.

// frob:ticket 01M44YQTCDPH87ASRMSJEN2C8Q

use std::collections::{HashMap, HashSet};

use petgraph::graph::NodeIndex;

use super::{GapReason, Outcome, SymbolGraph, base_segment};
use crate::csharp::{
    EXTENSION_PREFIX, Q_BASE, Q_BASE_INIT, Q_NEW, Q_THIS_INIT, USE_NAMESPACE, USE_STATIC,
};
use crate::model::{CallSite, FileSymbols, LocalBinding, Receiver, SymbolKind};
use crate::qualifier::CallQualifier;
use crate::stdtypes;
use gob_ir::Status;

/// Deepest chain of base types followed when looking a member up.
const MAX_BASES: usize = 8;

/// True when `path` is a C# source file.
pub(super) fn is_csharp(path: &str) -> bool {
    crate::csharp::is_csharp_path(path)
}

/// One `using` directive as the resolver sees it.
#[derive(Debug, Clone)]
struct CsUse {
    local: String,
    target: String,
    /// The namespace segments the directive sits in; empty for file level and `global using`.
    container: Vec<String>,
}

/// An extension method: the method, the type of its `this` parameter and its namespace.
#[derive(Debug, Clone)]
struct Ext {
    node: NodeIndex,
    recv: String,
    ns: String,
}

/// Lookup tables over the repository's C# files.
#[derive(Debug, Default)]
pub(super) struct CsIndex {
    /// Dotted name (overload and partial suffixes removed) to every unit so named.
    by_fqn: HashMap<String, Vec<NodeIndex>>,
    /// Unit to its dotted name.
    fqn: HashMap<NodeIndex, String>,
    /// Unit to its segments, suffixes removed.
    segs: HashMap<NodeIndex, Vec<String>>,
    /// Unit to the file declaring it.
    file_of: HashMap<NodeIndex, String>,
    /// Type unit to its written base types, generic arguments removed.
    bases: HashMap<NodeIndex, Vec<String>>,
    /// File to its `using` directives.
    uses: HashMap<String, Vec<CsUse>>,
    /// Every `global using`.
    globals: Vec<CsUse>,
    /// (owner dotted name, field or property) to its declared type head.
    field_types: HashMap<(String, String), String>,
    /// Extension method name to its definitions.
    ext: HashMap<String, Vec<Ext>>,
    /// C# file path to its file node.
    file_nodes: HashMap<String, NodeIndex>,
}

/// True for the unit kinds that are types.
fn is_type(k: SymbolKind) -> bool {
    matches!(
        k,
        SymbolKind::Class
            | SymbolKind::Struct
            | SymbolKind::Enum
            | SymbolKind::Interface
            | SymbolKind::Record
            | SymbolKind::Delegate
    )
}

/// True for the unit kinds a call can target.
fn is_callable(k: SymbolKind) -> bool {
    matches!(k, SymbolKind::Method | SymbolKind::Function)
}

/// True for the kinds a `new T(..)` constructs.
fn is_constructible(k: SymbolKind) -> bool {
    matches!(
        k,
        SymbolKind::Class | SymbolKind::Struct | SymbolKind::Record
    )
}

/// How a name resolved.
enum Name {
    /// The repository units it names.
    Repo(Vec<NodeIndex>),
    /// A known .NET core library type or namespace: external and clean.
    Bcl,
    /// Nothing in the repository or the known library defines it.
    Missing,
}

/// The tail of a hierarchy member search.
struct Members {
    nodes: Vec<NodeIndex>,
    /// A base type outside the repository could still provide the member.
    external_base: bool,
}

impl CsIndex {
    /// Indexes the C# files in `files` against the node table of `g`.
    pub(super) fn build(g: &SymbolGraph, files: &[FileSymbols]) -> Self {
        let mut ix = Self::default();
        for f in files.iter().filter(|f| is_csharp(&f.path)) {
            if let Some(&n) = g.index.get(&crate::symref::Symref::file(&f.path)) {
                ix.file_nodes.insert(f.path.clone(), n);
            }
            let uses: Vec<CsUse> = f
                .uses
                .iter()
                .map(|u| CsUse {
                    local: u.local.clone(),
                    target: u.target.clone(),
                    container: u
                        .container
                        .as_ref()
                        .map(|c| {
                            c.segments()
                                .iter()
                                .map(|s| base_segment(s).to_owned())
                                .collect()
                        })
                        .unwrap_or_default(),
                })
                .collect();
            for (u, raw) in uses.iter().zip(&f.uses) {
                if raw.public {
                    ix.globals.push(u.clone());
                }
            }
            ix.uses.insert(f.path.clone(), uses);
            for (s, e) in f.symbols.iter().zip(&f.extras) {
                let Some(&node) = g.index.get(&s.symref) else {
                    continue;
                };
                let segs: Vec<String> = s
                    .symref
                    .segments()
                    .iter()
                    .map(|g| base_segment(g).to_owned())
                    .collect();
                let key = segs.join(".");
                ix.by_fqn.entry(key.clone()).or_default().push(node);
                ix.fqn.insert(node, key.clone());
                ix.file_of.insert(node, f.path.clone());
                if is_type(s.kind) {
                    let bases = e.facts.bases.iter().map(|b| strip_generics(b)).collect();
                    ix.bases.insert(node, bases);
                }
                for m in &e.facts.modifiers {
                    if let Some(recv) = m.strip_prefix(EXTENSION_PREFIX)
                        && let Some(name) = segs.last()
                    {
                        let ns = segs[..segs.len().saturating_sub(2)].join(".");
                        ix.ext.entry(name.clone()).or_default().push(Ext {
                            node,
                            recv: recv.to_owned(),
                            ns,
                        });
                    }
                }
                ix.segs.insert(node, segs);
            }
            for d in &f.fields {
                ix.field_types
                    .insert((d.owner.clone(), d.field.clone()), d.ty.head.clone());
            }
        }
        tracing::debug!(
            files = ix.file_nodes.len(),
            names = ix.by_fqn.len(),
            extensions = ix.ext.len(),
            "csharp index built"
        );
        ix
    }

    /// The directives of `file` in force at a unit with segments `segs`, `global using` included.
    fn scope_uses<'a>(&'a self, file: &str, segs: &[String]) -> impl Iterator<Item = &'a CsUse> {
        let segs = segs.to_vec();
        self.uses
            .get(file)
            .into_iter()
            .flatten()
            .filter(move |u| segs.starts_with(&u.container))
            .chain(&self.globals)
    }

    /// True when some directive in force imports a .NET framework namespace.
    fn imports_framework(&self, file: &str, segs: &[String]) -> bool {
        self.scope_uses(file, segs).any(|u| {
            u.target
                .split('.')
                .next()
                .is_some_and(stdtypes::is_dotnet_namespace_root)
        })
    }

    /// The units named `name` (any of `kinds`) directly inside the repository unit named `owner`.
    fn child(
        &self,
        owner: &str,
        name: &str,
        want: &dyn Fn(SymbolKind) -> bool,
        g: &SymbolGraph,
    ) -> Vec<NodeIndex> {
        let key = if owner.is_empty() {
            name.to_owned()
        } else {
            format!("{owner}.{name}")
        };
        self.by_fqn
            .get(&key)
            .into_iter()
            .flatten()
            .copied()
            .filter(|&n| want(g.graph[n].kind))
            .collect()
    }

    /// The namespace prefixes of `segs` that name a namespace, longest first, then the global namespace.
    fn prefixes(segs: &[String]) -> impl Iterator<Item = String> + '_ {
        (0..=segs.len()).rev().map(|i| segs[..i].join("."))
    }
}

impl SymbolGraph {
    /// The units named `name` (matching `want`) in the type `t` or the repository base types it inherits from.
    fn cs_hierarchy_member(
        &self,
        cs: &CsIndex,
        t: NodeIndex,
        name: &str,
        want: &dyn Fn(SymbolKind) -> bool,
        depth: usize,
    ) -> Members {
        let owner = cs.fqn.get(&t).cloned().unwrap_or_default();
        let own = cs.child(&owner, name, want, self);
        if !own.is_empty() {
            return Members {
                nodes: own,
                external_base: false,
            };
        }
        let mut out = Members {
            nodes: Vec::new(),
            external_base: false,
        };
        if depth >= MAX_BASES {
            out.external_base = true;
            return out;
        }
        let file = cs.file_of.get(&t).map_or("", String::as_str);
        let segs = cs.segs.get(&t).cloned().unwrap_or_default();
        for b in cs.bases.get(&t).into_iter().flatten() {
            let found = self.cs_type_text(cs, file, &segs, b);
            let found: Vec<NodeIndex> = found
                .into_iter()
                .filter(|&n| is_type(self.graph[n].kind) && n != t)
                .collect();
            if found.is_empty() {
                out.external_base = true;
                continue;
            }
            for n in found {
                let m = self.cs_hierarchy_member(cs, n, name, want, depth + 1);
                out.nodes.extend(m.nodes);
                out.external_base |= m.external_base;
            }
        }
        out.nodes.sort();
        out.nodes.dedup();
        out
    }

    /// The repository type units a written type name (`Base`, `Ns.Base`) names from the scope `segs` of `file`.
    fn cs_type_text(
        &self,
        cs: &CsIndex,
        file: &str,
        segs: &[String],
        text: &str,
    ) -> Vec<NodeIndex> {
        let parts: Vec<&str> = text.split('.').filter(|p| !p.is_empty()).collect();
        let Some((head, rest)) = parts.split_first() else {
            return Vec::new();
        };
        let Name::Repo(mut cur) = self.cs_name(cs, file, segs, head, &|_| true, false) else {
            return Vec::new();
        };
        for seg in rest {
            cur = cur
                .iter()
                .flat_map(|&n| self.cs_members(cs, n, seg, &|_| true).nodes)
                .collect();
        }
        cur.retain(|&n| is_type(self.graph[n].kind));
        cur
    }

    /// The members named `name` of the unit `n`: a namespace's types, a type's members and inherited members.
    fn cs_members(
        &self,
        cs: &CsIndex,
        n: NodeIndex,
        name: &str,
        want: &dyn Fn(SymbolKind) -> bool,
    ) -> Members {
        let kind = self.graph[n].kind;
        if kind == SymbolKind::Namespace {
            let owner = cs.fqn.get(&n).cloned().unwrap_or_default();
            return Members {
                nodes: cs.child(&owner, name, want, self),
                external_base: false,
            };
        }
        if is_type(kind) {
            return self.cs_hierarchy_member(cs, n, name, want, 0);
        }
        Members {
            nodes: Vec::new(),
            external_base: false,
        }
    }

    /// Resolves the simple name `name` written in the scope `segs` of `file`.
    fn cs_name(
        &self,
        cs: &CsIndex,
        file: &str,
        segs: &[String],
        name: &str,
        want: &dyn Fn(SymbolKind) -> bool,
        inherit: bool,
    ) -> Name {
        // Enclosing units, innermost first: a type's members (inherited ones too), a namespace's types.
        for i in (0..=segs.len()).rev() {
            let owner = segs[..i].join(".");
            let direct = cs.child(&owner, name, want, self);
            if !direct.is_empty() {
                return Name::Repo(direct);
            }
            for &t in cs.by_fqn.get(&owner).into_iter().flatten() {
                if inherit && is_type(self.graph[t].kind) {
                    let m = self.cs_hierarchy_member(cs, t, name, want, 0);
                    if !m.nodes.is_empty() {
                        return Name::Repo(m.nodes);
                    }
                }
            }
        }
        let mut found: Vec<NodeIndex> = Vec::new();
        let mut external = false;
        for u in cs.scope_uses(file, segs) {
            if u.local == USE_NAMESPACE {
                for owner in CsIndex::prefixes(&segs[..segs.len().min(u.container.len())])
                    .map(|p| {
                        if p.is_empty() {
                            u.target.clone()
                        } else {
                            format!("{p}.{}", u.target)
                        }
                    })
                    .chain([u.target.clone()])
                {
                    found.extend(cs.child(&owner, name, want, self));
                }
            } else if u.local == USE_STATIC {
                for t in self.cs_type_text(cs, file, segs, &u.target) {
                    found.extend(self.cs_members(cs, t, name, want).nodes);
                }
            } else if u.local == name {
                let targets = self.cs_type_text(cs, file, segs, &u.target);
                if targets.is_empty() {
                    external = true;
                }
                found.extend(targets);
            }
        }
        found.sort();
        found.dedup();
        if !found.is_empty() {
            return Name::Repo(found);
        }
        if external {
            return Name::Missing;
        }
        if stdtypes::is_dotnet_keyword_type(name)
            || stdtypes::is_dotnet_namespace_root(name)
            || (stdtypes::is_dotnet_core_type(name) && cs.imports_framework(file, segs))
        {
            return Name::Bcl;
        }
        Name::Missing
    }

    /// The nearest type unit enclosing (or being) `segs` in the repository.
    fn cs_enclosing_type(&self, cs: &CsIndex, segs: &[String]) -> Option<NodeIndex> {
        (1..=segs.len()).rev().find_map(|i| {
            cs.by_fqn
                .get(&segs[..i].join("."))?
                .iter()
                .copied()
                .find(|&n| is_type(self.graph[n].kind))
        })
    }

    /// The Must/May status of a candidate set.
    fn cs_status(nodes: &[NodeIndex]) -> Status {
        if nodes.len() == 1 {
            Status::Must
        } else {
            Status::May
        }
    }

    /// The extension methods named `name` visible from `segs` whose receiver type matches `recv`.
    fn cs_extensions(cs: &CsIndex, file: &str, segs: &[String], name: &str, recv: &str) -> Outcome {
        let in_scope = |ns: &str| {
            ns.is_empty()
                || CsIndex::prefixes(segs).any(|p| p == ns)
                || cs
                    .scope_uses(file, segs)
                    .any(|u| u.local == USE_NAMESPACE && u.target == ns)
        };
        let hits: Vec<&Ext> = cs
            .ext
            .get(name)
            .into_iter()
            .flatten()
            .filter(|e| in_scope(&e.ns))
            .collect();
        if hits.is_empty() {
            return Outcome::Gap(GapReason::Unbound);
        }
        let exact: Vec<NodeIndex> = hits
            .iter()
            .filter(|e| e.recv == recv)
            .map(|e| e.node)
            .collect();
        if exact.is_empty() {
            return Outcome::Hit(hits.iter().map(|e| e.node).collect(), Status::May);
        }
        let status = Self::cs_status(&exact);
        Outcome::Hit(exact, status)
    }

    /// Resolves a call on a receiver of the evident type `ty`.
    fn cs_typed(&self, cs: &CsIndex, call: &CallSite, segs: &[String], ty: &str) -> Outcome {
        let file = call.caller.path();
        let found = self.cs_name(cs, file, segs, ty, &is_type, false);
        match found {
            Name::Repo(types) => {
                let mut nodes = Vec::new();
                let mut external = false;
                for t in types.into_iter().filter(|&t| is_type(self.graph[t].kind)) {
                    let m = self.cs_hierarchy_member(cs, t, &call.callee, &is_callable, 0);
                    nodes.extend(m.nodes);
                    external |= m.external_base;
                }
                nodes.sort();
                nodes.dedup();
                if !nodes.is_empty() {
                    let status = Self::cs_status(&nodes);
                    return Outcome::Hit(nodes, status);
                }
                match Self::cs_extensions(cs, file, segs, &call.callee, ty) {
                    Outcome::Gap(_) if !external => Outcome::Gap(GapReason::Unbound),
                    other => other,
                }
            }
            Name::Bcl => match Self::cs_extensions(cs, file, segs, &call.callee, ty) {
                Outcome::Gap(_) => Outcome::Local,
                hit => hit,
            },
            Name::Missing => match Self::cs_extensions(cs, file, segs, &call.callee, ty) {
                Outcome::Gap(g) => Outcome::Gap(g),
                hit => hit,
            },
        }
    }

    /// Resolves `new T(..)`: the constructors of `T`, or `T` itself when it declares none.
    fn cs_construct(&self, cs: &CsIndex, call: &CallSite, segs: &[String]) -> Outcome {
        let file = call.caller.path();
        let mut written: Vec<&str> = call.qual_path.iter().map(String::as_str).collect();
        written.push(&call.callee);
        if call.callee.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        let types = self.cs_type_text(cs, file, segs, &written.join("."));
        if types.is_empty() {
            let known = match self.cs_name(cs, file, segs, written[0], &|_| true, false) {
                Name::Bcl => true,
                Name::Repo(_) | Name::Missing => false,
            };
            return if known {
                Outcome::Local
            } else {
                Outcome::Gap(GapReason::Unbound)
            };
        }
        let mut nodes = Vec::new();
        for t in types
            .into_iter()
            .filter(|&t| is_constructible(self.graph[t].kind))
        {
            let owner = cs.fqn.get(&t).cloned().unwrap_or_default();
            let name = cs
                .segs
                .get(&t)
                .and_then(|s| s.last())
                .cloned()
                .unwrap_or_default();
            let ctors = cs.child(&owner, &name, &|k| k == SymbolKind::Constructor, self);
            if ctors.is_empty() {
                nodes.push(t);
            } else {
                nodes.extend(ctors);
            }
        }
        nodes.sort();
        nodes.dedup();
        if nodes.is_empty() {
            return Outcome::Gap(GapReason::Unbound);
        }
        let status = Self::cs_status(&nodes);
        Outcome::Hit(nodes, status)
    }

    /// Resolves a `: base(..)` or `: this(..)` constructor initializer of the constructor `caller`.
    fn cs_ctor_chain(&self, cs: &CsIndex, call: &CallSite, segs: &[String], base: bool) -> Outcome {
        let Some(t) = self.cs_enclosing_type(cs, &segs[..segs.len().saturating_sub(1)]) else {
            return Outcome::Gap(GapReason::Unbound);
        };
        let targets: Vec<NodeIndex> = if base {
            let file = call.caller.path();
            let tsegs = cs.segs.get(&t).cloned().unwrap_or_default();
            let mut out = Vec::new();
            let mut external = false;
            for b in cs.bases.get(&t).into_iter().flatten() {
                let found = self.cs_type_text(cs, file, &tsegs, b);
                if found.is_empty() {
                    external = true;
                }
                out.extend(
                    found
                        .into_iter()
                        .filter(|&n| is_constructible(self.graph[n].kind)),
                );
            }
            if out.is_empty() {
                return if external {
                    Outcome::Gap(GapReason::Unbound)
                } else {
                    Outcome::Local
                };
            }
            out
        } else {
            vec![t]
        };
        let mut nodes = Vec::new();
        for n in targets {
            let owner = cs.fqn.get(&n).cloned().unwrap_or_default();
            let name = cs
                .segs
                .get(&n)
                .and_then(|s| s.last())
                .cloned()
                .unwrap_or_default();
            let me = self.index.get(&call.caller).copied();
            nodes.extend(
                cs.child(&owner, &name, &|k| k == SymbolKind::Constructor, self)
                    .into_iter()
                    .filter(|&c| Some(c) != me),
            );
            if nodes.is_empty() && base {
                nodes.push(n);
            }
        }
        if nodes.is_empty() {
            return Outcome::Gap(GapReason::Unbound);
        }
        nodes.sort();
        nodes.dedup();
        let status = Self::cs_status(&nodes);
        Outcome::Hit(nodes, status)
    }

    /// Resolves the call `call` of a C# caller.
    pub(super) fn resolve_csharp(&self, cs: &CsIndex, call: &CallSite) -> Outcome {
        let Some(&node) = self.index.get(&call.caller) else {
            return Outcome::Gap(GapReason::Unbound);
        };
        let segs: Vec<String> = cs.segs.get(&node).cloned().unwrap_or_default();
        let file = call.caller.path();
        match call.qualifier.as_deref() {
            Some(Q_NEW) => return self.cs_construct(cs, call, &segs),
            Some(Q_BASE_INIT) => return self.cs_ctor_chain(cs, call, &segs, true),
            Some(Q_THIS_INIT) => return self.cs_ctor_chain(cs, call, &segs, false),
            Some(Q_BASE) => return self.cs_base_call(cs, call, &segs),
            _ => {}
        }
        if call.callee.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        if call.method {
            return match &call.receiver {
                Some(Receiver::SelfValue) => self.cs_self_call(cs, call, &segs),
                Some(Receiver::Typed(t)) => self.cs_typed(cs, call, &segs, t),
                _ => Outcome::Gap(GapReason::Dynamic),
            };
        }
        let Some((head, rest)) = call.qual_path.split_first() else {
            if call.local != LocalBinding::None {
                return Outcome::Gap(GapReason::LocalValue);
            }
            return match self.cs_name(cs, file, &segs, &call.callee, &is_callable, true) {
                Name::Repo(nodes) => {
                    let status = Self::cs_status(&nodes);
                    Outcome::Hit(nodes, status)
                }
                Name::Bcl | Name::Missing => Outcome::Gap(GapReason::Unbound),
            };
        };
        let start = match self.cs_name(cs, file, &segs, head, &|_| true, true) {
            Name::Repo(nodes) => nodes,
            Name::Bcl => return Outcome::Local,
            Name::Missing => return Outcome::Gap(GapReason::Unbound),
        };
        self.cs_chain(cs, call, &segs, start, rest)
    }

    /// Follows `rest` and then the callee through the members of `start`.
    fn cs_chain(
        &self,
        cs: &CsIndex,
        call: &CallSite,
        segs: &[String],
        start: Vec<NodeIndex>,
        rest: &[String],
    ) -> Outcome {
        let file = call.caller.path();
        let mut cur = start;
        let names = rest
            .iter()
            .map(String::as_str)
            .chain([call.callee.as_str()]);
        let last = rest.len();
        for (i, seg) in names.enumerate() {
            // A field or property is a value: continue in its declared type.
            let mut typed: Vec<NodeIndex> = Vec::new();
            for &n in &cur {
                if matches!(self.graph[n].kind, SymbolKind::Field | SymbolKind::Property) {
                    let owner = cs
                        .segs
                        .get(&n)
                        .map(|s| s[..s.len() - 1].join("."))
                        .unwrap_or_default();
                    let name = cs
                        .segs
                        .get(&n)
                        .and_then(|s| s.last())
                        .cloned()
                        .unwrap_or_default();
                    match cs.field_types.get(&(owner, name)) {
                        Some(t) if !t.is_empty() => {
                            let nsegs = cs.segs.get(&n).cloned().unwrap_or_default();
                            match self.cs_name(cs, file, &nsegs, t, &is_type, false) {
                                Name::Repo(ts) => typed.extend(ts),
                                Name::Bcl => return Outcome::Local,
                                Name::Missing => {}
                            }
                        }
                        _ => {}
                    }
                } else {
                    typed.push(n);
                }
            }
            if typed.is_empty() {
                return Outcome::Gap(GapReason::Dynamic);
            }
            let want: &dyn Fn(SymbolKind) -> bool =
                if i == last { &is_callable } else { &|_| true };
            let mut next = Vec::new();
            for &n in &typed {
                next.extend(self.cs_members(cs, n, seg, want).nodes);
            }
            next.sort();
            next.dedup();
            if next.is_empty() {
                if i == last
                    && typed.iter().all(|&n| is_type(self.graph[n].kind))
                    && let Some(t) = typed
                        .first()
                        .and_then(|n| cs.segs.get(n))
                        .and_then(|s| s.last())
                    && let hit @ Outcome::Hit(..) =
                        Self::cs_extensions(cs, file, segs, &call.callee, t)
                {
                    return hit;
                }
                return Outcome::Gap(GapReason::Unbound);
            }
            cur = next;
        }
        let status = Self::cs_status(&cur);
        Outcome::Hit(cur, status)
    }

    /// `this.M(..)`: the members of the enclosing type, then extensions on it.
    fn cs_self_call(&self, cs: &CsIndex, call: &CallSite, segs: &[String]) -> Outcome {
        let Some(t) = self.cs_enclosing_type(cs, segs) else {
            return Outcome::Gap(GapReason::Unbound);
        };
        let m = self.cs_hierarchy_member(cs, t, &call.callee, &is_callable, 0);
        if !m.nodes.is_empty() {
            let status = Self::cs_status(&m.nodes);
            return Outcome::Hit(m.nodes, status);
        }
        let tname = cs
            .segs
            .get(&t)
            .and_then(|s| s.last())
            .cloned()
            .unwrap_or_default();
        Self::cs_extensions(cs, call.caller.path(), segs, &call.callee, &tname)
    }

    /// `base.M(..)`: the members of the repository base types of the enclosing type.
    fn cs_base_call(&self, cs: &CsIndex, call: &CallSite, segs: &[String]) -> Outcome {
        let Some(t) = self.cs_enclosing_type(cs, segs) else {
            return Outcome::Gap(GapReason::Unbound);
        };
        let file = call.caller.path();
        let tsegs = cs.segs.get(&t).cloned().unwrap_or_default();
        let mut nodes = Vec::new();
        for b in cs.bases.get(&t).into_iter().flatten() {
            for n in self.cs_type_text(cs, file, &tsegs, b) {
                nodes.extend(
                    self.cs_hierarchy_member(cs, n, &call.callee, &is_callable, 0)
                        .nodes,
                );
            }
        }
        nodes.sort();
        nodes.dedup();
        if nodes.is_empty() {
            return Outcome::Gap(GapReason::Unbound);
        }
        let status = Self::cs_status(&nodes);
        Outcome::Hit(nodes, status)
    }

    /// What an unresolved C# `call` says about its callee (`None` when genuinely unknown).
    pub(super) fn csharp_qualifier(&self, cs: &CsIndex, call: &CallSite) -> Option<CallQualifier> {
        if call.callee.is_empty() || call.qualifier.is_some() {
            return None;
        }
        if call.method {
            return Some(match &call.receiver {
                Some(Receiver::SelfValue) => {
                    let segs = self
                        .index
                        .get(&call.caller)
                        .and_then(|n| cs.segs.get(n))
                        .cloned()
                        .unwrap_or_default();
                    match self
                        .cs_enclosing_type(cs, &segs)
                        .and_then(|t| cs.segs.get(&t))
                        .and_then(|s| s.last())
                    {
                        Some(t) => CallQualifier::SelfType(t.clone()),
                        None => CallQualifier::Receiver { args: call.args },
                    }
                }
                Some(Receiver::Typed(t)) => CallQualifier::Typed(t.clone()),
                _ => CallQualifier::Receiver { args: call.args },
            });
        }
        let head = call.qual_path.first()?;
        let node = self.index.get(&call.caller)?;
        let segs = cs.segs.get(node)?;
        match self.cs_name(cs, call.caller.path(), segs, head, &|_| true, true) {
            Name::Repo(nodes)
                if nodes.iter().all(|&n| {
                    is_type(self.graph[n].kind) || self.graph[n].kind == SymbolKind::Namespace
                }) =>
            {
                call.qual_path.last().cloned().map(CallQualifier::Path)
            }
            Name::Bcl => call.qual_path.last().cloned().map(CallQualifier::Path),
            _ => Some(CallQualifier::Receiver { args: call.args }),
        }
    }

    /// Links each C# file to the repository types its alias and `using static` directives name.
    pub(super) fn link_csharp_imports(&mut self, cs: &CsIndex, files: &[FileSymbols]) {
        let mut links: HashSet<(NodeIndex, NodeIndex)> = HashSet::new();
        for f in files.iter().filter(|f| is_csharp(&f.path)) {
            let Some(&from) = cs.file_nodes.get(&f.path) else {
                continue;
            };
            for u in f.uses.iter().filter(|u| u.local != USE_NAMESPACE) {
                for t in self.cs_type_text(cs, &f.path, &[], &u.target) {
                    links.insert((from, t));
                }
            }
        }
        let mut links: Vec<_> = links.into_iter().collect();
        links.sort();
        for (a, b) in links {
            if a != b {
                self.link(a, b, super::EdgeKind::Imports, Status::Must);
            }
        }
    }
}

/// `text` without any `<..>` generic argument list.
fn strip_generics(text: &str) -> String {
    let mut depth = 0usize;
    let mut out = String::new();
    for c in text.chars() {
        match c {
            '<' => depth += 1,
            '>' => depth = depth.saturating_sub(1),
            c if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}
