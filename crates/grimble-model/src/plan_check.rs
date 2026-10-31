//! Planning well-formedness and scenario typing: MDL022-MDL031 (grmb-planning 5.3-5.6, 7.1).
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

/// Actor kinds that need no pack (grmb-planning 4.2).
pub const CORE_ACTOR_KINDS: &[&str] = &["human", "external", "timer", "device"];

/// Realization kinds known without a pack (grmb-planning 4.6); packs add more as atoms.
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
}

fn join(ctx: &[String], tail: &str) -> String {
    if ctx.is_empty() {
        tail.to_owned()
    } else {
        format!("{}.{tail}", ctx.join("."))
    }
}

/// Resolves `path` from inside `ctx`, nearest enclosing prefix first (grmb-spec 5.3).
fn find<'t, T>(
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
    fn emit(&mut self, rule: &'static str, rec: &Rec, span: Span, message: String) {
        let anchor = format!("plan/{}", rec.full);
        tracing::debug!(rule, %span, %message, "plan finding");
        self.findings.push(PlanFinding {
            rule,
            file: rec.file,
            span,
            message,
            anchor,
        });
    }

    fn reserved(&mut self, rec: &Rec, name: &crate::ast::Ident, what: &str) {
        if is_planning_word(&name.text) && !(name.text == "ok" && what == "outcome variant") {
            self.emit(
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
                ctx.push(s.name.text.clone());
                self.collect(file, &s.items, ctx);
                ctx.pop();
            }
            PlanItem::Actor(a) => {
                let rec = self.rec(file, ctx, &a.name.text);
                self.pend(&rec, a.name.span, "actor");
                self.reserved(&rec, &a.name, "actor");
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
                for v in &g.variants {
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
                        span: s.target.span,
                    };
                    self.reserved(&rec, &id, "step");
                }
                self.steps.insert(
                    rec.full.clone(),
                    StepRec {
                        outcomes,
                        is_system: s.is_system(),
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

/// The summary of a typed scenario (grmb-planning 5.4).
#[derive(Clone, Debug)]
struct Summary {
    eok: bool,
    errs: BTreeSet<String>,
    starts_system: bool,
}

#[derive(Clone, Debug)]
struct Pair {
    label: String,
    key: String,
    var: String,
    span: Span,
}

struct ElemInfo {
    key: String,
    label: String,
    vars: Vec<String>,
    span: Span,
    is_step: bool,
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
    fn emit(&mut self, rule: &'static str, rec: &Rec, span: Span, message: String) {
        self.t.emit(rule, rec, span, message);
    }

    fn unresolved(&mut self, rec: &Rec, path: &RefPath, what: &str) {
        if !self.degraded {
            let msg = format!("`{}` does not resolve to a {what}", path.written());
            self.emit("MDL006", rec, path.span, msg);
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
                run.uses.insert(key.clone());
                Some(ElemInfo {
                    key,
                    label: p.dotted(),
                    vars,
                    span: path.span,
                    is_step: true,
                })
            }
            Elem::Include(p) => {
                let Some((key, _)) = find(&self.t.scenarios, &ctx, p) else {
                    self.unresolved(&run.rec.clone(), p, "scenario");
                    return None;
                };
                let key = key.clone();
                if self.busy.contains(&key) {
                    self.emit(
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
                    key,
                    label: p.dotted(),
                    vars,
                    span: p.span,
                    is_step: false,
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
            if find(&self.t.variants, &rec.ctx, r).is_none() {
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
            [] => self.emit(
                "MDL026",
                &rec,
                sc_ref.name.span,
                format!("scenario `{}` has no main chain", sc_ref.name.text),
            ),
            [main, rest @ ..] => {
                for extra in rest {
                    self.emit(
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
                self.emit(
                    "MDL031",
                    &rec,
                    h.span,
                    format!("scenario `{}` has more than one handle", sc_ref.name.text),
                );
            }
        }
        self.resolve_collected(&mut run, handles.first().copied());
        let colh = std::mem::take(&mut run.colh);
        for p in colh {
            if !self.declared(&run, &p.var) {
                self.emit(
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
        };
        self.busy.remove(key);
        self.uses.insert(key.to_owned(), run.uses);
        self.memo.insert(key.to_owned(), Some(sum.clone()));
        Some(sum)
    }

    fn declared(&self, run: &Run, var: &str) -> bool {
        run.f.as_ref().is_some_and(|f| f.iter().any(|x| x == var))
    }

    /// MDL029: the main chain must start with an actor step (grmb-planning 5.6).
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
            self.emit(
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
            self.emit(
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
                    self.emit(
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
                    self.emit(
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
            Tail::EndErr(v) => self.end_err(run, &v.text, v.span),
            Tail::Open(e) => {
                let _ = self.elem(run, e);
                self.emit(
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
                    self.emit(
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
            self.emit(
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
            None => self.emit("MDL027", &rec, span, "`retry` needs `max N`".to_owned()),
            Some(m) => {
                if m.value.parse::<u64>().map_or(true, |n| n < 1) {
                    self.emit(
                        "MDL027",
                        &rec,
                        m.span,
                        format!("`max {}` must be a number of at least 1", m.value),
                    );
                }
            }
        }
        if let Some(k) = &target {
            run.uses.insert(k.clone());
            let on_path = if arm.handle {
                run.main_keys.contains(k)
            } else {
                path.contains(k)
            };
            if !on_path {
                self.emit(
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
            (None, None) => self.emit(
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
                self.emit(
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
                self.emit(
                    "MDL028",
                    &rec,
                    *sp,
                    "a `_` arm hides variants added later; name each variant".to_owned(),
                );
            }
            if !used[i] {
                self.emit(
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

    /// Handles or propagates every collected pair (grmb-planning 5.4).
    fn resolve_collected(&mut self, run: &mut Run, handle: Option<&crate::plan::Handle>) {
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
        for (p, b) in pairs.iter().zip(&best) {
            if b.is_none() && !self.declared(run, &p.var) {
                self.emit(
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
    }
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
        t.collect(fi, &f.parsed.items, &mut ctx);
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
    impl_checks(&mut t, &uses, degraded);
    tracing::debug!(findings = t.findings.len(), "planning pass done");
    t.findings
}

/// The checks that need only the name tables: enclosure, kinds, goal keys, requires.
fn structure(t: &mut Tables<'_>, pack_atoms: &BTreeSet<String>) {
    for p in std::mem::take(&mut t.pending) {
        let enclosed = (0..=p.rec.ctx.len())
            .rev()
            .any(|n| t.systems.contains(&p.rec.ctx[..n].join(".")));
        if !enclosed {
            let msg = format!("this {} is outside any `system`", p.what);
            t.emit("MDL031", &p.rec, p.span, msg);
        }
    }
    for (rec, kind) in std::mem::take(&mut t.kinds) {
        if !CORE_ACTOR_KINDS.contains(&kind.text.as_str()) && !pack_atoms.contains(&kind.text) {
            let msg = format!("unknown actor kind `{}`", kind.text);
            t.emit("MDL031", &rec, kind.span, msg);
        }
    }
    for (rec, kind) in std::mem::take(&mut t.realizations) {
        if !CORE_REALIZATION_KINDS.contains(&kind.text.as_str()) && !pack_atoms.contains(&kind.text)
        {
            let msg = format!("unknown realization kind `{}`", kind.text);
            t.emit("MDL031", &rec, kind.span, msg);
        }
    }
    for (_, list) in std::mem::take(&mut t.keys_by_goal) {
        let first = list[0].1.clone();
        for (rec, key, span) in list.iter().skip(1) {
            if *key != first {
                let msg = format!("goal path has two different `as` keys: `{first}` and `{key}`");
                t.emit("MDL031", rec, *span, msg);
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
                t.emit("MDL006", &from, path.span, msg);
            }
            continue;
        };
        if system_of(t, &from) != system_of(t, &target) {
            let msg = format!("`requires {}` crosses a system boundary", path.written());
            t.emit("MDL031", &from, path.span, msg);
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
                t.emit("MDL006", &rec, imp.step.span, msg);
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
                t.emit("MDL006", &rec, sp.span, msg);
            }
            continue;
        };
        if uses.get(&sc).is_some_and(|u| !u.contains(&step)) {
            let msg = format!(
                "scenario `{}` never uses step `{}` directly",
                sp.written(),
                imp.step.written()
            );
            t.emit("MDL031", &rec, imp.step.span, msg);
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
                t.emit(
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
