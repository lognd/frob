//! Planning well-formedness and scenario typing: MDL022-MDL031 (grmb-spec 12.3-12.6, 16.1).
//!
//! The pass runs over the parsed planning items of one model root. It builds name tables
//! (systems, actors, goal variants, steps, scenarios), then types every scenario once, in
//! include order, with a memoized summary `(Eok, E, starts_system)` per scenario.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

// The typing walk is one cohesive pass; splitting it would scatter the shared run state.
#![allow(clippy::too_many_lines, clippy::unused_self)]

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

use crate::ast::{Item, RefPath};
use crate::keywords::is_planning_word;
use crate::model::Index;
use crate::plan::{
    Arm, Chain, Elem, Hop, ImplTarget, PClauseKind, Pattern, PlanItem, ScMember, Scenario, Tail,
};
use crate::span::Span;

/// Actor kinds that need no pack (grmb-spec 11.3).
pub const CORE_ACTOR_KINDS: &[&str] = &["human", "external", "timer", "device"];

/// Realization kinds known without a pack (grmb-spec 11.7); packs add more as atoms.
pub const CORE_REALIZATION_KINDS: &[&str] = &[
    "ui", "cli", "page", "api", "handler", "isr", "driver", "topic", "job", "task", "worker",
    "cron", "rpc", "queue", "consumer", "producer", "command", "view", "route", "endpoint",
];

/// One finding of the planning pass.
#[derive(Clone, Debug)]
pub struct PlanFinding {
    /// The rule id (`MDL022` .. `MDL031`, or `MDL006` for an unresolved planning reference).
    pub rule: &'static str,
    /// Index of the file in the root.
    pub file: usize,
    /// Where.
    pub span: Span,
    /// The message.
    pub message: String,
    /// The stable anchor of the finding.
    pub anchor: String,
    /// True when the model cannot decide the finding (SYS015, SYS016): reported Unresolved.
    pub unresolved: bool,
}

/// Where an item sits: its file, containing prefix and full name.
#[derive(Clone, Debug)]
struct Rec {
    file: usize,
    ctx: Vec<String>,
    full: String,
}

struct StepRec {
    outcomes: Vec<String>,
    is_system: bool,
    /// True when the outcome set is written `open` (MDL033).
    open: bool,
    /// True when the step carries the trailing `idempotent` fact (PLAN016).
    idempotent: bool,
    rec: Rec,
    span: Span,
}

struct ScRec<'a> {
    rec: Rec,
    sc: &'a Scenario,
}

struct Pending {
    rec: Rec,
    span: Span,
    what: &'static str,
}

#[derive(Default)]
struct Tables<'a> {
    systems: BTreeSet<String>,
    steps: BTreeMap<String, StepRec>,
    scenarios: BTreeMap<String, ScRec<'a>>,
    /// Full name of every goal variant, with its system, file and span.
    variants: BTreeMap<String, (Rec, Span)>,
    /// Requires edges between variants: (from full, resolved target, requires path, span).
    pending: Vec<Pending>,
    findings: Vec<PlanFinding>,
    impls: Vec<(Rec, &'a crate::plan::Impl)>,
    keys_by_goal: BTreeMap<String, Vec<(Rec, String, Span)>>,
    reqs: Vec<(Rec, Rec, RefPath)>,
    kinds: Vec<(Rec, crate::ast::Ident)>,
    realizations: Vec<(Rec, crate::ast::Ident)>,
    /// Every system with its record, for the ambient rules.
    system_decls: BTreeMap<String, (Rec, &'a crate::plan::System)>,
    /// Every `system REF;` marker in a mounted file: (record, span, mount prefix, REF) (D157).
    markers: Vec<(Rec, Span, Vec<String>, String)>,
    /// Every arm `retry` with a resolved step and a written bound (AMB004).
    arm_retries: Vec<ArmRetry>,
    /// Include edges `(includer, included)` between scenario full names (AMB004).
    includes: Vec<(String, String)>,
    /// Every goal block with its record, for the coverage rules (PLAN014, PLAN018).
    goal_blocks: Vec<(Rec, &'a crate::plan::GoalBlock)>,
    /// Every actor with its record and the node it sits in, if it names one (SYS015).
    actors: BTreeMap<String, (Rec, Option<RefPath>)>,
}

/// An arm `retry` seen while typing a scenario, kept for the ambient product check.
struct ArmRetry {
    rec: Rec,
    step: String,
    target: String,
    max: crate::ast::Spanned<String>,
    span: Span,
    /// Keys (steps and includes) re-run by the retry, target first; `None` for a handle arm (PLAN016).
    repeated: Option<Vec<String>>,
}

pub(crate) fn join(ctx: &[String], tail: &str) -> String {
    if ctx.is_empty() {
        tail.to_owned()
    } else {
        format!("{}.{tail}", ctx.join("."))
    }
}

/// The system a file's other top-level planning items join, when its top level declares exactly
/// one (braced or by marker); a marker in a mounted file never relocates items (grmb-spec 11.2).
pub(crate) fn file_system(items: &[Item], mounted: bool) -> Option<String> {
    let mut names: BTreeSet<&str> = BTreeSet::new();
    let mut braced = false;
    for item in items {
        if let Item::Plan(p) = item
            && let PlanItem::System(s) = &**p
        {
            names.insert(s.name.text.as_str());
            braced |= s.braced;
        }
    }
    match (names.len(), names.first()) {
        (1, Some(n)) if braced || !mounted => Some((*n).to_owned()),
        _ => None,
    }
}

/// Resolves a mounted file's marker `REF` from mount prefix `mount` (5.3, nearest prefix first);
/// `Some(full)` only when it names a declared system equal to the prefix or a proper prefix of it.
// frob:ticket 01M6D124NJ6QRDAX1QD2V4GRJE
pub(crate) fn marker_target(
    systems: &BTreeSet<String>,
    mount: &[String],
    name: &str,
) -> Option<String> {
    let hit = (0..=mount.len())
        .rev()
        .map(|n| join(&mount[..n], name))
        .find(|k| systems.contains(k))?;
    let m = mount.join(".");
    (m == hit || m.starts_with(&format!("{hit}."))).then_some(hit)
}

/// Resolves `path` from inside `ctx`, nearest enclosing prefix first (grmb-spec 5.3).
pub(crate) fn find<'t, T>(
    map: &'t BTreeMap<String, T>,
    ctx: &[String],
    path: &RefPath,
) -> Option<(&'t String, &'t T)> {
    let dotted = path.dotted();
    let top = if path.rooted { 0 } else { ctx.len() };
    for n in (0..=top).rev() {
        let key = join(&ctx[..n], &dotted);
        if let Some(hit) = map.get_key_value(&key) {
            return Some(hit);
        }
    }
    None
}

impl<'a> Tables<'a> {
    fn raise(&mut self, rule: &'static str, rec: &Rec, span: Span, message: String) {
        self.emit_as(rule, rec, span, message, false);
    }

    fn emit_as(
        &mut self,
        rule: &'static str,
        rec: &Rec,
        span: Span,
        message: String,
        unresolved: bool,
    ) {
        let anchor = format!("plan/{}", rec.full);
        tracing::debug!(rule, %span, %message, unresolved, "plan finding");
        self.findings.push(PlanFinding {
            rule,
            file: rec.file,
            span,
            message,
            anchor,
            unresolved,
        });
    }

    fn reserved(&mut self, rec: &Rec, name: &crate::ast::Ident, what: &str) {
        if is_planning_word(&name.text) && !(name.text == "ok" && what == "outcome variant") {
            self.raise(
                "MDL031",
                rec,
                name.span,
                format!(
                    "`{}` is a planning word and cannot name a {what}",
                    name.text
                ),
            );
        }
    }

    fn collect(&mut self, file: usize, items: &'a [Item], ctx: &mut Vec<String>) {
        for item in items {
            match item {
                Item::Namespace(n) => {
                    ctx.push(n.name.text.clone());
                    self.collect(file, &n.items, ctx);
                    ctx.pop();
                }
                Item::Plan(p) => self.collect_plan(file, p, ctx),
                _ => {}
            }
        }
    }

    /// Collects one file's top level, joining its planning items to the file's one system
    /// (grmb-spec 11.2 membership rule 2, D157).
    fn collect_file(&mut self, file: usize, items: &'a [Item], ctx: &mut Vec<String>) {
        let home = file_system(items, !ctx.is_empty());
        tracing::debug!(file, ?home, "file system membership");
        for item in items {
            match (item, &home) {
                (Item::Plan(p), Some(name)) if !matches!(**p, PlanItem::System(_)) => {
                    ctx.push(name.clone());
                    self.collect_plan(file, p, ctx);
                    ctx.pop();
                }
                // A marker in a mounted file never declares; it is checked once all systems
                // are known (grmb-spec 11.2, D157).
                (Item::Plan(p), _)
                    if !ctx.is_empty() && matches!(&**p, PlanItem::System(s) if !s.braced) =>
                {
                    if let PlanItem::System(s) = &**p {
                        let rec = self.rec(file, ctx, &s.name.text);
                        tracing::debug!(file, name = %s.name.text, "mounted system marker deferred");
                        self.markers
                            .push((rec, s.name.span, ctx.clone(), s.name.text.clone()));
                    }
                }
                _ => self.collect(file, std::slice::from_ref(item), ctx),
            }
        }
    }

    fn rec(&self, file: usize, ctx: &[String], name: &str) -> Rec {
        Rec {
            file,
            ctx: ctx.to_vec(),
            full: join(ctx, name),
        }
    }

    fn pend(&mut self, rec: &Rec, span: Span, what: &'static str) {
        self.pending.push(Pending {
            rec: rec.clone(),
            span,
            what,
        });
    }

    fn collect_plan(&mut self, file: usize, p: &'a PlanItem, ctx: &mut Vec<String>) {
        match p {
            PlanItem::System(s) => {
                let rec = self.rec(file, ctx, &s.name.text);
                self.systems.insert(rec.full.clone());
                match self.system_decls.get(&rec.full) {
                    Some((first, prev)) if prev.braced && s.braced => {
                        let msg = format!(
                            "system `{}` already has a braced declaration (file {}); a system has at most one",
                            rec.full, first.file
                        );
                        self.raise("MDL001", &rec, s.name.span, msg);
                    }
                    // a marker never displaces a declaration already recorded
                    Some((_, prev)) if prev.braced || !s.braced => {}
                    _ => {
                        self.system_decls.insert(rec.full.clone(), (rec.clone(), s));
                    }
                }
                ctx.push(s.name.text.clone());
                self.collect(file, &s.items, ctx);
                ctx.pop();
            }
            PlanItem::Actor(a) => {
                let rec = self.rec(file, ctx, &a.name.text);
                self.pend(&rec, a.name.span, "actor");
                self.reserved(&rec, &a.name, "actor");
                let node = a.clauses.iter().find_map(|c| match &c.kind {
                    PClauseKind::Node(p) | PClauseKind::InNode(p) => Some(p.clone()),
                    _ => None,
                });
                self.actors.insert(rec.full.clone(), (rec.clone(), node));
                self.kind_check(&rec, &a.kind, &a.clauses);
            }
            PlanItem::Goal(g) => {
                let rec = self.rec(file, ctx, &g.path.dotted());
                self.pend(&rec, g.path.span, "goal");
                if let Some(k) = &g.key {
                    self.keys_by_goal
                        .entry(rec.full.clone())
                        .or_default()
                        .push((rec.clone(), k.text.clone(), k.span));
                }
                self.goal_blocks.push((rec.clone(), g));
                for v in g
                    .variants
                    .iter()
                    .chain(g.groups.iter().flat_map(|o| o.variants.iter()))
                {
                    let vfull = join(&rec_ctx(&rec), &v.name.text);
                    let vrec = Rec {
                        file,
                        ctx: rec.full.split('.').map(str::to_owned).collect(),
                        full: vfull.clone(),
                    };
                    self.reserved(&vrec, &v.name, "goal variant");
                    for r in &v.requires {
                        self.reqs.push((vrec.clone(), vrec.clone(), r.clone()));
                    }
                    self.variants.insert(vfull, (vrec, v.name.span));
                }
            }
            PlanItem::Step(s) => {
                let rec = self.rec(file, ctx, &s.target.dotted());
                self.pend(&rec, s.target.span, "step");
                let mut outcomes: Vec<String> = match &s.outcome {
                    Some(o) => o.iter().map(|x| x.name.text.clone()).collect(),
                    None => vec!["ok".to_owned()],
                };
                if let Some(o) = &s.outcome {
                    for x in o {
                        self.reserved(&rec, &x.name, "outcome variant");
                    }
                }
                outcomes.dedup();
                if let Some(last) = s.target.segments.last() {
                    let id = crate::ast::Ident {
                        text: last.clone(),
                        raw: false,
                        span: s.target.span,
                    };
                    self.reserved(&rec, &id, "step");
                }
                self.steps.insert(
                    rec.full.clone(),
                    StepRec {
                        outcomes,
                        is_system: s.is_system(),
                        open: s.open,
                        idempotent: s.idempotent,
                        span: s.target.span,
                        rec: rec.clone(),
                    },
                );
            }
            PlanItem::Scenario(sc) => {
                let rec = self.rec(file, ctx, &sc.name.text);
                self.pend(&rec, sc.name.span, "scenario");
                self.reserved(&rec, &sc.name, "scenario");
                if let Some(f) = &sc.fails {
                    for v in f {
                        self.reserved(&rec, v, "error variant");
                    }
                }
                self.scenarios.insert(rec.full.clone(), ScRec { rec, sc });
            }
            PlanItem::Impl(i) => {
                let rec = self.rec(file, ctx, &i.step.dotted());
                self.pend(&rec, i.step.span, "impl");
                self.realization_check(&rec, &i.clauses);
                self.impls.push((rec, i));
            }
            PlanItem::Page(pg) => {
                let rec = self.rec(file, ctx, &pg.name.text);
                self.pend(&rec, pg.name.span, "page");
                self.reserved(&rec, &pg.name, "page");
                self.realization_check(&rec, &pg.clauses);
            }
        }
    }

    fn kind_check(
        &mut self,
        rec: &Rec,
        kind: &crate::ast::Ident,
        _clauses: &[crate::plan::PClause],
    ) {
        self.kinds.push((rec.clone(), kind.clone()));
    }

    fn realization_check(&mut self, rec: &Rec, clauses: &[crate::plan::PClause]) {
        for c in clauses {
            if let PClauseKind::Realization(r) = &c.kind {
                self.realizations.push((rec.clone(), r.kind.clone()));
            }
        }
    }
}

fn rec_ctx(rec: &Rec) -> Vec<String> {
    // The goal path is part of `full`, so variants hang off `full` directly.
    vec![rec.full.clone()]
}

/// The summary of a typed scenario (grmb-spec 12.3, 12.4).
#[derive(Clone, Debug)]
struct Summary {
    eok: bool,
    errs: BTreeSet<String>,
    starts_system: bool,
    collected: Vec<CollectedPair>,
}

/// One collected `(step, variant)` pair of a scenario and what takes it (grmb-spec 12.4).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CollectedPair {
    /// Anchor of the collecting element: `step/NAME`, or `scenario/NAME` for an include.
    pub step: String,
    /// The collected outcome variant.
    pub variant: String,
    /// Anchor of the handle arm that takes the pair, or `None` when it propagates.
    pub handled_by: Option<String>,
}

/// The error facts of one scenario: its error set `E(s)` and the pairs it collects.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ScenarioErrors {
    /// `E(s)`: the declared `fails with` set, else the variants of every `end err`, sorted.
    pub error_set: Vec<String>,
    /// `Col(s)` then `Colh(s)`, deduplicated, in first-collected order.
    pub collected: Vec<CollectedPair>,
}

#[derive(Clone, Debug)]
struct Pair {
    label: String,
    key: String,
    anchor: String,
    var: String,
    span: Span,
}

struct ElemInfo {
    key: String,
    anchor: String,
    label: String,
    vars: Vec<String>,
    span: Span,
    is_step: bool,
    /// True when the matched step's outcome set is `open` (MDL033).
    open: bool,
}

struct ArmCtx {
    var: Option<String>,
    handle: bool,
}

struct Run {
    rec: Rec,
    f: Option<Vec<String>>,
    col: Vec<Pair>,
    colh: Vec<Pair>,
    errs: BTreeSet<String>,
    eok: bool,
    main_keys: Vec<String>,
    uses: BTreeSet<String>,
}

struct Analyzer<'a, 't> {
    t: &'t mut Tables<'a>,
    degraded: bool,
    memo: HashMap<String, Option<Summary>>,
    busy: HashSet<String>,
    uses: HashMap<String, BTreeSet<String>>,
}

impl Analyzer<'_, '_> {
    fn raise(&mut self, rule: &'static str, rec: &Rec, span: Span, message: String) {
        self.t.raise(rule, rec, span, message);
    }

    fn unresolved(&mut self, rec: &Rec, path: &RefPath, what: &str) {
        if !self.degraded {
            let msg = format!("`{}` does not resolve to a {what}", path.written());
            self.raise("MDL006", rec, path.span, msg);
        }
    }

    fn elem(&mut self, run: &mut Run, e: &Elem) -> Option<ElemInfo> {
        let path = e.path();
        let ctx = run.rec.ctx.clone();
        match e {
            Elem::Step(p) => {
                let Some((key, st)) = find(&self.t.steps, &ctx, p) else {
                    self.unresolved(&run.rec.clone(), p, "step");
                    return None;
                };
                let key = key.clone();
                let vars = st.outcomes.clone();
                let open = st.open;
                run.uses.insert(key.clone());
                Some(ElemInfo {
                    anchor: format!("step/{key}"),
                    key,
                    label: p.dotted(),
                    vars,
                    span: path.span,
                    is_step: true,
                    open,
                })
            }
            Elem::Include(p) => {
                let Some((key, _)) = find(&self.t.scenarios, &ctx, p) else {
                    self.unresolved(&run.rec.clone(), p, "scenario");
                    return None;
                };
                let key = key.clone();
                self.t.includes.push((run.rec.full.clone(), key.clone()));
                if self.busy.contains(&key) {
                    self.raise(
                        "MDL026",
                        &run.rec.clone(),
                        p.span,
                        format!(
                            "`include {}` closes a cycle in the include graph",
                            p.written()
                        ),
                    );
                    return None;
                }
                let sum = self.analyze(&key)?;
                let mut vars = Vec::new();
                if sum.eok {
                    vars.push("ok".to_owned());
                }
                vars.extend(sum.errs.iter().cloned());
                Some(ElemInfo {
                    anchor: format!("scenario/{key}"),
                    key,
                    label: p.dotted(),
                    vars,
                    span: p.span,
                    is_step: false,
                    open: false,
                })
            }
        }
    }

    fn analyze(&mut self, key: &str) -> Option<Summary> {
        if let Some(s) = self.memo.get(key) {
            return s.clone();
        }
        let sc_ref: &Scenario = self.t.scenarios.get(key)?.sc;
        let rec = self.t.scenarios.get(key)?.rec.clone();
        self.busy.insert(key.to_owned());
        tracing::debug!(scenario = key, "typing scenario");
        for r in &sc_ref.realizes {
            if find(&self.t.variants, &rec.ctx, r).is_none() && !is_non_goal(self.t, &rec, r) {
                self.unresolved(&rec, r, "goal variant");
            }
        }
        let mut run = Run {
            rec: rec.clone(),
            f: sc_ref
                .fails
                .as_ref()
                .map(|v| v.iter().map(|i| i.text.clone()).collect()),
            col: Vec::new(),
            colh: Vec::new(),
            errs: BTreeSet::new(),
            eok: false,
            main_keys: Vec::new(),
            uses: BTreeSet::new(),
        };
        let chains: Vec<&Chain> = sc_ref
            .members
            .iter()
            .filter_map(|m| match m {
                ScMember::Chain(_, c) => Some(c),
                _ => None,
            })
            .collect();
        let handles: Vec<&crate::plan::Handle> = sc_ref
            .members
            .iter()
            .filter_map(|m| match m {
                ScMember::Handle(h) => Some(h),
                _ => None,
            })
            .collect();
        let mut starts_system = false;
        match chains.as_slice() {
            [] => self.raise(
                "MDL026",
                &rec,
                sc_ref.name.span,
                format!("scenario `{}` has no main chain", sc_ref.name.text),
            ),
            [main, rest @ ..] => {
                for extra in rest {
                    self.raise(
                        "MDL031",
                        &rec,
                        extra.span,
                        format!(
                            "scenario `{}` has more than one main chain",
                            sc_ref.name.text
                        ),
                    );
                }
                starts_system = self.start_check(&mut run, main);
                let mut path = Vec::new();
                self.walk(&mut run, main, false, &mut path, None);
                run.main_keys = path;
            }
        }
        if let Some((_, extra)) = handles.split_first() {
            for h in extra {
                self.raise(
                    "MDL031",
                    &rec,
                    h.span,
                    format!("scenario `{}` has more than one handle", sc_ref.name.text),
                );
            }
        }
        let mut collected = self.resolve_collected(&mut run, handles.first().copied());
        let colh = std::mem::take(&mut run.colh);
        for p in colh {
            let row = CollectedPair {
                step: p.anchor.clone(),
                variant: p.var.clone(),
                handled_by: None,
            };
            if !collected.contains(&row) {
                collected.push(row);
            }
            if !self.declared(&run, &p.var) {
                self.raise(
                    "MDL023",
                    &rec,
                    p.span,
                    format!(
                        "`{}.{}` collected inside a handle arm must be in `fails with`",
                        p.label, p.var
                    ),
                );
            }
        }
        let errs = match &run.f {
            Some(f) => f.iter().cloned().collect(),
            None => run.errs.clone(),
        };
        let sum = Summary {
            eok: run.eok,
            errs,
            starts_system,
            collected,
        };
        self.busy.remove(key);
        self.uses.insert(key.to_owned(), run.uses);
        self.memo.insert(key.to_owned(), Some(sum.clone()));
        Some(sum)
    }

    fn declared(&self, run: &Run, var: &str) -> bool {
        run.f.as_ref().is_some_and(|f| f.iter().any(|x| x == var))
    }

    /// MDL029: the main chain must start with an actor step (grmb-spec 12.6).
    fn start_check(&mut self, run: &mut Run, main: &Chain) -> bool {
        let first = match main.links.first() {
            Some((e, _)) => e,
            None => match &main.tail {
                Tail::Match { elem, .. } | Tail::Open(elem) => elem,
                _ => return false,
            },
        };
        let sys = match first {
            Elem::Step(p) => {
                let ctx = run.rec.ctx.clone();
                find(&self.t.steps, &ctx, p).is_some_and(|(_, s)| s.is_system)
            }
            Elem::Include(p) => {
                let ctx = run.rec.ctx.clone();
                let key = find(&self.t.scenarios, &ctx, p).map(|(k, _)| k.clone());
                key.and_then(|k| {
                    if self.busy.contains(&k) {
                        None
                    } else {
                        self.analyze(&k)
                    }
                })
                .is_some_and(|s| s.starts_system)
            }
        };
        if sys {
            self.raise(
                "MDL029",
                &run.rec.clone(),
                first.path().span,
                format!(
                    "scenario starts with `{}`, a system step; start with an actor step",
                    first.path().written()
                ),
            );
        }
        sys
    }

    fn end_err(&mut self, run: &mut Run, var: &str, span: Span) {
        if run.f.is_some() && !self.declared(run, var) {
            self.raise(
                "MDL023",
                &run.rec.clone(),
                span,
                format!("`end err({var})` is not in the declared `fails with` set"),
            );
        }
        run.errs.insert(var.to_owned());
    }

    fn walk(
        &mut self,
        run: &mut Run,
        chain: &Chain,
        handle: bool,
        path: &mut Vec<String>,
        arm: Option<&ArmCtx>,
    ) {
        let rec = run.rec.clone();
        for (e, hop) in &chain.links {
            let Some(info) = self.elem(run, e) else {
                continue;
            };
            path.push(info.key.clone());
            let non_ok: Vec<&String> = info.vars.iter().filter(|v| *v != "ok").collect();
            let has_ok = info.vars.iter().any(|v| v == "ok");
            match hop {
                Hop::Seq if !(non_ok.is_empty() && has_ok) => {
                    self.raise(
                        "MDL024",
                        &rec,
                        info.span,
                        format!(
                            "`->` after `{}`, whose outcomes are {{ {} }}; use `-!>` or `=>`",
                            info.label,
                            info.vars.join(", ")
                        ),
                    );
                }
                Hop::Seq => {}
                Hop::Try if !has_ok => {
                    self.raise(
                        "MDL024",
                        &rec,
                        info.span,
                        format!("`-!>` after `{}`, which has no `ok` outcome", info.label),
                    );
                }
                Hop::Try => {
                    for v in non_ok {
                        let pair = Pair {
                            label: info.label.clone(),
                            key: info.key.clone(),
                            anchor: info.anchor.clone(),
                            var: v.clone(),
                            span: info.span,
                        };
                        if handle {
                            run.colh.push(pair);
                        } else {
                            run.col.push(pair);
                        }
                    }
                }
            }
        }
        match &chain.tail {
            Tail::EndOk(_) => run.eok = true,
            // frob:ticket 01M6CFZKEKAJM0YF9FB5820W3Y
            Tail::Sorry(_) => {}
            Tail::EndErr(v) => self.end_err(run, &v.text, v.span),
            Tail::Open(e) => {
                let _ = self.elem(run, e);
                self.raise(
                    "MDL026",
                    &rec,
                    chain.span,
                    "chain ends without `end ok`, `end err(..)`, `retry` or `=>`".to_owned(),
                );
            }
            Tail::Match { elem, arms } => {
                let Some(info) = self.elem(run, elem) else {
                    for a in arms {
                        self.walk(
                            run,
                            &a.chain,
                            handle,
                            &mut path.clone(),
                            Some(&arm_ctx(a, handle)),
                        );
                    }
                    return;
                };
                path.push(info.key.clone());
                let pairs: Vec<Pair> = info
                    .vars
                    .iter()
                    .map(|v| Pair {
                        label: info.label.clone(),
                        key: info.key.clone(),
                        anchor: info.anchor.clone(),
                        var: v.clone(),
                        span: info.span,
                    })
                    .collect();
                let best = self.match_arms(run, arms, &pairs);
                let missing: Vec<String> = pairs
                    .iter()
                    .zip(&best)
                    .filter(|(_, b)| b.is_none())
                    .map(|(p, _)| p.var.clone())
                    .collect();
                if !missing.is_empty() {
                    self.raise(
                        "MDL022",
                        &rec,
                        info.span,
                        format!(
                            "`=>` on `{}` does not match: {}",
                            info.label,
                            missing.join(", ")
                        ),
                    );
                }
                self.unknown_arms(&rec, &info, arms, &pairs, &best);
                let _ = info.is_step;
                for a in arms {
                    self.walk(
                        run,
                        &a.chain,
                        handle,
                        &mut path.clone(),
                        Some(&arm_ctx(a, handle)),
                    );
                }
            }
            Tail::Retry {
                step,
                max,
                otherwise,
                span,
                ..
            } => {
                self.retry(
                    run,
                    handle,
                    path,
                    arm,
                    step,
                    max.as_ref(),
                    otherwise.as_deref(),
                    *span,
                );
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn retry(
        &mut self,
        run: &mut Run,
        handle: bool,
        path: &[String],
        arm: Option<&ArmCtx>,
        step: &RefPath,
        max: Option<&crate::ast::Spanned<String>>,
        otherwise: Option<&Chain>,
        span: Span,
    ) {
        let rec = run.rec.clone();
        let ctx = rec.ctx.clone();
        let target = find(&self.t.steps, &ctx, step).map(|(k, _)| k.clone());
        if target.is_none() {
            self.unresolved(&rec, step, "step");
        }
        let Some(arm) = arm else {
            self.raise(
                "MDL027",
                &rec,
                span,
                "`retry` is only allowed as the tail of an arm chain".to_owned(),
            );
            if let Some(c) = otherwise {
                self.walk(run, c, handle, &mut path.to_vec(), None);
            }
            return;
        };
        match max {
            None => self.raise("MDL027", &rec, span, "`retry` needs `max N`".to_owned()),
            Some(m) => {
                if m.value.parse::<u64>().map_or(true, |n| n < 1) {
                    self.raise(
                        "MDL027",
                        &rec,
                        m.span,
                        format!("`max {}` must be a number of at least 1", m.value),
                    );
                }
            }
        }
        if let (Some(k), Some(m)) = (&target, max) {
            self.t.arm_retries.push(ArmRetry {
                rec: rec.clone(),
                step: step.written(),
                target: k.clone(),
                max: m.clone(),
                span: step.span,
                repeated: (!arm.handle)
                    .then(|| path.iter().skip_while(|p| *p != k).cloned().collect()),
            });
        }
        if let Some(k) = &target {
            run.uses.insert(k.clone());
            let on_path = if arm.handle {
                run.main_keys.contains(k)
            } else {
                path.contains(k)
            };
            if !on_path {
                self.raise(
                    "MDL027",
                    &rec,
                    step.span,
                    format!("`retry {}` is not on the path to this arm", step.written()),
                );
            }
        }
        match (otherwise, &arm.var) {
            (Some(c), _) => self.walk(run, c, handle, &mut path.to_vec(), None),
            (None, Some(v)) => self.end_err(run, v, span),
            (None, None) => self.raise(
                "MDL027",
                &rec,
                span,
                "a `_` arm needs an explicit `else` after `retry`".to_owned(),
            ),
        }
    }

    /// Matches `pairs` against `arms`; returns the best arm per pair and reports MDL025/MDL028.
    fn match_arms(&mut self, run: &Run, arms: &[Arm], pairs: &[Pair]) -> Vec<Option<usize>> {
        let rec = run.rec.clone();
        let mut used = vec![false; arms.len()];
        let mut best = Vec::with_capacity(pairs.len());
        for p in pairs {
            let specs: Vec<Option<u8>> = arms.iter().map(|a| self.spec(run, a, p)).collect();
            let top = specs.iter().flatten().max().copied();
            let hits: Vec<usize> = specs
                .iter()
                .enumerate()
                .filter(|(_, s)| top.is_some() && **s == top)
                .map(|(i, _)| i)
                .collect();
            if hits.len() > 1 {
                self.raise(
                    "MDL025",
                    &rec,
                    arms[hits[1]].span,
                    format!(
                        "two arms of equal specificity match `{}.{}`",
                        p.label, p.var
                    ),
                );
                for h in &hits {
                    used[*h] = true;
                }
            }
            best.push(hits.first().copied());
            if let Some(h) = hits.first() {
                used[*h] = true;
            }
        }
        for (i, a) in arms.iter().enumerate() {
            if let Pattern::Wild(sp) = &a.pattern {
                self.raise(
                    "MDL028",
                    &rec,
                    *sp,
                    "a `_` arm hides variants added later; name each variant".to_owned(),
                );
            }
            if !used[i] && !is_unknown(a) {
                self.raise(
                    "MDL025",
                    &rec,
                    a.span,
                    format!(
                        "arm `{}` matches no pair of its domain (unknown, not collected, or shadowed)",
                        a.pattern.written()
                    ),
                );
            }
        }
        best
    }

    /// MDL032 (lone or premature `unknown` arm) and MDL033 (`open` match with no catch-all).
    ///
    /// frob:ticket 01M6P033KB0H2X52QC73P40F6M
    fn unknown_arms(
        &mut self,
        rec: &Rec,
        info: &ElemInfo,
        arms: &[Arm],
        pairs: &[Pair],
        best: &[Option<usize>],
    ) {
        let unknown = arms.iter().find(|a| is_unknown(a));
        if let Some(u) = unknown {
            let missing: Vec<&str> = pairs
                .iter()
                .zip(best)
                .filter(|(_, b)| b.is_none())
                .map(|(p, _)| p.var.as_str())
                .collect();
            if arms.len() == 1 {
                tracing::debug!(label = %info.label, "MDL032: lone `unknown` arm");
                self.raise(
                    "MDL032",
                    rec,
                    u.span,
                    format!("`unknown` is the only arm of the match on `{}`", info.label),
                );
            } else if !missing.is_empty() {
                tracing::debug!(label = %info.label, "MDL032: known variant without an arm");
                self.raise(
                    "MDL032",
                    rec,
                    u.span,
                    format!(
                        "`unknown` arm on `{}` but known variants have no arm: {}",
                        info.label,
                        missing.join(", ")
                    ),
                );
            }
        }
        let catch_all =
            unknown.is_some() || arms.iter().any(|a| matches!(a.pattern, Pattern::Wild(_)));
        if info.open && !catch_all {
            tracing::debug!(label = %info.label, "MDL033: open match without catch-all");
            self.raise(
                "MDL033",
                rec,
                info.span,
                format!(
                    "`=>` on the `open` outcome set of `{}` needs an `unknown` or `_` arm",
                    info.label
                ),
            );
        }
    }

    fn spec(&self, run: &Run, arm: &Arm, pair: &Pair) -> Option<u8> {
        match &arm.pattern {
            Pattern::Wild(_) => Some(0),
            Pattern::Path(p) => {
                let (var, prefix) = p.segments.split_last()?;
                if *var != pair.var {
                    return None;
                }
                if prefix.is_empty() {
                    return Some(1);
                }
                let pre = RefPath {
                    rooted: p.rooted,
                    segments: prefix.to_vec(),
                    span: p.span,
                };
                let ctx = &run.rec.ctx;
                let key = find(&self.t.steps, ctx, &pre)
                    .map(|(k, _)| k)
                    .or_else(|| find(&self.t.scenarios, ctx, &pre).map(|(k, _)| k))?;
                (*key == pair.key).then_some(2)
            }
        }
    }

    /// Handles or propagates every collected pair (grmb-spec 12.4).
    fn resolve_collected(
        &mut self,
        run: &mut Run,
        handle: Option<&crate::plan::Handle>,
    ) -> Vec<CollectedPair> {
        let rec = run.rec.clone();
        let mut pairs: Vec<Pair> = Vec::new();
        let mut seen = HashSet::new();
        for p in &run.col {
            if seen.insert((p.key.clone(), p.var.clone())) {
                pairs.push(p.clone());
            }
        }
        let arms: &[Arm] = handle.map_or(&[], |h| h.arms.as_slice());
        let best = self.match_arms(run, arms, &pairs);
        let rows: Vec<CollectedPair> = pairs
            .iter()
            .zip(&best)
            .map(|(p, b)| CollectedPair {
                step: p.anchor.clone(),
                variant: p.var.clone(),
                handled_by: b.map(|i| arm_anchor(&rec, &arms[i])),
            })
            .collect();
        for (p, b) in pairs.iter().zip(&best) {
            if b.is_none() && !self.declared(run, &p.var) {
                self.raise(
                    "MDL023",
                    &rec,
                    p.span,
                    format!(
                        "`{}.{}` is collected but neither handled nor listed in `fails with`",
                        p.label, p.var
                    ),
                );
            }
        }
        for a in arms {
            self.walk(
                run,
                &a.chain,
                true,
                &mut run.main_keys.clone(),
                Some(&arm_ctx(a, true)),
            );
        }
        rows
    }
}

/// True for the `unknown` arm (a lone-segment `unknown` path pattern).
fn is_unknown(a: &Arm) -> bool {
    matches!(&a.pattern, Pattern::Path(p) if p.segments.len() == 1 && p.segments[0] == "unknown")
}

/// `scenario/S/handle[PATTERN]`, the anchor the fold gives a handle arm (grmb-spec 9.4).
fn arm_anchor(rec: &Rec, arm: &Arm) -> String {
    format!("scenario/{}/handle[{}]", rec.full, arm.pattern.written())
}

fn arm_ctx(a: &Arm, handle: bool) -> ArmCtx {
    ArmCtx {
        var: match &a.pattern {
            Pattern::Path(p) => p.segments.last().cloned(),
            Pattern::Wild(_) => None,
        },
        handle,
    }
}

/// Runs the planning checks over the model root of `idx` (MDL022-MDL031).
///
/// `pack_atoms` are the vocabulary words enabled packs contribute (actor and realization kinds).
pub fn plan_findings(idx: &Index<'_>, pack_atoms: &BTreeSet<String>) -> Vec<PlanFinding> {
    analyze_plan(idx, pack_atoms).0
}

/// The error set and collected pairs of every typed scenario, by scenario anchor (`scenario/S`).
pub fn scenario_errors(idx: &Index<'_>) -> BTreeMap<String, ScenarioErrors> {
    analyze_plan(idx, &BTreeSet::new()).1
}

/// One planning pass: the findings and the per-scenario error facts it computed on the way.
fn analyze_plan(
    idx: &Index<'_>,
    pack_atoms: &BTreeSet<String>,
) -> (Vec<PlanFinding>, BTreeMap<String, ScenarioErrors>) {
    let mut t = Tables::default();
    let mut order: Vec<usize> = (0..idx.root.files.len()).collect();
    order.sort_by(|&a, &b| {
        idx.root.files[a]
            .parsed
            .path
            .cmp(&idx.root.files[b].parsed.path)
    });
    for fi in order {
        let f = &idx.root.files[fi];
        if f.parsed.status != crate::ast::FileStatus::Parsed {
            continue;
        }
        let mut ctx: Vec<String> = if f.mount.is_empty() {
            Vec::new()
        } else {
            f.mount.split('.').map(str::to_owned).collect()
        };
        t.collect_file(fi, &f.parsed.items, &mut ctx);
    }
    structure(&mut t, pack_atoms);
    let keys: Vec<String> = t.scenarios.keys().cloned().collect();
    let mut an = Analyzer {
        t: &mut t,
        degraded: idx.degraded,
        memo: HashMap::new(),
        busy: HashSet::new(),
        uses: HashMap::new(),
    };
    for k in &keys {
        let _ = an.analyze(k);
    }
    let uses = std::mem::take(&mut an.uses);
    let degraded = an.degraded;
    let errors: BTreeMap<String, ScenarioErrors> = std::mem::take(&mut an.memo)
        .into_iter()
        .filter_map(|(k, s)| {
            let s = s?;
            Some((
                format!("scenario/{k}"),
                ScenarioErrors {
                    error_set: s.errs.into_iter().collect(),
                    collected: s.collected,
                },
            ))
        })
        .collect();
    ambient_checks(&mut t, idx);
    plan_rules(&mut t, &uses, degraded);
    plan016(&mut t, &uses);
    outcome_maps(&mut t);
    sys_flow(&mut t, idx, degraded);
    impl_checks(&mut t, &uses, degraded);
    tracing::debug!(
        findings = t.findings.len(),
        scenarios = errors.len(),
        "planning pass done"
    );
    (t.findings, errors)
}

/// True when `path` names a `non_goal` of the system enclosing `rec` (PLAN027, not MDL006).
fn is_non_goal(t: &Tables<'_>, rec: &Rec, path: &RefPath) -> bool {
    let Some(sys) = system_of(t, rec) else {
        return false;
    };
    let Some((_, decl)) = t.system_decls.get(&sys) else {
        return false;
    };
    let dotted = path.dotted();
    non_goals_of(decl).any(|n| n.text == dotted || path.segments.last() == Some(&n.text))
}

/// The `non_goal` names a system declares.
fn non_goals_of(sys: &crate::plan::System) -> impl Iterator<Item = &crate::ast::Ident> {
    sys.clauses.iter().filter_map(|c| match &c.kind {
        PClauseKind::NonGoal(n) => Some(n),
        _ => None,
    })
}

/// Calls `f` on `chain` and on every chain nested in its arms or `retry .. else`.
fn visit_chain<'c>(
    chain: &'c Chain,
    arm: Option<&'c Arm>,
    f: &mut dyn FnMut(&'c Chain, Option<&'c Arm>),
) {
    f(chain, arm);
    match &chain.tail {
        Tail::Match { arms, .. } => {
            for a in arms {
                visit_chain(&a.chain, Some(a), f);
            }
        }
        Tail::Retry {
            otherwise: Some(o), ..
        } => visit_chain(o, None, f),
        _ => {}
    }
}

/// Calls `f` on every chain of `sc`, main chains and `handle` arms alike.
fn visit_scenario<'c>(sc: &'c Scenario, f: &mut dyn FnMut(&'c Chain, Option<&'c Arm>)) {
    for m in &sc.members {
        match m {
            ScMember::Chain(_, c) => visit_chain(c, None, f),
            ScMember::Handle(h) => {
                for a in &h.arms {
                    visit_chain(&a.chain, Some(a), f);
                }
            }
            ScMember::Clause(_) => {}
        }
    }
}

/// True when goal paths `a` and `b` are equal or one is a dotted ancestor of the other.
fn related(a: &str, b: &str) -> bool {
    a == b || a.starts_with(&format!("{b}.")) || b.starts_with(&format!("{a}."))
}

/// PLAN012..PLAN027: coverage of goals, steps and impls, `sorry` holes and `non_goal`s.
// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ
fn plan_rules(t: &mut Tables<'_>, uses: &HashMap<String, BTreeSet<String>>, degraded: bool) {
    let mut out: Vec<AmbFinding> = Vec::new();
    let reached: BTreeSet<&String> = uses.values().flatten().collect();
    let mut realized: BTreeSet<String> = BTreeSet::new();
    for (key, sr) in &t.scenarios {
        for r in &sr.sc.realizes {
            if let Some((k, _)) = find(&t.variants, &sr.rec.ctx, r) {
                realized.insert(k.clone());
            } else if is_non_goal(t, &sr.rec, r) {
                let msg = format!(
                    "scenario `{key}` realizes `{}`, which the system declares a `non_goal`",
                    r.written()
                );
                out.push(("PLAN027", sr.rec.clone(), r.span, msg));
            }
        }
        scenario_holes(t, key, sr, &mut out);
    }
    for (rec, imp) in &t.impls {
        let ImplTarget::Any(span) = imp.target else {
            continue;
        };
        if let Some((step, _)) = find(&t.steps, &rec.ctx, &imp.step)
            && !degraded
            && !reached.contains(step)
        {
            let msg = format!(
                "`impl {} for *` covers a step no scenario uses",
                imp.step.written()
            );
            out.push(("PLAN013", rec.clone(), span, msg));
        }
    }
    if !degraded {
        for (key, st) in &t.steps {
            let impl_hit = t
                .impls
                .iter()
                .any(|(r, i)| find(&t.steps, &r.ctx, &i.step).is_some_and(|(k, _)| k == key));
            if !reached.contains(key) && !impl_hit {
                let msg = format!("step `{key}` is reached by no scenario and has no impl");
                out.push(("PLAN014", st.rec.clone(), st.span, msg));
            }
        }
    }
    goal_shape(t, &realized, degraded, &mut out);
    for (rule, rec, span, msg) in out {
        t.raise(rule, &rec, span, msg);
    }
}

/// PLAN012 and PLAN015 for one scenario: `end ok` arms with no effect, and `sorry` holes.
fn scenario_holes(t: &Tables<'_>, key: &str, sr: &ScRec<'_>, out: &mut Vec<AmbFinding>) {
    visit_scenario(sr.sc, &mut |chain, arm| {
        if let Some(a) = arm
            && let Pattern::Path(p) = &a.pattern
            && p.segments.last().is_some_and(|s| s != "ok")
            && chain.links.is_empty()
            && matches!(chain.tail, Tail::EndOk(_))
        {
            let msg = format!(
                "arm `{}` of scenario `{key}` ends `end ok` with no effect on a non-ok outcome",
                a.pattern.written()
            );
            out.push(("PLAN012", sr.rec.clone(), a.span, msg));
        }
        if let Tail::Sorry(d) = &chain.tail {
            let mut tainted: BTreeSet<String> = BTreeSet::new();
            let mut todo = vec![key.to_owned()];
            while let Some(cur) = todo.pop() {
                for (from, to) in &t.includes {
                    if *to == cur && tainted.insert(from.clone()) {
                        todo.push(from.clone());
                    }
                }
            }
            let dep = if tainted.is_empty() {
                String::new()
            } else {
                format!(
                    "; tainted: {}",
                    tainted.into_iter().collect::<Vec<_>>().join(", ")
                )
            };
            let msg = format!("`sorry` hole in scenario `{key}`{dep}");
            out.push(("PLAN015", sr.rec.clone(), d.span, msg));
        }
    });
}

/// PLAN014 (one-variant refinement or `one_of`) and PLAN018 (unrealized `one_of`).
fn goal_shape(
    t: &Tables<'_>,
    realized: &BTreeSet<String>,
    degraded: bool,
    out: &mut Vec<AmbFinding>,
) {
    // Per refined goal: (variants in all, variants written directly, record, span).
    let mut counts: BTreeMap<&str, (usize, usize, &Rec, Span)> = BTreeMap::new();
    for (rec, g) in &t.goal_blocks {
        if t.variants.contains_key(&rec.full) {
            let e = counts
                .entry(rec.full.as_str())
                .or_insert((0, 0, rec, g.path.span));
            e.0 += g.variants.len() + g.groups.iter().map(|o| o.variants.len()).sum::<usize>();
            e.1 += g.variants.len();
        }
        for o in &g.groups {
            if o.exclusive {
                let mut seen = BTreeSet::new();
                for v in &o.variants {
                    if !seen.insert(v.name.text.as_str()) {
                        tracing::debug!(alt = %v.name.text, "MDL034: duplicate exclusive alternative");
                        let msg = format!(
                            "alternative `{}` appears twice in an `exclusive` `one_of` under `{}`",
                            v.name.text, rec.full
                        );
                        out.push(("MDL034", rec.clone(), v.span, msg));
                    }
                }
            }
            if o.variants.len() == 1 {
                let msg = format!("`one_of` under `{}` has a single alternative", rec.full);
                out.push(("PLAN014", rec.clone(), o.span, msg));
            }
            let alts: Vec<String> = o
                .variants
                .iter()
                .map(|v| join(&rec_ctx(rec), &v.name.text))
                .collect();
            let hit = alts.iter().any(|a| realized.iter().any(|r| related(a, r)));
            if !hit && !degraded && !o.variants.is_empty() {
                let msg = format!(
                    "no scenario realizes any alternative of the `one_of` under `{}`",
                    rec.full
                );
                out.push(("PLAN018", rec.clone(), o.span, msg));
            }
        }
    }
    for (full, (n, direct, rec, span)) in counts {
        // A lone `one_of` alternative is already reported above.
        if n == 1 && direct == 1 {
            let msg = format!("goal `{full}` is refined into a single variant");
            out.push(("PLAN014", rec.clone(), span, msg));
        }
    }
}

/// The checks that need only the name tables: enclosure, kinds, goal keys, requires.
fn structure(t: &mut Tables<'_>, pack_atoms: &BTreeSet<String>) {
    for (rec, span, mount, name) in std::mem::take(&mut t.markers) {
        if marker_target(&t.systems, &mount, &name).is_none() {
            let msg = format!(
                "a mounted file names a different system: `system {name};` does not resolve to `{}` or an enclosing system; drop the marker or the `as`",
                mount.join(".")
            );
            t.raise("MDL031", &rec, span, msg);
        }
    }
    for p in std::mem::take(&mut t.pending) {
        let enclosed = (0..=p.rec.ctx.len())
            .rev()
            .any(|n| t.systems.contains(&p.rec.ctx[..n].join(".")));
        if !enclosed {
            let msg = format!("this {} is outside any `system`", p.what);
            t.raise("MDL031", &p.rec, p.span, msg);
        }
    }
    for (rec, kind) in std::mem::take(&mut t.kinds) {
        if !CORE_ACTOR_KINDS.contains(&kind.text.as_str()) && !pack_atoms.contains(&kind.text) {
            let msg = format!("unknown actor kind `{}`", kind.text);
            t.raise("MDL031", &rec, kind.span, msg);
        }
    }
    for (rec, kind) in std::mem::take(&mut t.realizations) {
        if !CORE_REALIZATION_KINDS.contains(&kind.text.as_str()) && !pack_atoms.contains(&kind.text)
        {
            let msg = format!("unknown realization kind `{}`", kind.text);
            t.raise("MDL031", &rec, kind.span, msg);
        }
    }
    for (_, list) in std::mem::take(&mut t.keys_by_goal) {
        let first = list[0].1.clone();
        for (rec, key, span) in list.iter().skip(1) {
            if *key != first {
                let msg = format!("goal path has two different `as` keys: `{first}` and `{key}`");
                t.raise("MDL031", rec, *span, msg);
            }
        }
    }
}

fn system_of(t: &Tables<'_>, rec: &Rec) -> Option<String> {
    (0..=rec.ctx.len())
        .rev()
        .map(|n| rec.ctx[..n].join("."))
        .find(|k| t.systems.contains(k))
}

/// The `max` of a policy or retry as a count of at least 1, when it parses.
fn max_count(max: Option<&crate::ast::Spanned<String>>) -> Option<u64> {
    max?.value.parse::<u64>().ok().filter(|n| *n >= 1)
}

/// The ambient clause of a system or scenario clause list.
fn ambient_of(clauses: &[crate::plan::PClause]) -> Option<&crate::plan::Ambient> {
    clauses.iter().find_map(|c| match &c.kind {
        PClauseKind::Ambient(a) => Some(a),
        _ => None,
    })
}

/// The policy and every `else` fallback of it, outermost first.
fn policy_chain(p: &crate::plan::Policy) -> Vec<&crate::plan::Policy> {
    let mut out = vec![p];
    let mut cur = p;
    while let Some(next) = cur.otherwise.as_deref() {
        out.push(next);
        cur = next;
    }
    out
}

type AmbFinding = (&'static str, Rec, Span, String);

/// Adds to `out` every step run by scenario or step `key`, expanding includes (PLAN016).
fn steps_run(
    t: &Tables<'_>,
    uses: &HashMap<String, BTreeSet<String>>,
    key: &str,
    out: &mut BTreeSet<String>,
) {
    if t.steps.contains_key(key) {
        out.insert(key.to_owned());
    } else if t.scenarios.contains_key(key) {
        out.extend(uses.get(key).into_iter().flatten().cloned());
        for (from, to) in &t.includes {
            if from == key {
                steps_run(t, uses, to, out);
            }
        }
    }
}

/// The scenarios in `roots` and everything they include, transitively.
fn include_closure(t: &Tables<'_>, roots: Vec<String>) -> BTreeSet<String> {
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut todo = roots;
    while let Some(cur) = todo.pop() {
        if seen.insert(cur.clone()) {
            todo.extend(
                t.includes
                    .iter()
                    .filter(|(f, _)| *f == cur)
                    .map(|(_, to)| to.clone()),
            );
        }
    }
    seen
}

/// The written names of the non-`idempotent` steps among `keys`, sorted; `system_only` skips actor steps.
fn hazardous(t: &Tables<'_>, keys: &BTreeSet<String>, system_only: bool) -> Vec<String> {
    keys.iter()
        .filter(|k| {
            t.steps
                .get(*k)
                .is_some_and(|s| !s.idempotent && (s.is_system || !system_only))
        })
        .cloned()
        .collect()
}

/// PLAN016: a `retry` (arm or ambient) whose repeated path holds a step that is not `idempotent`.
///
/// An arm `retry` repeats the chain path from its target to the matched element (12.5); an
/// ambient `retry` repeats every system step of the scenarios it covers and their includes
/// (15.1). Handle-arm retries are not read: their repeated path is not specified.
// frob:ticket 01M6D467FK4WW4H4HB6NTVM2T5
fn plan016(t: &mut Tables<'_>, uses: &HashMap<String, BTreeSet<String>>) {
    let mut out: Vec<AmbFinding> = Vec::new();
    for r in &t.arm_retries {
        let Some(keys) = &r.repeated else {
            tracing::debug!(step = %r.step, "PLAN016 skips a handle-arm retry");
            continue;
        };
        let mut run = BTreeSet::new();
        for k in keys {
            steps_run(t, uses, k, &mut run);
        }
        let bad = hazardous(t, &run, false);
        if !bad.is_empty() {
            let msg = format!(
                "`retry {}` repeats non-idempotent step(s): {}",
                r.step,
                bad.join(", ")
            );
            out.push(("PLAN016", r.rec.clone(), r.span, msg));
        }
    }
    let mut ambient: Vec<(Rec, &crate::plan::Policy, Vec<String>)> = Vec::new();
    for (srec, sys) in t.system_decls.values() {
        let Some(a) = ambient_of(&sys.clauses) else {
            continue;
        };
        let roots: Vec<String> = t
            .scenarios
            .iter()
            .filter(|(k, sr)| {
                system_of(t, &sr.rec).as_deref() == Some(srec.full.as_str())
                    && override_of(t, k).is_none()
            })
            .map(|(k, _)| k.clone())
            .collect();
        ambient.push((srec.clone(), &a.policy, roots));
    }
    for (k, sr) in &t.scenarios {
        if let Some(p) = override_of(t, k) {
            ambient.push((sr.rec.clone(), p, vec![k.clone()]));
        }
    }
    for (rec, policy, roots) in ambient {
        for p in policy_chain(policy)
            .into_iter()
            .filter(|p| p.action.text == "retry")
        {
            let mut run = BTreeSet::new();
            for sc in include_closure(t, roots.clone()) {
                steps_run(t, uses, &sc, &mut run);
            }
            let bad = hazardous(t, &run, true);
            if !bad.is_empty() {
                let msg = format!(
                    "the ambient `retry` repeats non-idempotent system step(s): {}",
                    bad.join(", ")
                );
                out.push(("PLAN016", rec.clone(), p.action.span, msg));
            }
        }
    }
    tracing::debug!(findings = out.len(), "PLAN016 done");
    for (rule, rec, span, msg) in out {
        t.raise(rule, &rec, span, msg);
    }
}

/// AMB001, AMB003, AMB004, AMB005, AMB007, AMB008 and AMB009 over the parsed ambient policies (grmb-spec 15.1, 16.4).
fn ambient_checks(t: &mut Tables<'_>, idx: &Index<'_>) {
    let mut out: Vec<AmbFinding> = Vec::new();
    amb001(t, &mut out);
    amb003(t, &mut out);
    amb005(t, &mut out);
    amb008(t, &mut out);
    amb004(t, &mut out);
    amb009(t, idx, &mut out);
    tracing::debug!(findings = out.len(), "ambient pass done");
    for (rule, rec, span, msg) in out {
        t.raise(rule, &rec, span, msg);
    }
}

/// Ambient failure classes owned by grimble; they never enter an outcome map (AMB005).
const AMBIENT_CLASSES: [&str; 4] = ["exhausted", "defect", "interrupted", "killed"];

/// Language-root catch-all error types that an outcome map must not name (AMB005).
const ROOT_CATCHERS: [&str; 3] = ["Throwable", "BaseException", "recover"];

/// Source words that name a panic-converting call (`unwrap`, `expect`, `panic`) in an outcome map (AMB007).
const PANIC_CONVERSIONS: [&str; 3] = ["unwrap", "expect", "panic"];

/// AMB001: a system with no ambient policy.
fn amb001(t: &Tables<'_>, out: &mut Vec<AmbFinding>) {
    for (rec, sys) in t.system_decls.values() {
        if ambient_of(&sys.clauses).is_none() {
            tracing::debug!(system = %rec.full, "AMB001: no ambient policy");
            out.push((
                "AMB001",
                rec.clone(),
                sys.name.span,
                format!("system `{}` declares no ambient policy", rec.full),
            ));
        }
    }
}

/// AMB003: a `retry` or `restart` policy (system or scenario override) with no `max` or no `else` tail.
fn amb003(t: &Tables<'_>, out: &mut Vec<AmbFinding>) {
    let mut policies: Vec<(Rec, &crate::plan::Policy)> = Vec::new();
    for (rec, sys) in t.system_decls.values() {
        if let Some(a) = ambient_of(&sys.clauses) {
            policies.push((rec.clone(), &a.policy));
        }
    }
    for (key, sc) in &t.scenarios {
        if let Some(p) = override_of(t, key) {
            policies.push((sc.rec.clone(), p));
        }
    }
    for (rec, root) in policies {
        for p in policy_chain(root) {
            if !matches!(p.action.text.as_str(), "retry" | "restart") {
                continue;
            }
            let mut missing = Vec::new();
            if p.max.is_none() {
                missing.push("`max`");
            }
            if p.otherwise.is_none() {
                missing.push("an `else` tail");
            }
            if !missing.is_empty() {
                tracing::debug!(scope = %rec.full, action = %p.action.text, "AMB003: unbounded policy");
                out.push((
                    "AMB003",
                    rec.clone(),
                    p.action.span,
                    format!(
                        "the ambient `{}` policy of `{}` has no {}",
                        p.action.text,
                        rec.full,
                        missing.join(" and ")
                    ),
                ));
            }
        }
    }
}

/// AMB005 and AMB007: an ambient class, root catch-all or panic conversion named as a waypoint outcome-map source.
fn amb005(t: &Tables<'_>, out: &mut Vec<AmbFinding>) {
    for (irec, imp) in &t.impls {
        for c in &imp.clauses {
            let PClauseKind::Chain(wps) = &c.kind else {
                continue;
            };
            for wp in wps {
                for m in &wp.maps {
                    for src in &m.sources {
                        if PANIC_CONVERSIONS.contains(&src.value.as_str()) {
                            tracing::debug!(source = %src.value, "AMB007: domain error panics");
                            out.push((
                                "AMB007",
                                irec.clone(),
                                src.span,
                                format!(
                                    "outcome map source `{}` converts a mapped domain error into a panic",
                                    src.value
                                ),
                            ));
                            continue;
                        }
                        let what = if AMBIENT_CLASSES.contains(&src.value.as_str()) {
                            "an ambient class"
                        } else if ROOT_CATCHERS.contains(&src.value.as_str()) {
                            "a root catch-all"
                        } else {
                            continue;
                        };
                        tracing::debug!(source = %src.value, "AMB005: over-catch");
                        out.push((
                            "AMB005",
                            irec.clone(),
                            src.span,
                            format!("outcome map source `{}` is {what}", src.value),
                        ));
                    }
                }
            }
        }
    }
}

/// PLAN041, PLAN042 and PLAN044 over the outcome maps of impl waypoints (grmb-spec 14.4); producible errors of the unit need adapter facts, so PLAN041 judges only declared failure variants no map reaches.
// frob:ticket 01M6P033S4VV7JST84C3Q0TF80
fn outcome_maps(t: &mut Tables<'_>) {
    let mut out: Vec<AmbFinding> = Vec::new();
    for (irec, imp) in &t.impls {
        let Some((key, st)) = find(&t.steps, &irec.ctx, &imp.step) else {
            continue;
        };
        let mut mapped: BTreeSet<&str> = BTreeSet::new();
        let mut any_map = false;
        for c in &imp.clauses {
            let PClauseKind::Chain(wps) = &c.kind else {
                continue;
            };
            for wp in wps {
                any_map |= !wp.maps.is_empty();
                mapped.extend(wp.maps.iter().map(|m| m.target.text.as_str()));
                if wp.maps.is_empty() {
                    continue;
                }
                let wild = wp
                    .maps
                    .iter()
                    .any(|m| m.sources.iter().any(|s| s.value == "_"));
                if st.open && !wild {
                    tracing::debug!(step = %key, "PLAN044: open map without `_`");
                    out.push((
                        "PLAN044",
                        irec.clone(),
                        wp.span,
                        format!("the outcome map over the `open` set of `{key}` has no `_` source"),
                    ));
                }
                for m in &wp.maps {
                    if !st.outcomes.contains(&m.target.text) {
                        tracing::debug!(step = %key, variant = %m.target.text, "PLAN042: unproducible variant");
                        out.push((
                            "PLAN042",
                            irec.clone(),
                            m.target.span,
                            format!(
                                "outcome map targets `{}`, which is not a variant of `{key}`",
                                m.target.text
                            ),
                        ));
                    }
                }
            }
        }
        if any_map {
            for o in st.outcomes.iter().filter(|o| *o != "ok") {
                if !mapped.contains(o.as_str()) {
                    tracing::debug!(step = %key, variant = %o, "PLAN041: failure variant with no source");
                    out.push((
                        "PLAN041",
                        irec.clone(),
                        imp.step.span,
                        format!(
                            "no outcome-map source reaches the failure variant `{o}` of `{key}`"
                        ),
                    ));
                }
            }
        }
    }
    for (rule, rec, span, msg) in out {
        t.raise(rule, &rec, span, msg);
    }
}

/// AMB008: a system policy with no `verified_by` body.
fn amb008(t: &Tables<'_>, out: &mut Vec<AmbFinding>) {
    for (rec, sys) in t.system_decls.values() {
        let Some(a) = ambient_of(&sys.clauses) else {
            continue;
        };
        let proven = a
            .clauses
            .iter()
            .any(|c| matches!(c.kind, PClauseKind::Verified(_)));
        if !proven {
            out.push((
                "AMB008",
                rec.clone(),
                a.policy.action.span,
                format!(
                    "the ambient `{}` policy of system `{}` has no `verified_by` test",
                    a.policy.action.text, rec.full
                ),
            ));
        }
    }
}

/// AMB004: an arm `retry` that an applying ambient `retry` repeats, multiplying the attempts.
fn amb004(t: &Tables<'_>, out: &mut Vec<AmbFinding>) {
    for r in &t.arm_retries {
        if !t.steps.get(&r.target).is_some_and(|s| s.is_system) {
            continue;
        }
        let Some(arm_n) = max_count(Some(&r.max)) else {
            continue;
        };
        let mut seen: BTreeSet<Span> = BTreeSet::new();
        for p in applying_policies(t, &r.rec) {
            if p.action.text != "retry" || !seen.insert(p.action.span) {
                continue;
            }
            let Some(amb_n) = max_count(p.max.as_ref()) else {
                continue;
            };
            out.push((
                "AMB004",
                r.rec.clone(),
                r.span,
                format!(
                    "`retry {}` (max {arm_n}) is also repeated by the ambient `retry max {amb_n}`: up to {} attempts",
                    r.step,
                    arm_n * amb_n
                ),
            ));
        }
    }
}

/// The scenario's own ambient override, when it has one.
fn override_of<'a>(t: &Tables<'a>, key: &str) -> Option<&'a crate::plan::Policy> {
    t.scenarios
        .get(key)?
        .sc
        .members
        .iter()
        .find_map(|m| match m {
            ScMember::Clause(c) => match &c.kind {
                PClauseKind::Ambient(a) => Some(&a.policy),
                _ => None,
            },
            _ => None,
        })
}

/// The policies that apply to scenario `rec`: its override else its system policy, plus every includer's override.
fn applying_policies<'a>(t: &Tables<'a>, rec: &Rec) -> Vec<&'a crate::plan::Policy> {
    let mut out = Vec::new();
    match override_of(t, &rec.full) {
        Some(p) => out.push(p),
        None => {
            if let Some((_, sys)) = system_of(t, rec).and_then(|k| t.system_decls.get(&k)) {
                out.extend(ambient_of(&sys.clauses).map(|a| &a.policy));
            }
        }
    }
    let mut seen: BTreeSet<String> = BTreeSet::from([rec.full.clone()]);
    let mut todo = vec![rec.full.clone()];
    while let Some(cur) = todo.pop() {
        for (from, to) in &t.includes {
            if *to == cur && seen.insert(from.clone()) {
                out.extend(override_of(t, from));
                todo.push(from.clone());
            }
        }
    }
    out
}

/// AMB009: a `restart` policy that covers an impl in a stateful node with no flow to a store.
fn amb009(t: &Tables<'_>, idx: &Index<'_>, out: &mut Vec<AmbFinding>) {
    use crate::ast::{ClauseKind, EntityKind, Header, Value};
    let nodes: BTreeMap<String, &crate::model::EntityRec<'_>> = idx
        .entities
        .iter()
        .filter(|e| e.entity.kind == EntityKind::Node && !e.entity.extension)
        .map(|e| (e.full.clone(), e))
        .collect();
    let is_store = |e: &crate::model::EntityRec<'_>| {
        e.entity
            .clauses
            .iter()
            .any(|c| matches!(&c.kind, ClauseKind::Kind(k) if k.text == "store"))
    };
    let stateful = |e: &crate::model::EntityRec<'_>| {
        e.entity.clauses.iter().any(|c| match &c.kind {
            ClauseKind::Attr { key, value } if key.text == "stateful" => !matches!(
                value.as_ref().map(|v| &v.value),
                Some(Value::Ident(i)) if i == "false"
            ),
            _ => false,
        })
    };
    let mut stored: BTreeSet<String> = BTreeSet::new();
    for e in &idx.entities {
        if let Header::Flow { from, to } = &e.entity.header
            && let Some((fk, _)) = find(&nodes, &e.ctx, from)
            && let Some((_, tn)) = find(&nodes, &e.ctx, to)
            && is_store(tn)
        {
            stored.insert(fk.clone());
        }
    }
    let mut done: BTreeSet<(Span, String)> = BTreeSet::new();
    for (irec, imp) in &t.impls {
        let node = imp.clauses.iter().find_map(|c| match &c.kind {
            PClauseKind::InNode(p) => find(&nodes, &irec.ctx, p),
            _ => None,
        });
        let Some((nkey, nrec)) = node else {
            continue;
        };
        if !stateful(nrec) || stored.contains(nkey) {
            continue;
        }
        let scenario = match &imp.target {
            ImplTarget::Scenario(p) => find(&t.scenarios, &irec.ctx, p).map(|(k, _)| k.clone()),
            ImplTarget::Any(_) => None,
        };
        let source: Option<(Rec, &crate::plan::Policy)> = match scenario
            .as_ref()
            .and_then(|k| Some((t.scenarios.get(k)?, override_of(t, k)?)))
        {
            Some((sc, p)) => Some((sc.rec.clone(), p)),
            None => system_of(t, irec)
                .and_then(|k| t.system_decls.get(&k))
                .and_then(|(srec, sd)| Some((srec.clone(), &ambient_of(&sd.clauses)?.policy))),
        };
        let Some((srec, policy)) = source else {
            continue;
        };
        for p in policy_chain(policy) {
            if p.action.text == "restart" && done.insert((p.action.span, nkey.clone())) {
                out.push((
                    "AMB009",
                    srec.clone(),
                    p.action.span,
                    format!(
                        "`restart` loses the state of stateful node `{nkey}`, which has no flow to a store"
                    ),
                ));
            }
        }
    }
}

/// Goal `requires` cycles and cross-system edges, then impl-versus-scenario consistency.
fn impl_checks(t: &mut Tables<'_>, uses: &HashMap<String, BTreeSet<String>>, degraded: bool) {
    let mut edges: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for (from, _, path) in std::mem::take(&mut t.reqs) {
        let hit = find(&t.variants, &from.ctx, &path).map(|(k, v)| (k.clone(), v.0.clone()));
        let Some((key, target)) = hit else {
            if !degraded {
                let msg = format!(
                    "`requires {}` does not resolve to a goal variant",
                    path.written()
                );
                t.raise("MDL006", &from, path.span, msg);
            }
            continue;
        };
        if system_of(t, &from) != system_of(t, &target) {
            let msg = format!("`requires {}` crosses a system boundary", path.written());
            t.raise("MDL031", &from, path.span, msg);
        }
        edges.entry(from.full.clone()).or_default().push(key);
    }
    let mut state: HashMap<String, u8> = HashMap::new();
    let names: Vec<String> = edges.keys().cloned().collect();
    let mut reported = BTreeSet::new();
    for n in names {
        cycle(t, &edges, &n, &mut state, &mut reported);
    }
    for (rec, imp) in std::mem::take(&mut t.impls) {
        let step = find(&t.steps, &rec.ctx, &imp.step).map(|(k, _)| k.clone());
        let Some(step) = step else {
            if !degraded {
                let msg = format!("`impl {}` does not resolve to a step", imp.step.written());
                t.raise("MDL006", &rec, imp.step.span, msg);
            }
            continue;
        };
        let ImplTarget::Scenario(sp) = &imp.target else {
            continue;
        };
        let sc = find(&t.scenarios, &rec.ctx, sp).map(|(k, _)| k.clone());
        let Some(sc) = sc else {
            if !degraded {
                let msg = format!(
                    "`impl .. for {}` does not resolve to a scenario",
                    sp.written()
                );
                t.raise("MDL006", &rec, sp.span, msg);
            }
            continue;
        };
        if uses.get(&sc).is_some_and(|u| !u.contains(&step)) {
            let msg = format!(
                "scenario `{}` never uses step `{}` directly",
                sp.written(),
                imp.step.written()
            );
            t.raise("MDL031", &rec, imp.step.span, msg);
        }
    }
}

fn cycle(
    t: &mut Tables<'_>,
    edges: &BTreeMap<String, Vec<String>>,
    n: &str,
    state: &mut HashMap<String, u8>,
    reported: &mut BTreeSet<String>,
) {
    match state.get(n) {
        Some(2) => return,
        Some(1) => {
            if reported.insert(n.to_owned())
                && let Some((rec, span)) = t.variants.get(n).cloned()
            {
                t.raise(
                    "MDL030",
                    &rec,
                    span,
                    format!("`{n}` is part of a `requires` cycle"),
                );
            }
            return;
        }
        _ => {}
    }
    state.insert(n.to_owned(), 1);
    for m in edges.get(n).cloned().unwrap_or_default() {
        cycle(t, edges, &m, state, reported);
    }
    state.insert(n.to_owned(), 2);
}

/// One step use in a scenario chain, resolved: the step key and where it was written.
#[derive(Clone)]
struct StepUse {
    step: String,
    span: Span,
}

/// A flow declared in the model, with its resolved endpoint nodes.
struct DeclaredFlow {
    name: String,
    from: String,
    to: String,
    rec: Rec,
    span: Span,
}

/// A consecutive step-use pair in one scenario, with the node of each side when known.
struct UsePair {
    rec: Rec,
    a: StepUse,
    b: StepUse,
    na: Option<String>,
    nb: Option<String>,
}

/// Collects the `(predecessor, successor)` step-use pairs of `chain` and its arms (`Succ`, 13.5).
///
/// An `include` breaks the sequence: the included scenario's entry and exit are not tracked.
fn succ_pairs(
    t: &Tables<'_>,
    ctx: &[String],
    chain: &Chain,
    mut prev: Option<StepUse>,
    out: &mut Vec<(StepUse, StepUse)>,
) {
    let mut visit = |e: &Elem, prev: &mut Option<StepUse>| {
        let cur = match e {
            Elem::Step(p) => find(&t.steps, ctx, p).map(|(k, _)| StepUse {
                step: k.clone(),
                span: p.span,
            }),
            Elem::Include(_) => None,
        };
        if let (Some(a), Some(b)) = (prev.as_ref(), cur.as_ref()) {
            out.push((a.clone(), b.clone()));
        }
        *prev = cur;
    };
    for (e, _) in &chain.links {
        visit(e, &mut prev);
    }
    match &chain.tail {
        Tail::Open(e) => visit(e, &mut prev),
        Tail::Match { elem, arms } => {
            visit(elem, &mut prev);
            for a in arms {
                succ_pairs(t, ctx, &a.chain, prev.clone(), out);
            }
        }
        Tail::Retry {
            otherwise: Some(o), ..
        } => succ_pairs(t, ctx, o, None, out),
        _ => {}
    }
}

// frob:ticket 01M6CKH5T88K0H44GH91F0PXRG
/// SYS015 and SYS016 (grmb-spec 13.5): behaviour implies a declared data flow.
///
/// A node is known only from an impl `in node` or an actor `in node`; an owner derived from
/// bound code is not visible here, so such a step use is Unknown and its findings Unresolved.
fn sys_flow(t: &mut Tables<'_>, idx: &Index<'_>, degraded: bool) {
    use crate::ast::{EntityKind, Header};
    if t.scenarios.is_empty() {
        return;
    }
    let nodes: BTreeMap<String, String> = idx
        .entities
        .iter()
        .filter(|e| e.entity.kind == EntityKind::Node && !e.entity.extension)
        .map(|e| (e.full.clone(), e.full.clone()))
        .collect();
    let mut flows: Vec<DeclaredFlow> = Vec::new();
    for e in &idx.entities {
        if let Header::Flow { from, to } = &e.entity.header
            && let Some((fk, _)) = find(&nodes, &e.ctx, from)
            && let Some((tk, _)) = find(&nodes, &e.ctx, to)
        {
            let rec = Rec {
                file: e.file,
                ctx: e.ctx.clone(),
                full: e.full.clone(),
            };
            flows.push(DeclaredFlow {
                name: e.full.clone(),
                from: fk.clone(),
                to: tk.clone(),
                rec,
                span: e.entity.name.span,
            });
        }
    }
    let mut pairs: Vec<UsePair> = Vec::new();
    let keys: Vec<String> = t.scenarios.keys().cloned().collect();
    for key in &keys {
        let sr = &t.scenarios[key];
        let mut found = Vec::new();
        for m in &sr.sc.members {
            match m {
                ScMember::Chain(_, c) => succ_pairs(t, &sr.rec.ctx, c, None, &mut found),
                ScMember::Handle(h) => {
                    for a in &h.arms {
                        succ_pairs(t, &sr.rec.ctx, &a.chain, None, &mut found);
                    }
                }
                ScMember::Clause(_) => {}
            }
        }
        for (a, b) in found {
            let na = use_node(t, &nodes, key, &a.step);
            let nb = use_node(t, &nodes, key, &b.step);
            pairs.push(UsePair {
                rec: sr.rec.clone(),
                a,
                b,
                na,
                nb,
            });
        }
    }
    let mut exercised: BTreeSet<(String, String)> = BTreeSet::new();
    let mut seen: BTreeSet<(String, Span)> = BTreeSet::new();
    for UsePair { rec, a, b, na, nb } in &pairs {
        match (na, nb) {
            (Some(x), Some(y)) if x != y => {
                exercised.insert((x.clone(), y.clone()));
                if !flows.iter().any(|f| f.from == *x && f.to == *y) {
                    if degraded {
                        let msg = format!(
                            "no flow `{x} -> {y}` for `{} -> {}`, but the model has holes that may declare one",
                            a.step, b.step
                        );
                        t.emit_as("SYS015", rec, b.span, msg, true);
                    } else if seen.insert((rec.full.clone(), b.span)) {
                        let msg = format!(
                            "`{}` (in `{x}`) is followed by `{}` (in `{y}`) but no flow `{x} -> {y}` is declared",
                            a.step, b.step
                        );
                        t.emit_as("SYS015", rec, b.span, msg, false);
                    }
                }
            }
            (Some(_), Some(_)) => {}
            _ => {
                let unknown = if na.is_none() { &a.step } else { &b.step };
                let msg = format!(
                    "`{} -> {}` cannot be checked against the flows: `{unknown}` has no known node",
                    a.step, b.step
                );
                t.emit_as("SYS015", rec, b.span, msg, true);
            }
        }
    }
    let hops_unknown = t.impls.iter().any(|(_, i)| {
        i.clauses
            .iter()
            .any(|c| matches!(&c.kind, PClauseKind::Chain(w) if w.len() > 1))
    });
    for DeclaredFlow {
        name,
        from: x,
        to: y,
        rec,
        span,
    } in flows
    {
        if exercised.contains(&(x.clone(), y.clone())) {
            continue;
        }
        let could = hops_unknown
            || pairs.iter().any(|UsePair { na, nb, .. }| {
                na.as_ref().is_none_or(|n| *n == x) && nb.as_ref().is_none_or(|n| *n == y)
            });
        if could || degraded {
            let msg = format!(
                "flow `{name}` is exercised by no known step use or hop; a step with no known node could"
            );
            t.emit_as("SYS016", &rec, span, msg, true);
        } else {
            let msg = format!("flow `{name}` is exercised by no step use or waypoint hop");
            t.emit_as("SYS016", &rec, span, msg, false);
        }
    }
}

/// The node a step use sits in: the scenario's (else the wildcard) impl `in node`, else the actor's.
fn use_node(
    t: &Tables<'_>,
    nodes: &BTreeMap<String, String>,
    scenario: &str,
    step: &str,
) -> Option<String> {
    match impl_node(t, nodes, scenario, step) {
        ImplNode::Matched(found) => found,
        ImplNode::NoImpl => actor_node(t, nodes, step),
    }
}

/// Outcome of looking up the impl that places a step.
enum ImplNode {
    /// An impl matched; its `in node` resolved to this node, if it resolved.
    Matched(Option<String>),
    /// No impl matches the step.
    NoImpl,
}

/// The node a matching impl names with `in node`; `NoImpl` when no impl matches the step.
fn impl_node(
    t: &Tables<'_>,
    nodes: &BTreeMap<String, String>,
    scenario: &str,
    step: &str,
) -> ImplNode {
    let in_node = |imp: &crate::plan::Impl| {
        imp.clauses.iter().find_map(|c| match &c.kind {
            PClauseKind::InNode(p) => Some(p.clone()),
            _ => None,
        })
    };
    let mut specific = None;
    let mut wildcard = None;
    for (rec, imp) in &t.impls {
        if find(&t.steps, &rec.ctx, &imp.step).is_none_or(|(k, _)| k != step) {
            continue;
        }
        let Some(p) = in_node(imp) else { continue };
        match &imp.target {
            ImplTarget::Scenario(sp)
                if find(&t.scenarios, &rec.ctx, sp).is_some_and(|(k, _)| k == scenario) =>
            {
                specific = Some((rec, p));
            }
            ImplTarget::Any(_) => wildcard = Some((rec, p)),
            ImplTarget::Scenario(_) => {}
        }
    }
    let Some((rec, p)) = specific.or(wildcard) else {
        return ImplNode::NoImpl;
    };
    ImplNode::Matched(find(nodes, &rec.ctx, &p).map(|(k, _)| k.clone()))
}

/// The node of the actor owning `step`.
fn actor_node(t: &Tables<'_>, nodes: &BTreeMap<String, String>, step: &str) -> Option<String> {
    let (actor, _) = step.rsplit_once('.')?;
    let (arec, path) = t.actors.get(actor).map(|(r, p)| (r, p.as_ref()))?;
    find(nodes, &arec.ctx, path?).map(|(k, _)| k.clone())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set(names: &[&str]) -> BTreeSet<String> {
        names.iter().map(|s| (*s).to_owned()).collect()
    }

    fn m(s: &str) -> Vec<String> {
        s.split('.').map(str::to_owned).collect()
    }

    // frob:tests marker_target
    #[test]
    fn marker_equal_to_mount_resolves() {
        let got = marker_target(&set(&["web_app"]), &m("web_app"), "web_app");
        assert_eq!(got.as_deref(), Some("web_app"));
    }

    // frob:tests marker_target
    #[test]
    fn marker_naming_proper_prefix_resolves() {
        let got = marker_target(&set(&["web_app"]), &m("web_app.sub"), "web_app");
        assert_eq!(got.as_deref(), Some("web_app"));
    }

    // frob:tests marker_target
    #[test]
    fn marker_naming_other_system_is_rejected() {
        assert_eq!(
            marker_target(&set(&["web_app"]), &m("api"), "web_app"),
            None
        );
        assert_eq!(marker_target(&set(&["api"]), &m("api"), "web_app"), None);
    }

    // frob:tests marker_target
    #[test]
    fn marker_not_extending_prefix_by_name_alone_is_rejected() {
        assert_eq!(marker_target(&set(&["web"]), &m("web_app"), "web"), None);
    }
}
