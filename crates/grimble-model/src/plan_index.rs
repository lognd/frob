//! The resolved planning graph of one model root (grmb-planning 4, 9): nodes, clauses and edges.
//!
//! [`PlanModel::build`] walks the parsed planning items in path order, builds the name tables
//! (systems, actors, goal variants, steps, scenarios, pages), and resolves every reference to the
//! anchor of its target. The result is plain data: binding computes statuses and obligations on it,
//! and the sibling document renders it.

// frob:ticket 01M4FDBBXG990QVX35HERF5VCQ

use std::collections::{BTreeMap, BTreeSet};

use crate::ast::{EntityKind, FileStatus, Item, RefPath, Sel};
use crate::model::Index;
use crate::plan::{Chain, Elem, ImplTarget, PClauseKind, PlanItem, ScMember, Tail, Variant};
use crate::plan_check::{find, join};
use crate::span::Span;

/// A `realization` or `verified_by` clause of a planning node.
#[derive(Clone, Debug)]
pub struct PlanClause {
    /// `kind/full/key[n]` (`impl/S.sc.o.step/realization[0]`).
    pub anchor: String,
    /// The realization kind; `None` marks a `verified_by` clause.
    pub realization_kind: Option<String>,
    /// The realization name, if written.
    pub name: Option<String>,
    /// The selector as written.
    pub sel: Sel,
    /// The `for step.variant` pair of a `verified_by`, as written.
    pub pair: Option<String>,
    /// The whole clause span.
    pub span: Span,
}

/// One edge of the planning graph.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct PlanEdge {
    /// `realizes`, `requires`, `refines`, `succ`, `invokes`, `impl_of`, `impl_for`,
    /// `requires_page`, `navigates`, `actor_node` or `in_node`.
    pub kind: &'static str,
    /// Source anchor.
    pub from: String,
    /// Target anchor.
    pub to: String,
    /// The scenario a `succ` edge belongs to.
    pub scenario: Option<String>,
}

/// One planning entity with the facts of its kind filled in.
#[derive(Clone, Debug, Default)]
pub struct PlanNode {
    /// `kind/full`.
    pub anchor: String,
    /// `system`, `actor`, `goal`, `step`, `scenario`, `impl` or `page`.
    pub kind: &'static str,
    /// The entity name as the sibling document shows it.
    pub name: String,
    /// Index of the file in the root.
    pub file: usize,
    /// The span of the item (the variant, for a goal).
    pub span: Span,
    /// Anchor of the owning system.
    pub system: Option<String>,
    /// The `realization` and `verified_by` clauses, in written order.
    pub clauses: Vec<PlanClause>,
    /// Actor kind word.
    pub actor_kind: Option<String>,
    /// Actor `node`, or the `in node` of an impl (a node anchor).
    pub node: Option<String>,
    /// Goal: the parent goal or actor anchor.
    pub parent: Option<String>,
    /// Goal: the dimension key of the declaring block.
    pub dimension: Option<String>,
    /// Goal: no goal refines it.
    pub leaf: bool,
    /// Goal: anchors of the goals it requires.
    pub requires: Vec<String>,
    /// Step: the owner as written (`system` or an actor reference).
    pub owner: String,
    /// Step: `(variant, payload)` outcomes.
    pub outcomes: Vec<(String, Option<String>)>,
    /// Scenario: goals realized.
    pub realizes: Vec<String>,
    /// Scenario: the declared `fails with` set.
    pub fails_with: Vec<String>,
    /// Scenario: steps used directly, in order of first use.
    pub uses: Vec<String>,
    /// Scenario: scenarios included.
    pub includes: Vec<String>,
    /// Impl: the step anchor.
    pub impl_step: Option<String>,
    /// Impl: the scenario anchor; `None` for `for *`.
    pub impl_scenario: Option<String>,
    /// Impl: pages it requires.
    pub pages: Vec<String>,
    /// Page: marked `entry`.
    pub entry: bool,
    /// Page: pages that navigate to it.
    pub from: Vec<String>,
}

/// The planning graph of a model root.
#[derive(Clone, Debug, Default)]
pub struct PlanModel {
    /// Nodes in anchor order.
    pub nodes: Vec<PlanNode>,
    /// Edges in sorted order.
    pub edges: Vec<PlanEdge>,
}

struct Raw<'a> {
    file: usize,
    ctx: Vec<String>,
    item: &'a PlanItem,
}

#[derive(Default)]
struct Tables {
    systems: BTreeSet<String>,
    actors: BTreeMap<String, String>,
    /// Goal variant full name to its anchor.
    variants: BTreeMap<String, String>,
    steps: BTreeMap<String, String>,
    scenarios: BTreeMap<String, String>,
    pages: BTreeMap<String, String>,
}

fn collect<'a>(file: usize, items: &'a [Item], ctx: &mut Vec<String>, out: &mut Vec<Raw<'a>>) {
    for item in items {
        match item {
            Item::Namespace(n) => {
                ctx.push(n.name.text.clone());
                collect(file, &n.items, ctx, out);
                ctx.pop();
            }
            Item::Plan(p) => {
                let p: &PlanItem = p;
                out.push(Raw {
                    file,
                    ctx: ctx.clone(),
                    item: p,
                });
                if let PlanItem::System(s) = p {
                    ctx.push(s.name.text.clone());
                    collect(file, &s.items, ctx, out);
                    ctx.pop();
                }
            }
            _ => {}
        }
    }
}

fn register(t: &mut Tables, r: &Raw<'_>) {
    let ctx = &r.ctx;
    match r.item {
        PlanItem::System(s) => {
            t.systems.insert(join(ctx, &s.name.text));
        }
        PlanItem::Actor(a) => {
            let full = join(ctx, &a.name.text);
            t.actors.insert(full.clone(), format!("actor/{full}"));
        }
        PlanItem::Goal(g) => {
            let block = join(ctx, &g.path.dotted());
            for v in &g.variants {
                let full = format!("{block}.{}", v.name.text);
                t.variants.insert(full.clone(), format!("goal/{full}"));
            }
        }
        PlanItem::Step(s) => {
            let full = join(ctx, &s.target.dotted());
            t.steps.insert(full.clone(), format!("step/{full}"));
        }
        PlanItem::Scenario(s) => {
            let full = join(ctx, &s.name.text);
            t.scenarios.insert(full.clone(), format!("scenario/{full}"));
        }
        PlanItem::Page(p) => {
            let full = join(ctx, &p.name.text);
            t.pages.insert(full.clone(), format!("page/{full}"));
        }
        PlanItem::Impl(_) => {}
    }
}

fn system_of(t: &Tables, ctx: &[String]) -> Option<String> {
    (0..=ctx.len())
        .rev()
        .map(|n| ctx[..n].join("."))
        .find(|k| t.systems.contains(k))
        .map(|k| format!("system/{k}"))
}

fn lookup(map: &BTreeMap<String, String>, ctx: &[String], p: &RefPath) -> Option<String> {
    find(map, ctx, p).map(|(_, a)| a.clone())
}

/// The `realization` and `verified_by` clauses of `clauses` with their anchors.
fn plan_clauses(anchor: &str, clauses: &[crate::plan::PClause]) -> Vec<PlanClause> {
    let (mut real, mut ver) = (0usize, 0usize);
    let mut out = Vec::new();
    for c in clauses {
        match &c.kind {
            PClauseKind::Realization(r) => {
                out.push(PlanClause {
                    anchor: format!("{anchor}/realization[{real}]"),
                    realization_kind: Some(r.kind.text.clone()),
                    name: r.name.as_ref().map(|n| n.text.clone()),
                    sel: r.sel.clone(),
                    pair: None,
                    span: c.span,
                });
                real += 1;
            }
            PClauseKind::Verified(v) => {
                out.push(PlanClause {
                    anchor: format!("{anchor}/verified_by[{ver}]"),
                    realization_kind: None,
                    name: None,
                    sel: v.sel.clone(),
                    pair: v.pair.as_ref().map(RefPath::written),
                    span: c.span,
                });
                ver += 1;
            }
            _ => {}
        }
    }
    out
}

struct Walk<'t> {
    t: &'t Tables,
    ctx: Vec<String>,
    uses: Vec<String>,
    includes: Vec<String>,
    edges: BTreeSet<PlanEdge>,
    scenario: String,
}

impl Walk<'_> {
    /// Visits one element; returns its step anchor when it is a step.
    fn elem(&mut self, e: &Elem, prev: &mut Option<String>) -> Option<String> {
        match e {
            Elem::Step(p) => {
                let a = lookup(&self.t.steps, &self.ctx, p)?;
                if !self.uses.contains(&a) {
                    self.uses.push(a.clone());
                }
                if let Some(from) = prev.take() {
                    self.edges.insert(PlanEdge {
                        kind: "succ",
                        from,
                        to: a.clone(),
                        scenario: Some(self.scenario.clone()),
                    });
                }
                *prev = Some(a.clone());
                Some(a)
            }
            Elem::Include(p) => {
                let a = lookup(&self.t.scenarios, &self.ctx, p)?;
                if !self.includes.contains(&a) {
                    self.includes.push(a.clone());
                }
                self.edges.insert(PlanEdge {
                    kind: "invokes",
                    from: self.scenario.clone(),
                    to: a,
                    scenario: None,
                });
                None
            }
        }
    }

    fn chain(&mut self, c: &Chain, mut prev: Option<String>) {
        for (e, _) in &c.links {
            self.elem(e, &mut prev);
        }
        match &c.tail {
            Tail::Match { elem, arms } => {
                self.elem(elem, &mut prev);
                for arm in arms {
                    self.chain(&arm.chain, prev.clone());
                }
            }
            Tail::Open(e) => {
                self.elem(e, &mut prev);
            }
            Tail::Retry {
                step, otherwise, ..
            } => {
                self.elem(&Elem::Step(step.clone()), &mut prev);
                if let Some(o) = otherwise {
                    self.chain(o, prev);
                }
            }
            Tail::EndOk(_) | Tail::EndErr(_) => {}
        }
    }
}

fn node(
    t: &Tables,
    r: &Raw<'_>,
    anchor: String,
    kind: &'static str,
    name: &str,
    span: Span,
) -> PlanNode {
    PlanNode {
        anchor,
        kind,
        name: name.to_owned(),
        file: r.file,
        span,
        system: if kind == "system" {
            None
        } else {
            system_of(t, &r.ctx)
        },
        ..PlanNode::default()
    }
}

struct Build<'i, 'a> {
    idx: &'i Index<'a>,
    t: Tables,
    nodes: Vec<PlanNode>,
    edges: BTreeSet<PlanEdge>,
}

#[allow(clippy::many_single_char_names)] // short AST binders mirror the grammar
impl Build<'_, '_> {
    fn node_ref(&self, ctx: &[String], p: &RefPath) -> Option<String> {
        let r = self.idx.resolve(ctx, p)?;
        (self.idx.kind(r.rec) == EntityKind::Node)
            .then(|| format!("node/{}", self.idx.entities[r.rec].full))
    }

    fn edge(&mut self, kind: &'static str, from: &str, to: &str) {
        self.edges.insert(PlanEdge {
            kind,
            from: from.to_owned(),
            to: to.to_owned(),
            scenario: None,
        });
    }

    fn goal(&mut self, r: &Raw<'_>, g: &crate::plan::GoalBlock) {
        let block = join(&r.ctx, &g.path.dotted());
        let bctx: Vec<String> = block.split('.').map(str::to_owned).collect();
        let parent = lookup(&self.t.variants, &r.ctx, &g.path)
            .or_else(|| lookup(&self.t.actors, &r.ctx, &g.path));
        for v in &g.variants {
            self.variant(r, g, v, parent.as_ref(), &block, &bctx);
        }
    }

    fn variant(
        &mut self,
        r: &Raw<'_>,
        g: &crate::plan::GoalBlock,
        v: &Variant,
        parent: Option<&String>,
        block: &str,
        bctx: &[String],
    ) {
        let anchor = format!("goal/{block}.{}", v.name.text);
        let mut n = node(&self.t, r, anchor.clone(), "goal", &v.name.text, v.span);
        n.parent = parent.cloned();
        n.dimension = g.key.as_ref().map(|k| k.text.clone());
        for q in &v.requires {
            if let Some(a) = lookup(&self.t.variants, bctx, q) {
                self.edge("requires", &anchor, &a);
                n.requires.push(a);
            }
        }
        if let Some(p) = parent
            && p.starts_with("goal/")
        {
            self.edge("refines", &anchor, p);
        }
        n.clauses = plan_clauses(&anchor, &v.clauses);
        self.nodes.push(n);
    }

    fn scenario(&mut self, r: &Raw<'_>, s: &crate::plan::Scenario) {
        let full = join(&r.ctx, &s.name.text);
        let anchor = format!("scenario/{full}");
        let mut n = node(&self.t, r, anchor.clone(), "scenario", &s.name.text, s.span);
        for g in &s.realizes {
            if let Some(a) = lookup(&self.t.variants, &r.ctx, g) {
                self.edge("realizes", &anchor, &a);
                n.realizes.push(a);
            }
        }
        n.fails_with = s.fails.iter().flatten().map(|i| i.text.clone()).collect();
        let mut w = Walk {
            t: &self.t,
            ctx: r.ctx.clone(),
            uses: Vec::new(),
            includes: Vec::new(),
            edges: BTreeSet::new(),
            scenario: anchor.clone(),
        };
        for m in &s.members {
            match m {
                ScMember::Chain(_, c) => {
                    w.chain(c, None);
                }
                ScMember::Handle(h) => {
                    for arm in &h.arms {
                        w.chain(&arm.chain, None);
                    }
                }
                ScMember::Clause(_) => {}
            }
        }
        n.uses = w.uses;
        n.includes = w.includes;
        self.edges.extend(w.edges);
        let clauses: Vec<_> = s
            .members
            .iter()
            .filter_map(|m| match m {
                ScMember::Clause(c) => Some(c.clone()),
                _ => None,
            })
            .collect();
        n.clauses = plan_clauses(&anchor, &clauses);
        self.nodes.push(n);
    }

    fn imp(&mut self, r: &Raw<'_>, i: &crate::plan::Impl) {
        let tname = match &i.target {
            ImplTarget::Scenario(p) => p.dotted(),
            ImplTarget::Any(_) => "_".to_owned(),
        };
        let full = join(&r.ctx, &format!("{tname}.{}", i.step.dotted()));
        let anchor = format!("impl/{full}");
        let mut n = node(
            &self.t,
            r,
            anchor.clone(),
            "impl",
            &format!("{tname}.{}", i.step.dotted()),
            i.span,
        );
        n.impl_step = lookup(&self.t.steps, &r.ctx, &i.step);
        if let ImplTarget::Scenario(p) = &i.target {
            n.impl_scenario = lookup(&self.t.scenarios, &r.ctx, p);
        }
        if let Some(s) = n.impl_step.clone() {
            self.edge("impl_of", &anchor, &s);
        }
        if let Some(s) = n.impl_scenario.clone() {
            self.edge("impl_for", &anchor, &s);
        }
        for c in &i.clauses {
            match &c.kind {
                PClauseKind::RequiresPage(p) => {
                    if let Some(a) = lookup(&self.t.pages, &r.ctx, p) {
                        self.edge("requires_page", &anchor, &a);
                        n.pages.push(a);
                    }
                }
                PClauseKind::InNode(p) => {
                    n.node = self.node_ref(&r.ctx, p);
                    if let Some(a) = n.node.clone() {
                        self.edge("in_node", &anchor, &a);
                    }
                }
                _ => {}
            }
        }
        n.clauses = plan_clauses(&anchor, &i.clauses);
        self.nodes.push(n);
    }

    fn page(&mut self, r: &Raw<'_>, p: &crate::plan::Page) {
        let anchor = format!("page/{}", join(&r.ctx, &p.name.text));
        let mut n = node(&self.t, r, anchor.clone(), "page", &p.name.text, p.span);
        for c in &p.clauses {
            match &c.kind {
                PClauseKind::Entry => n.entry = true,
                PClauseKind::From(ps) => {
                    for q in ps {
                        if let Some(a) = lookup(&self.t.pages, &r.ctx, q) {
                            self.edge("navigates", &a, &anchor);
                            n.from.push(a);
                        }
                    }
                }
                _ => {}
            }
        }
        n.clauses = plan_clauses(&anchor, &p.clauses);
        self.nodes.push(n);
    }

    fn one(&mut self, r: &Raw<'_>) {
        match r.item {
            PlanItem::System(s) => {
                let anchor = format!("system/{}", join(&r.ctx, &s.name.text));
                let mut n = node(&self.t, r, anchor, "system", &s.name.text, s.span);
                n.clauses = plan_clauses(&n.anchor, &s.clauses);
                self.nodes.push(n);
            }
            PlanItem::Actor(a) => {
                let anchor = format!("actor/{}", join(&r.ctx, &a.name.text));
                let mut n = node(&self.t, r, anchor.clone(), "actor", &a.name.text, a.span);
                n.actor_kind = Some(a.kind.text.clone());
                for c in &a.clauses {
                    if let PClauseKind::Node(p) = &c.kind {
                        n.node = self.node_ref(&r.ctx, p);
                        if let Some(x) = n.node.clone() {
                            self.edge("actor_node", &anchor, &x);
                        }
                    }
                }
                n.clauses = plan_clauses(&anchor, &a.clauses);
                self.nodes.push(n);
            }
            PlanItem::Goal(g) => self.goal(r, g),
            PlanItem::Step(s) => {
                let anchor = format!("step/{}", join(&r.ctx, &s.target.dotted()));
                let mut n = node(&self.t, r, anchor, "step", &s.target.dotted(), s.span);
                n.owner = if s.is_system() {
                    "system".to_owned()
                } else {
                    lookup(&self.t.actors, &r.ctx, &s.owner()).unwrap_or_else(|| s.owner().dotted())
                };
                n.outcomes = match &s.outcome {
                    Some(o) => o
                        .iter()
                        .map(|x| (x.name.text.clone(), x.payload.as_ref().map(RefPath::dotted)))
                        .collect(),
                    None => vec![("ok".to_owned(), None)],
                };
                n.clauses = plan_clauses(&n.anchor, &s.clauses);
                self.nodes.push(n);
            }
            PlanItem::Scenario(s) => self.scenario(r, s),
            PlanItem::Impl(i) => self.imp(r, i),
            PlanItem::Page(p) => self.page(r, p),
        }
    }
}

impl PlanModel {
    /// Build the planning graph of the root indexed by `idx`.
    pub fn build(idx: &Index<'_>) -> Self {
        let mut order: Vec<usize> = (0..idx.root.files.len()).collect();
        order.sort_by(|&a, &b| {
            idx.root.files[a]
                .parsed
                .path
                .cmp(&idx.root.files[b].parsed.path)
        });
        let mut raws = Vec::new();
        for fi in order {
            let f = &idx.root.files[fi];
            if f.parsed.status != FileStatus::Parsed {
                continue;
            }
            let mut ctx: Vec<String> = if f.mount.is_empty() {
                Vec::new()
            } else {
                f.mount.split('.').map(str::to_owned).collect()
            };
            collect(fi, &f.parsed.items, &mut ctx, &mut raws);
        }
        let mut t = Tables::default();
        for r in &raws {
            register(&mut t, r);
        }
        let mut b = Build {
            idx,
            t,
            nodes: Vec::new(),
            edges: BTreeSet::new(),
        };
        for r in &raws {
            b.one(r);
        }
        let mut nodes = b.nodes;
        let parents: BTreeSet<String> = nodes
            .iter()
            .filter(|n| n.kind == "goal")
            .filter_map(|n| n.parent.clone())
            .collect();
        for n in &mut nodes {
            if n.kind == "goal" {
                n.leaf = !parents.contains(&n.anchor);
            }
        }
        nodes.sort_by(|a, b| a.anchor.cmp(&b.anchor));
        tracing::info!(
            nodes = nodes.len(),
            edges = b.edges.len(),
            "planning graph built"
        );
        Self {
            nodes,
            edges: b.edges.into_iter().collect(),
        }
    }
}
