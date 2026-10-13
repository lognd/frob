//! Intra-unit def-use edges with Must/May strength (cohesion.md 1.1; F2 binders and references).
//!
//! The engine walks one unit's body in evaluation order and joins reaching definitions across
//! branches and loop back edges. A read reached by a write through a local variable is a `Must`
//! edge (a static dependence, not a certain execution). Everything static dependence cannot see
//! is a `May` edge with a [`MayCause`]: attribute and heap writes, mutation through a method call,
//! closures capturing by reference, `setattr`-style dynamic writes and `**kwargs` splats. The
//! adapter supplies only the names of its operators in a [`DefUseSyntax`]; the walk is shared.

// frob:ticket 01M4CXSPADQCCZ40KNYPAFVSV6

use std::collections::{BTreeMap, BTreeSet, HashMap};

use tracing::{debug, trace};

use crate::operator::{Operator, Universal};
use crate::scope::{DeclId, DeclKind, Resolution, ScopeGraph, Status};
use crate::term::{NodeId, Term};

/// Why a [`Status::May`] def-use edge exists.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum MayCause {
    /// A write to `base.field` may reach a read of the same field through another alias.
    Attribute,
    /// A `setattr`-style write whose field is dynamic: it may reach any field read.
    DynamicAttribute,
    /// A `**kwargs` splat handed to a call whose callee may mutate what it holds.
    Kwargs,
    /// A closure captures the variable by reference, so any write may be seen inside.
    Closure,
    /// A method call (or index write) on a variable may mutate it in place.
    Mutation,
}

impl MayCause {
    /// Stable lowercase spelling for reports and golden files.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Attribute => "attribute",
            Self::DynamicAttribute => "dynamic-attribute",
            Self::Kwargs => "kwargs",
            Self::Closure => "closure",
            Self::Mutation => "mutation",
        }
    }
}

/// One def-use edge: the write at `def` may or must reach the read at `use_site`.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct DefUseEdge {
    /// The variable (`x`) or attribute location (`self.v`).
    pub var: String,
    /// The defining node (an assignment, a binder node, or the unit for a parameter).
    pub def: NodeId,
    /// The reading node.
    pub use_site: NodeId,
    /// `Must` for a static dependence, `May` for an alias-dependent one.
    pub strength: Status,
    /// Why the edge is `May`; `None` exactly for `Must` edges.
    pub cause: Option<MayCause>,
}

/// The operator names (adapter operator `name`s) that tell the engine how a language spells things.
#[derive(Debug, Clone, Copy, Default)]
pub struct DefUseSyntax {
    /// Assignment operators; the flag is true for compound ones (`+=`), which also read.
    pub assign: &'static [(&'static str, bool)],
    /// Declarators: first child is a `lit` naming the variable, the rest is the initialiser.
    pub declarators: &'static [&'static str],
    /// Member access (`a.f`): first child the base, last `lit` child the field name.
    pub members: &'static [&'static str],
    /// Index access (`a[i]`); a write through it mutates the base.
    pub indexes: &'static [&'static str],
    /// Conditional constructs whose alternative children fork the flow.
    pub branches: &'static [&'static str],
    /// Child operators that are alternatives of a branch (blocks, `else`, arms).
    pub alternatives: &'static [&'static str],
    /// Children of a branch that hold alternatives one level down (a `match` block).
    pub arm_containers: &'static [&'static str],
    /// Alternative operators that make a branch exhaustive (no fall-through path).
    pub else_ops: &'static [&'static str],
    /// Branches that are exhaustive by construction (`match`).
    pub exhaustive: &'static [&'static str],
    /// Loop constructs; their body may run any number of times.
    pub loops: &'static [&'static str],
    /// `bind` kinds that are loops (`for`): the rhs runs once, binders and body per iteration.
    pub loop_binds: &'static [&'static str],
    /// `bind` kinds that are match arms; a `group` holding them is an exhaustive branch.
    pub arm_binds: &'static [&'static str],
    /// Callee names that write a dynamically named attribute of their first argument.
    pub dynamic_setters: &'static [&'static str],
    /// Argument splats (`**kw`, `...xs`) whose referents the callee may mutate.
    pub splats: &'static [&'static str],
}

type Flow = BTreeMap<DeclId, BTreeSet<NodeId>>;

fn join(into: &mut Flow, other: &Flow) {
    for (d, defs) in other {
        into.entry(*d).or_default().extend(defs.iter().copied());
    }
}

struct Walker<'a> {
    term: &'a Term,
    scopes: &'a ScopeGraph,
    syn: &'a DefUseSyntax,
    must: BTreeSet<(DeclId, NodeId, NodeId)>,
    defs: BTreeSet<(DeclId, NodeId)>,
    uses: BTreeSet<(DeclId, NodeId)>,
    captures: BTreeSet<(DeclId, NodeId)>,
    cap_writes: BTreeSet<(DeclId, NodeId)>,
    mutations: BTreeSet<(DeclId, NodeId, MayCause)>,
    attr_writes: BTreeSet<(String, String, NodeId)>,
    attr_reads: BTreeSet<(String, String, NodeId)>,
    seq: HashMap<NodeId, u32>,
    clock: u32,
    loop_stack: Vec<NodeId>,
    loops_at: HashMap<NodeId, Vec<NodeId>>,
    anons: Vec<NodeId>,
}

fn op_name(term: &Term, id: NodeId) -> Option<&str> {
    match term.node(id).op() {
        Operator::Adapter(a) => Some(a.name.as_str()),
        Operator::Universal(_) => None,
    }
}

fn lit_text(term: &Term, id: NodeId) -> Option<&str> {
    match term.node(id).op() {
        Operator::Universal(Universal::Lit { lexeme, .. }) => Some(lexeme),
        _ => None,
    }
}

fn ref_name(term: &Term, id: NodeId) -> Option<&str> {
    match term.node(id).op() {
        Operator::Universal(Universal::Ref { name }) => Some(name),
        _ => None,
    }
}

impl Walker<'_> {
    fn is(&self, id: NodeId, set: &[&str]) -> bool {
        op_name(self.term, id).is_some_and(|n| set.contains(&n))
    }

    fn kids(&self, id: NodeId) -> Vec<NodeId> {
        self.term.node(id).children().to_vec()
    }

    fn stamp(&mut self, site: NodeId) {
        self.clock += 1;
        self.seq.entry(site).or_insert(self.clock);
        let loops = self.loop_stack.clone();
        self.loops_at.entry(site).or_insert(loops);
    }

    fn binder_decl(&self, r: NodeId) -> Option<DeclId> {
        let rid = self.scopes.ref_at(r)?;
        match self.scopes.resolve(rid) {
            Resolution::Must(d) if self.scopes.decl(d).kind == DeclKind::Binder => Some(d),
            _ => None,
        }
    }

    fn captured(&self, d: DeclId) -> bool {
        let Some(&anon) = self.anons.last() else {
            return false;
        };
        let Some(mut cur) = self.scopes.scope_node(self.scopes.decl(d).scope) else {
            return true;
        };
        loop {
            if cur == anon {
                return false;
            }
            match self.term.node(cur).parent() {
                Some(p) => cur = p,
                None => return true,
            }
        }
    }

    fn write(&mut self, d: DeclId, site: NodeId, flow: &mut Flow) {
        self.stamp(site);
        if self.captured(d) {
            self.cap_writes.insert((d, site));
            return;
        }
        self.defs.insert((d, site));
        flow.insert(d, BTreeSet::from([site]));
    }

    fn read(&mut self, d: DeclId, site: NodeId, flow: &Flow) {
        self.stamp(site);
        if self.captured(d) {
            self.captures.insert((d, site));
            return;
        }
        self.uses.insert((d, site));
        for &def in flow.get(&d).into_iter().flatten() {
            self.must.insert((d, def, site));
        }
    }

    fn name_decl(&self, at: NodeId, name: &str) -> Option<DeclId> {
        let mut cur = Some(at);
        while let Some(n) = cur {
            if let Some(s) = self.scopes.scope_at(n) {
                return match self.scopes.resolve_name(s, name) {
                    Resolution::Must(d) if self.scopes.decl(d).kind == DeclKind::Binder => Some(d),
                    _ => None,
                };
            }
            cur = self.term.node(n).parent();
        }
        None
    }

    fn walk_all(&mut self, id: NodeId, flow: &mut Flow) {
        for c in self.kids(id) {
            self.walk(c, flow);
        }
    }

    fn field_of(&self, member: NodeId) -> Option<String> {
        self.kids(member)
            .iter()
            .rev()
            .find_map(|&c| lit_text(self.term, c).map(str::to_owned))
    }

    fn base_key(&self, member: NodeId) -> String {
        let base = self.kids(member).first().copied();
        base.and_then(|b| {
            ref_name(self.term, b)
                .or_else(|| lit_text(self.term, b))
                .map(str::to_owned)
        })
        .unwrap_or_else(|| "_".to_owned())
    }

    fn base_decl(&self, member: NodeId) -> Option<DeclId> {
        let b = *self.term.node(member).children().first()?;
        self.binder_decl(b)
    }

    fn walk(&mut self, id: NodeId, flow: &mut Flow) {
        let node = self.term.node(id);
        match node.op() {
            Operator::Universal(Universal::Ref { .. }) => {
                if let Some(d) = self.binder_decl(id) {
                    self.read(d, id, flow);
                }
            }
            Operator::Universal(Universal::Bind { kind, .. }) => {
                if self.syn.loop_binds.contains(&kind.as_str()) {
                    self.walk_loop_bind(id, flow);
                } else {
                    self.walk_bind(id, flow);
                }
            }
            Operator::Universal(Universal::Group { .. }) if self.has_arms(id) => {
                self.walk_arms(id, flow);
            }
            Operator::Universal(Universal::Anon { .. }) => {
                self.anons.push(id);
                self.walk_all(id, flow);
                self.anons.pop();
            }
            Operator::Universal(Universal::Apply { .. }) => self.walk_apply(id, flow),
            Operator::Adapter(_) => self.walk_adapter(id, flow),
            Operator::Universal(_) => self.walk_all(id, flow),
        }
    }

    fn bind_kind_in(&self, id: NodeId, set: &[&str]) -> bool {
        matches!(self.term.node(id).op(),
            Operator::Universal(Universal::Bind { kind, .. }) if set.contains(&kind.as_str()))
    }

    fn has_arms(&self, id: NodeId) -> bool {
        self.term
            .node(id)
            .children()
            .iter()
            .any(|&c| self.bind_kind_in(c, self.syn.arm_binds))
    }

    fn walk_arms(&mut self, id: NodeId, flow: &mut Flow) {
        let mut out = Flow::new();
        for c in self.kids(id) {
            if self.bind_kind_in(c, self.syn.arm_binds) {
                let mut f = flow.clone();
                self.walk(c, &mut f);
                join(&mut out, &f);
            } else {
                self.walk(c, flow);
            }
        }
        *flow = out;
    }

    fn walk_loop_bind(&mut self, id: NodeId, flow: &mut Flow) {
        let kids = self.kids(id);
        if let Some(&rhs) = kids.get(1) {
            self.walk(rhs, flow);
        }
        self.loop_stack.push(id);
        let entry = flow.clone();
        let mut state = flow.clone();
        for _ in 0..2 {
            let mut f = state.clone();
            self.bind_names(id, &mut f);
            if let Some(&body) = kids.first() {
                self.walk(body, &mut f);
            }
            join(&mut state, &f);
        }
        self.loop_stack.pop();
        join(&mut state, &entry);
        *flow = state;
    }

    fn bind_names(&mut self, id: NodeId, flow: &mut Flow) {
        let names: Vec<String> = self.term.node(id).binders().to_vec();
        if let Some(s) = self.scopes.scope_at(id) {
            for n in names {
                if let Resolution::Must(d) = self.scopes.resolve_name(s, &n) {
                    self.write(d, id, flow);
                }
            }
        }
    }

    fn walk_bind(&mut self, id: NodeId, flow: &mut Flow) {
        let kids = self.kids(id);
        if let Some(&rhs) = kids.get(1) {
            self.walk(rhs, flow);
        }
        self.bind_names(id, flow);
        if let Some(&body) = kids.first() {
            self.walk(body, flow);
        }
    }

    fn walk_apply(&mut self, id: NodeId, flow: &mut Flow) {
        self.walk_all(id, flow);
        let kids = self.kids(id);
        self.stamp(id);
        let Some(&head) = kids.first() else { return };
        if self.is(head, self.syn.members)
            && let Some(d) = self.base_decl(head)
        {
            self.mutations.insert((d, id, MayCause::Mutation));
        }
        if ref_name(self.term, head).is_some_and(|n| self.syn.dynamic_setters.contains(&n))
            && let Some(&first) = kids.get(1)
        {
            if let Some(d) = self.binder_decl(first) {
                self.mutations.insert((d, id, MayCause::DynamicAttribute));
            }
            let base = ref_name(self.term, first).unwrap_or("_").to_owned();
            self.attr_writes.insert(("*".to_owned(), base, id));
        }
        for &c in &kids {
            if self.is(c, self.syn.splats) {
                for r in self.term.descendants(c) {
                    if let Some(d) = self.binder_decl(r) {
                        self.mutations.insert((d, id, MayCause::Kwargs));
                    }
                }
            }
        }
    }

    fn walk_adapter(&mut self, id: NodeId, flow: &mut Flow) {
        let name = op_name(self.term, id).unwrap_or_default().to_owned();
        let n = name.as_str();
        if let Some(&(_, compound)) = self.syn.assign.iter().find(|(a, _)| *a == n) {
            self.walk_assign(id, compound, flow);
        } else if self.syn.declarators.contains(&n) {
            let kids = self.kids(id);
            for &c in kids.iter().skip(1) {
                self.walk(c, flow);
            }
            if kids.len() > 1
                && let Some(var) = kids.first().and_then(|&k| lit_text(self.term, k))
                && let Some(d) = self.name_decl(id, var)
            {
                self.write(d, id, flow);
            }
        } else if self.syn.members.contains(&n) {
            self.walk_all(id, flow);
            if let Some(f) = self.field_of(id) {
                self.stamp(id);
                self.attr_reads.insert((f, self.base_key(id), id));
            }
        } else if self.syn.branches.contains(&n) {
            self.walk_branch(id, flow);
        } else if self.syn.loops.contains(&n) {
            self.walk_loop(id, flow);
        } else {
            self.walk_all(id, flow);
        }
    }

    fn walk_assign(&mut self, id: NodeId, compound: bool, flow: &mut Flow) {
        let kids = self.kids(id);
        let (Some(&target), Some(&value)) = (kids.first(), kids.last()) else {
            return;
        };
        if target != value {
            self.walk(value, flow);
        }
        if ref_name(self.term, target).is_some() {
            if let Some(d) = self.binder_decl(target) {
                if compound {
                    self.read(d, target, flow);
                }
                self.write(d, id, flow);
            }
        } else if self.is(target, self.syn.members) {
            self.walk_all(target, flow);
            if let Some(f) = self.field_of(target) {
                let base = self.base_key(target);
                self.stamp(id);
                if compound {
                    self.attr_reads.insert((f.clone(), base.clone(), id));
                }
                self.attr_writes.insert((f, base, id));
            }
            if let Some(d) = self.base_decl(target) {
                self.mutations.insert((d, id, MayCause::Attribute));
            }
        } else if self.is(target, self.syn.indexes) {
            self.walk_all(target, flow);
            if let Some(d) = self.base_decl(target) {
                self.mutations.insert((d, id, MayCause::Mutation));
            }
        } else {
            for r in self.term.descendants(target) {
                if ref_name(self.term, r).is_some()
                    && let Some(d) = self.binder_decl(r)
                {
                    self.write(d, id, flow);
                }
            }
        }
    }

    fn is_alt(&self, c: NodeId) -> bool {
        self.is(c, self.syn.alternatives)
            || matches!(
                self.term.node(c).op(),
                Operator::Universal(Universal::Group { .. })
            )
    }

    fn walk_branch(&mut self, id: NodeId, flow: &mut Flow) {
        let mut alts: Vec<NodeId> = Vec::new();
        let mut pre: Vec<NodeId> = Vec::new();
        for c in self.kids(id) {
            if self.is(c, self.syn.arm_containers) {
                alts.extend(self.kids(c).into_iter().filter(|&a| self.is_alt(a)));
            } else if self.is_alt(c) {
                alts.push(c);
            } else if alts.is_empty() {
                pre.push(c);
            }
        }
        for c in pre {
            self.walk(c, flow);
        }
        let has_else =
            alts.iter().any(|&a| self.is(a, self.syn.else_ops)) || self.is(id, self.syn.exhaustive);
        let mut out: Flow = if has_else { Flow::new() } else { flow.clone() };
        for a in alts {
            let mut f = flow.clone();
            self.walk(a, &mut f);
            join(&mut out, &f);
        }
        *flow = out;
    }

    fn walk_loop(&mut self, id: NodeId, flow: &mut Flow) {
        self.loop_stack.push(id);
        let entry = flow.clone();
        let mut once = flow.clone();
        self.walk_loop_body(id, &mut once);
        let mut again = entry.clone();
        join(&mut again, &once);
        self.walk_loop_body(id, &mut again);
        self.loop_stack.pop();
        let mut exit = entry;
        join(&mut exit, &again);
        *flow = exit;
    }

    fn walk_loop_body(&mut self, id: NodeId, flow: &mut Flow) {
        let kids = self.kids(id);
        let split = kids
            .iter()
            .position(|&c| matches!(lit_text(self.term, c), Some("in" | "of")));
        for (i, &c) in kids.iter().enumerate() {
            if split.is_some_and(|s| i < s) && ref_name(self.term, c).is_some() {
                continue;
            }
            self.walk(c, flow);
            if split == Some(i) {
                for &t in &kids[..i] {
                    if let Some(d) = self.binder_decl(t) {
                        self.write(d, id, flow);
                    }
                }
            }
        }
    }

    fn reaches(&self, def: NodeId, use_site: NodeId) -> bool {
        let (Some(a), Some(b)) = (self.seq.get(&def), self.seq.get(&use_site)) else {
            return false;
        };
        if a < b {
            return true;
        }
        let la = self.loops_at.get(&def).map_or(&[][..], Vec::as_slice);
        let lb = self.loops_at.get(&use_site).map_or(&[][..], Vec::as_slice);
        la.iter().any(|l| lb.contains(l))
    }
}

/// Computes the def-use edges of `unit` (a function-like unit of `term`), sorted and deduplicated.
///
/// `scopes` must resolve the references of `term` (the adapter's folded scope graph); `syntax`
/// names the language's operators. Parameters and unit-level binders are defined at `unit`.
pub fn def_use(
    term: &Term,
    scopes: &ScopeGraph,
    unit: NodeId,
    syntax: &DefUseSyntax,
) -> Vec<DefUseEdge> {
    let mut w = Walker {
        term,
        scopes,
        syn: syntax,
        must: BTreeSet::new(),
        defs: BTreeSet::new(),
        uses: BTreeSet::new(),
        captures: BTreeSet::new(),
        cap_writes: BTreeSet::new(),
        mutations: BTreeSet::new(),
        attr_writes: BTreeSet::new(),
        attr_reads: BTreeSet::new(),
        seq: HashMap::new(),
        clock: 0,
        loop_stack: Vec::new(),
        loops_at: HashMap::new(),
        anons: Vec::new(),
    };
    let mut flow = Flow::new();
    w.stamp(unit);
    if let Some(s) = scopes.scope_at(unit) {
        for (i, d) in scopes.decls().iter().enumerate() {
            if d.scope == s && d.kind == DeclKind::Binder {
                let id = DeclId(crate::idx32(i));
                w.defs.insert((id, unit));
                flow.insert(id, BTreeSet::from([unit]));
            }
        }
    }
    for c in w.kids(unit) {
        w.walk(c, &mut flow);
    }
    let edges = collect(&w);
    debug!(edges = edges.len(), "def-use computed");
    edges
}

fn collect(w: &Walker<'_>) -> Vec<DefUseEdge> {
    let name = |d: DeclId| w.scopes.decl(d).name.clone();
    let mut out: BTreeSet<DefUseEdge> = BTreeSet::new();
    let mut may = |var: String, def: NodeId, use_site: NodeId, cause: MayCause| {
        if def != use_site {
            out.insert(DefUseEdge {
                var,
                def,
                use_site,
                strength: Status::May,
                cause: Some(cause),
            });
        }
    };
    trace!(
        must = w.must.len(),
        mutations = w.mutations.len(),
        "collecting may edges"
    );
    for &(d, u) in &w.captures {
        for &(d2, def) in w.defs.iter().chain(&w.cap_writes) {
            if d2 == d {
                may(name(d), def, u, MayCause::Closure);
            }
        }
    }
    for &(d, wr) in &w.cap_writes {
        for &(d2, u) in w.uses.iter().chain(&w.captures) {
            if d2 == d {
                may(name(d), wr, u, MayCause::Closure);
            }
        }
    }
    for &(d, m, cause) in &w.mutations {
        for &(d2, u) in &w.uses {
            if d2 == d && w.reaches(m, u) {
                may(name(d), m, u, cause);
            }
        }
        let n = name(d);
        for (f, base, r) in &w.attr_reads {
            if *base == n && w.reaches(m, *r) {
                may(format!("{base}.{f}"), m, *r, cause);
            }
        }
    }
    for (f, b, wr) in &w.attr_writes {
        for (f2, _, r) in &w.attr_reads {
            if (f == f2 || f == "*") && w.reaches(*wr, *r) {
                let cause = if f == "*" {
                    MayCause::DynamicAttribute
                } else {
                    MayCause::Attribute
                };
                may(format!("{b}.{f2}"), *wr, *r, cause);
            }
        }
    }
    let mut v: Vec<DefUseEdge> = out.into_iter().collect();
    v.extend(w.must.iter().map(|&(d, def, use_site)| DefUseEdge {
        var: name(d),
        def,
        use_site,
        strength: Status::Must,
        cause: None,
    }));
    let key = |n: NodeId| w.seq.get(&n).copied().unwrap_or(0);
    v.sort_by(|a, b| {
        (key(a.use_site), key(a.def), &a.var, a.strength, a.cause).cmp(&(
            key(b.use_site),
            key(b.def),
            &b.var,
            b.strength,
            b.cause,
        ))
    });
    v.dedup();
    v
}
