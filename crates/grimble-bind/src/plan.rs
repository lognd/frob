//! Design status and planning obligations (grmb-planning 5.8, 7.2): what the graph JSON adds.
//!
//! [`report`] reads the planning nodes of the model and the selector answers of the relation and
//! returns, per planning entity, the `status`, `status_hi`, `level`, `plan` and `rollup` keys of the
//! sibling document, the planning edges, and the PLAN obligations. Nothing here runs tests: `verified`
//! means an evidence selector resolves, never that the evidence passed.

// frob:ticket 01M4FDBBXG990QVX35HERF5VCQ

use std::collections::{BTreeMap, BTreeSet};

use grimble_model::plan_index::{PlanEdge, PlanNode};
use serde_json::{Map, Value, json};

use crate::model::Model;
use crate::owner::Owners;
use crate::relation::{ClauseResult, Relation};
use crate::types::{BindFinding, Reason};
use gob_rules::Severity;

/// The design status of an entity, ordered `declared < bound < verified`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum St {
    Declared,
    Bound,
    Verified,
}

impl St {
    fn word(self) -> &'static str {
        match self {
            St::Declared => "declared",
            St::Bound => "bound",
            St::Verified => "verified",
        }
    }
}

/// The planning facts of a run, ready to merge into the sibling document.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct PlanReport {
    /// Per planning anchor: `status`, `status_hi`, `level`, `system`, `plan` and `rollup` keys.
    pub fields: BTreeMap<String, Map<String, Value>>,
    /// Planning edges as `{kind, from, to, anchor, contract[, scenario]}` objects.
    pub edges: Vec<Value>,
    /// `{rule, kind, anchor, detail}` objects sorted by anchor.
    pub obligations: Vec<Value>,
}

struct Cx<'a> {
    nodes: BTreeMap<&'a str, &'a PlanNode>,
    results: BTreeMap<&'a str, &'a ClauseResult>,
    /// Goal anchor to the leaf goals at or under it.
    leaves: BTreeMap<&'a str, Vec<&'a str>>,
    /// Impls by `(step, scenario)`.
    impls: BTreeMap<(String, Option<String>), Vec<&'a PlanNode>>,
}

impl<'a> Cx<'a> {
    fn build(model: &'a Model, rel: &'a Relation) -> Self {
        let nodes: BTreeMap<&str, &PlanNode> = model
            .plan
            .iter()
            .map(|p| (p.node.anchor.as_str(), &p.node))
            .collect();
        let results = rel
            .clauses
            .iter()
            .map(|r| (r.clause.anchor.as_str(), r))
            .collect();
        let mut leaves: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
        for g in nodes.values().filter(|n| n.kind == "goal" && n.leaf) {
            let mut at = Some(g.anchor.as_str());
            while let Some(a) = at {
                leaves.entry(a).or_default().push(g.anchor.as_str());
                at = nodes.get(a).and_then(|n| n.parent.as_deref());
                if at.is_some_and(|p| !p.starts_with("goal/")) {
                    break;
                }
            }
        }
        let mut impls: BTreeMap<(String, Option<String>), Vec<&PlanNode>> = BTreeMap::new();
        for n in nodes.values().filter(|n| n.kind == "impl") {
            if let Some(step) = n.impl_step.as_ref() {
                impls
                    .entry((step.clone(), n.impl_scenario.clone()))
                    .or_default()
                    .push(n);
            }
        }
        Self {
            nodes,
            results,
            leaves,
            impls,
        }
    }

    /// Does the clause resolve to something (at `hi`: could it; at lo: must it)?
    fn ok(&self, anchor: &str, hi: bool) -> bool {
        self.results
            .get(anchor)
            .is_some_and(|r| if hi { !r.hi_empty() } else { r.lo() > 0 })
    }

    fn realizations(n: &PlanNode) -> impl Iterator<Item = &str> {
        n.clauses
            .iter()
            .filter(|c| c.realization_kind.is_some())
            .map(|c| c.anchor.as_str())
    }

    fn evidence(n: &PlanNode) -> Vec<&str> {
        n.clauses
            .iter()
            .filter(|c| c.realization_kind.is_none())
            .map(|c| c.anchor.as_str())
            .collect()
    }

    fn own_verified(&self, n: &PlanNode, hi: bool) -> bool {
        let ev = Self::evidence(n);
        !ev.is_empty() && ev.iter().all(|a| self.ok(a, hi))
    }

    fn bound(&self, n: &PlanNode, hi: bool) -> bool {
        let real: Vec<&str> = Self::realizations(n).collect();
        if real.is_empty() || !real.iter().all(|a| self.ok(a, hi)) {
            return false;
        }
        n.pages.iter().all(|p| {
            self.nodes
                .get(p.as_str())
                .is_none_or(|pn| self.bound(pn, hi))
        })
    }

    /// Status of an impl or page.
    fn artifact(&self, n: &PlanNode, hi: bool) -> St {
        if !self.bound(n, hi) {
            St::Declared
        } else if self.own_verified(n, hi) {
            St::Verified
        } else {
            St::Bound
        }
    }

    /// The impls serving one step use `(step, scenario)`: the specific ones, else `for *`.
    fn impls_of<'s>(&'s self, step: &str, scenario: &str) -> &'s [&'a PlanNode] {
        if let Some(v) = self
            .impls
            .get(&(step.to_owned(), Some(scenario.to_owned())))
        {
            return v;
        }
        self.impls
            .get(&(step.to_owned(), None))
            .map_or(&[], Vec::as_slice)
    }

    fn step_status(&self, step: &str, hi: bool) -> St {
        self.impls
            .iter()
            .filter(|((s, _), _)| s == step)
            .flat_map(|(_, v)| v.iter())
            .map(|i| self.artifact(i, hi))
            .min()
            .unwrap_or(St::Declared)
    }

    fn scenario_base(&self, n: &PlanNode, hi: bool, seen: &mut BTreeSet<String>) -> St {
        if !seen.insert(n.anchor.clone()) {
            return St::Declared;
        }
        let mut parts: Vec<St> = Vec::new();
        for step in &n.uses {
            let impls = self.impls_of(step, &n.anchor);
            parts.push(
                impls
                    .iter()
                    .map(|i| self.artifact(i, hi))
                    .min()
                    .unwrap_or(St::Declared),
            );
        }
        for inc in &n.includes {
            if let Some(i) = self.nodes.get(inc.as_str()) {
                parts.push(self.scenario_base(i, hi, seen));
            }
        }
        seen.remove(&n.anchor);
        parts.into_iter().min().unwrap_or(St::Declared)
    }

    fn cap(&self, n: &PlanNode, base: St, hi: bool) -> St {
        if base == St::Verified && !self.own_verified(n, hi) {
            St::Bound
        } else {
            base
        }
    }

    fn scenario(&self, n: &PlanNode, hi: bool) -> St {
        let base = self.scenario_base(n, hi, &mut BTreeSet::new());
        self.cap(n, base, hi)
    }

    /// Scenarios that cover the goal leaf `leaf`.
    fn covering(&self, leaf: &str) -> Vec<&'a PlanNode> {
        self.nodes
            .values()
            .copied()
            .filter(|s| s.kind == "scenario")
            .filter(|s| {
                s.realizes.iter().any(|g| {
                    self.leaves
                        .get(g.as_str())
                        .is_some_and(|l| l.contains(&leaf))
                })
            })
            .collect()
    }

    fn leaf_goal(&self, leaf: &PlanNode, hi: bool) -> St {
        let base = self
            .covering(&leaf.anchor)
            .iter()
            .map(|s| self.scenario(s, hi))
            .min()
            .unwrap_or(St::Declared);
        self.cap(leaf, base, hi)
    }

    fn goal(&self, n: &PlanNode, hi: bool) -> St {
        let ls = self
            .leaves
            .get(n.anchor.as_str())
            .map_or(&[][..], Vec::as_slice);
        if n.leaf {
            return self.leaf_goal(n, hi);
        }
        let base = ls
            .iter()
            .filter_map(|l| self.nodes.get(l))
            .map(|l| self.leaf_goal(l, hi))
            .min()
            .unwrap_or(St::Declared);
        self.cap(n, base, hi)
    }

    /// Leaf goals under an actor or system.
    fn goals_of(&self, n: &PlanNode) -> Vec<&'a PlanNode> {
        self.nodes
            .values()
            .copied()
            .filter(|g| g.kind == "goal" && g.leaf)
            .filter(|g| {
                if n.kind == "system" {
                    g.system.as_deref() == Some(n.anchor.as_str())
                } else {
                    self.root_actor(g) == Some(n.anchor.as_str())
                }
            })
            .collect()
    }

    fn root_actor<'s>(&'s self, g: &'s PlanNode) -> Option<&'s str> {
        let mut at = g.parent.as_deref()?;
        loop {
            if at.starts_with("actor/") {
                return Some(at);
            }
            at = self.nodes.get(at)?.parent.as_deref()?;
        }
    }

    fn status(&self, n: &PlanNode, hi: bool) -> St {
        match n.kind {
            "impl" | "page" => self.artifact(n, hi),
            "scenario" => self.scenario(n, hi),
            "goal" => self.goal(n, hi),
            "step" => self.step_status(&n.anchor, hi),
            _ => self
                .goals_of(n)
                .iter()
                .map(|g| self.leaf_goal(g, hi))
                .min()
                .unwrap_or(St::Declared),
        }
    }

    /// Impls reached by a scenario (through includes), deduplicated by anchor.
    fn scenario_impls(
        &self,
        n: &PlanNode,
        seen: &mut BTreeSet<String>,
        out: &mut BTreeMap<String, &'a PlanNode>,
    ) {
        if !seen.insert(n.anchor.clone()) {
            return;
        }
        for step in &n.uses {
            for i in self.impls_of(step, &n.anchor) {
                out.insert(i.anchor.clone(), i);
            }
        }
        for inc in &n.includes {
            if let Some(i) = self.nodes.get(inc.as_str()) {
                self.scenario_impls(i, seen, out);
            }
        }
    }

    fn rollup(&self, n: &PlanNode) -> Option<Value> {
        let mut found: BTreeMap<String, &PlanNode> = BTreeMap::new();
        match n.kind {
            "scenario" => self.scenario_impls(n, &mut BTreeSet::new(), &mut found),
            "goal" if n.leaf => {
                for s in self.covering(&n.anchor) {
                    self.scenario_impls(s, &mut BTreeSet::new(), &mut found);
                }
            }
            "goal" => {
                for l in self.leaves.get(n.anchor.as_str()).into_iter().flatten() {
                    for s in self.covering(l) {
                        self.scenario_impls(s, &mut BTreeSet::new(), &mut found);
                    }
                }
            }
            "system" => {
                for i in self.nodes.values().filter(|i| i.kind == "impl") {
                    if i.system.as_deref() == Some(n.anchor.as_str()) {
                        found.insert(i.anchor.clone(), i);
                    }
                }
            }
            _ => return None,
        }
        let sts: Vec<St> = found.values().map(|i| self.artifact(i, false)).collect();
        Some(json!({
            "declared": sts.len(),
            "bound": sts.iter().filter(|s| **s >= St::Bound).count(),
            "verified": sts.iter().filter(|s| **s == St::Verified).count(),
        }))
    }
}

fn level(n: &PlanNode) -> Value {
    match n.kind {
        "goal" if n.parent.as_deref().is_some_and(|p| p.starts_with("actor/")) => {
            json!("requirements")
        }
        "goal" => json!("requirement_spec"),
        "scenario" => json!("system_spec"),
        "page" => json!("system_design"),
        "impl" => json!("component_design"),
        _ => Value::Null,
    }
}

fn plan_object(n: &PlanNode) -> Option<Value> {
    Some(match n.kind {
        "actor" => json!({"kind": n.actor_kind, "node": n.node}),
        "goal" => json!({
            "dimension": n.dimension, "parent": n.parent, "leaf": n.leaf, "requires": n.requires,
        }),
        "step" => {
            let outcome: Vec<Value> = if n.outcomes.is_empty() {
                vec![json!({"variant": "ok", "payload": null})]
            } else {
                n.outcomes
                    .iter()
                    .map(|(v, p)| json!({"variant": v, "payload": p}))
                    .collect()
            };
            json!({"owner": n.owner, "outcome": outcome})
        }
        "scenario" => {
            let collected: Vec<Value> = n
                .collected
                .iter()
                .map(|c| json!({"step": c.step, "variant": c.variant, "handled_by": c.handled_by}))
                .collect();
            tracing::debug!(anchor = %n.anchor, errors = n.error_set.len(), collected = collected.len(), "scenario plan row");
            json!({
                "realizes": n.realizes, "fails_with": n.fails_with,
                "error_set": n.error_set, "collected": collected,
            })
        }
        "impl" => json!({
            "step": n.impl_step, "scenario": n.impl_scenario, "node": n.node, "pages": n.pages,
        }),
        "page" => json!({"entry": n.entry, "from": n.from}),
        _ => return None,
    })
}

/// One planning obligation before it is rendered as graph JSON or lifted to a finding.
struct Ob {
    rule: &'static str,
    kind: &'static str,
    anchor: String,
    detail: String,
    /// Whether the obligation could still be met at `hi` (a May selector): Unresolved, not fired.
    undecided: bool,
    /// Whether SYS004 already reports the same fact (an empty realization selector).
    sys004_dup: bool,
}

impl Ob {
    fn new(rule: &'static str, kind: &'static str, n: &PlanNode, detail: String) -> Self {
        Self {
            rule,
            kind,
            anchor: n.anchor.clone(),
            detail,
            undecided: false,
            sys004_dup: false,
        }
    }

    fn json(&self) -> Value {
        json!({"rule": self.rule, "kind": self.kind, "anchor": self.anchor, "detail": self.detail})
    }
}

/// PLAN005 for `n` when it has no own evidence at `lo`; undecided when `hi` would have some.
fn unverified(cx: &Cx<'_>, n: &PlanNode) -> Option<Ob> {
    if cx.own_verified(n, false) {
        return None;
    }
    let mut ob = Ob::new(
        "PLAN005",
        "unverified",
        n,
        format!("{} has no resolving verified_by", n.name),
    );
    ob.undecided = cx.own_verified(n, true);
    Some(ob)
}

fn typed_obligations(cx: &Cx<'_>) -> Vec<Ob> {
    let mut out: Vec<Ob> = Vec::new();
    for n in cx.nodes.values() {
        match n.kind {
            "goal" if n.leaf => {
                if cx.covering(&n.anchor).is_empty() {
                    out.push(Ob::new(
                        "PLAN001",
                        "unrealized_goal",
                        n,
                        format!("goal leaf {} is realized by no scenario", n.name),
                    ));
                }
                out.extend(unverified(cx, n));
            }
            "scenario" => {
                for step in &n.uses {
                    if cx.impls_of(step, &n.anchor).is_empty() {
                        out.push(Ob::new(
                            "PLAN003",
                            "unimplemented_step",
                            n,
                            format!("({step}, {}) has no impl, specific or for *", n.anchor),
                        ));
                    }
                }
                out.extend(unverified(cx, n));
            }
            "impl" | "page" => {
                let real: Vec<&str> = Cx::realizations(n).collect();
                if real.is_empty() {
                    out.push(Ob::new(
                        "PLAN004",
                        "unbound_impl",
                        n,
                        format!("{} has no realization clause", n.name),
                    ));
                } else if let Some(bad) = real.iter().find(|a| !cx.ok(a, false)) {
                    let mut ob = Ob::new(
                        "PLAN004",
                        "unbound_impl",
                        n,
                        format!("realization {bad} resolves to nothing"),
                    );
                    ob.sys004_dup = true;
                    out.push(ob);
                }
                out.extend(unverified(cx, n));
            }
            _ => {}
        }
    }
    out.sort_by(|a, b| (&a.anchor, a.rule, &a.detail).cmp(&(&b.anchor, b.rule, &b.detail)));
    out
}

/// How a scenario is started, from its first main-chain element (grmb-planning 12.6, D199).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Trigger {
    /// A `timer` or `device` actor starts it.
    Timed,
    /// Another actor, or the system, starts it.
    Other,
    /// The first element does not resolve to a known owner.
    Unknown,
}

/// The realization kinds an impl may use for a step owner kind, when the owner kind has a rule.
fn affordance(owner: &str) -> Option<&'static [&'static str]> {
    match owner {
        "human" => Some(&["ui", "cli", "api"]),
        "external" => Some(&["handler", "api"]),
        "device" => Some(&["isr", "driver"]),
        "timer" => Some(&["handler", "isr"]),
        _ => None,
    }
}

impl<'a> Cx<'a> {
    /// The kind word of a step owner: `system`, an actor kind word, or `None` when unknown.
    fn owner_kind(&self, step: &str) -> Option<&str> {
        let owner = self.nodes.get(step)?.owner.as_str();
        if owner == "system" {
            return Some("system");
        }
        self.nodes.get(owner)?.actor_kind.as_deref()
    }

    /// How the scenario `sc` starts, following leading includes.
    fn trigger(&self, sc: &str, seen: &mut BTreeSet<String>) -> Trigger {
        if !seen.insert(sc.to_owned()) {
            return Trigger::Unknown;
        }
        let Some(first) = self.nodes.get(sc).and_then(|n| n.first.as_deref()) else {
            return Trigger::Unknown;
        };
        if first.starts_with("scenario/") {
            return self.trigger(first, seen);
        }
        match self.owner_kind(first) {
            Some("timer" | "device") => Trigger::Timed,
            Some(_) => Trigger::Other,
            None => Trigger::Unknown,
        }
    }

    /// Scenarios an impl serves: its own, or every scenario using the step for `for *`.
    fn served(&self, i: &PlanNode, step: &str) -> Vec<&'a PlanNode> {
        match i.impl_scenario.as_deref() {
            Some(sc) => self.nodes.get(sc).copied().into_iter().collect(),
            None => self
                .nodes
                .values()
                .copied()
                .filter(|s| s.kind == "scenario" && s.uses.iter().any(|u| u == step))
                .collect(),
        }
    }

    /// Pages reachable from an entry page along `from` edges (grmb-planning 12.7).
    fn reach(&self) -> BTreeSet<&'a str> {
        let mut reach: BTreeSet<&str> = self
            .nodes
            .values()
            .filter(|n| n.kind == "page" && n.entry)
            .map(|n| n.anchor.as_str())
            .collect();
        loop {
            let more: Vec<&str> = self
                .nodes
                .values()
                .filter(|n| n.kind == "page" && !reach.contains(n.anchor.as_str()))
                .filter(|n| n.from.iter().any(|f| reach.contains(f.as_str())))
                .map(|n| n.anchor.as_str())
                .collect();
            if more.is_empty() {
                return reach;
            }
            reach.extend(more);
        }
    }
}

/// PLAN007 for an impl: its realization kinds against the affordance rule of the step owner.
fn affordance_ob(cx: &Cx<'_>, i: &PlanNode) -> Option<Ob> {
    let step = i.impl_step.as_deref()?;
    let kinds: BTreeSet<&str> = i
        .clauses
        .iter()
        .filter_map(|c| c.realization_kind.as_deref())
        .collect();
    if kinds.is_empty() {
        return None;
    }
    let owner = cx.owner_kind(step)?;
    let any = |want: &[&str]| kinds.iter().any(|k| want.contains(k));
    let list = kinds.iter().copied().collect::<Vec<_>>().join(", ");
    let mut ob = Ob::new(
        "PLAN007",
        "",
        i,
        format!("realization kinds [{list}] do not satisfy the affordance rule of a {owner} step"),
    );
    if owner == "system" {
        if any(&["handler"]) {
            return None;
        }
        if !any(&["isr", "driver"]) {
            return Some(ob);
        }
        let served = cx.served(i, step);
        let triggers: Vec<Trigger> = served
            .iter()
            .map(|s| cx.trigger(&s.anchor, &mut BTreeSet::new()))
            .collect();
        tracing::debug!(impl_ = %i.anchor, ?triggers, "system step isr/driver needs timed triggers");
        if triggers.is_empty() || triggers.contains(&Trigger::Other) {
            return Some(ob);
        }
        if triggers.contains(&Trigger::Unknown) {
            ob.undecided = true;
            return Some(ob);
        }
        return None;
    }
    let want = affordance(owner)?;
    (!any(want)).then_some(ob)
}

/// PLAN009 for an impl: the Must owner of a bound realization differs from its `in node`.
fn node_mismatch_ob(cx: &Cx<'_>, owners: &Owners, i: &PlanNode) -> Option<Ob> {
    let want = i.node.as_deref()?.trim_start_matches("node/");
    for c in i.clauses.iter().filter(|c| c.realization_kind.is_some()) {
        let Some(res) = cx.results.get(c.anchor.as_str()) else {
            continue;
        };
        for (hit, _) in &res.matches {
            let Some(uo) = owners.units.get(&hit.symref) else {
                continue;
            };
            if let gob_walk::Owner::Must(n) = &uo.merged.owner
                && n.as_str().trim_start_matches("node/") != want
            {
                return Some(Ob::new(
                    "PLAN009",
                    "",
                    i,
                    format!(
                        "{} is declared in node {want} but {} is owned by {}",
                        i.name,
                        hit.symref,
                        n.as_str()
                    ),
                ));
            }
        }
    }
    None
}

/// PLAN002, PLAN007, PLAN008, PLAN009 and PLAN010: the rules that are findings only, never graph JSON.
fn finding_obligations(cx: &Cx<'_>, owners: &Owners) -> Vec<Ob> {
    let mut out: Vec<Ob> = Vec::new();
    let included: BTreeSet<&str> = cx
        .nodes
        .values()
        .filter(|n| n.kind == "scenario")
        .flat_map(|n| n.includes.iter().map(String::as_str))
        .collect();
    let reach = cx.reach();
    for n in cx.nodes.values() {
        match n.kind {
            "scenario" => {
                let coarse = n.realizes.iter().find(|g| {
                    cx.nodes
                        .get(g.as_str())
                        .is_some_and(|g| g.kind == "goal" && !g.leaf)
                });
                if let Some(g) = coarse {
                    out.push(Ob::new(
                        "PLAN002",
                        "",
                        n,
                        format!("{} realizes {g}, a goal with children", n.name),
                    ));
                }
                if n.realizes.is_empty() && !included.contains(n.anchor.as_str()) {
                    out.push(Ob::new(
                        "PLAN010",
                        "",
                        n,
                        format!("{} realizes no goal and no scenario includes it", n.name),
                    ));
                }
            }
            "impl" => {
                out.extend(affordance_ob(cx, n));
                out.extend(node_mismatch_ob(cx, owners, n));
                if let Some(p) = n.pages.iter().find(|p| !reach.contains(p.as_str())) {
                    out.push(Ob::new(
                        "PLAN008",
                        "",
                        n,
                        format!("{} requires page {p}, which no entry reaches", n.name),
                    ));
                }
            }
            "page" if !reach.contains(n.anchor.as_str()) => {
                out.push(Ob::new(
                    "PLAN008",
                    "",
                    n,
                    format!("page {} is not reachable from an entry page", n.name),
                ));
            }
            _ => {}
        }
    }
    out.sort_by(|a, b| (&a.anchor, a.rule, &a.detail).cmp(&(&b.anchor, b.rule, &b.detail)));
    out
}

fn obligations(cx: &Cx<'_>) -> Vec<Value> {
    typed_obligations(cx).iter().map(Ob::json).collect()
}

/// The planning obligations as binding findings, with the subjects each PLAN rule examined.
#[derive(Debug, Default)]
pub struct PlanFindings {
    /// PLAN001 to PLAN010 findings (Error when decided, Unresolved on a May selector or unknown trigger).
    pub findings: Vec<BindFinding>,
    /// Subjects examined per rule.
    pub subjects: BTreeMap<&'static str, usize>,
}

// frob:ticket 01M69AXE9FSCASMNDSMA1A7YMH
// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF
/// Lift the PLAN001 to PLAN010 obligations of the planning graph to findings.
pub fn findings(model: &Model, rel: &Relation, owners: &Owners) -> PlanFindings {
    let mut out = PlanFindings::default();
    if model.plan.is_empty() {
        return out;
    }
    let cx = Cx::build(model, rel);
    for n in cx.nodes.values() {
        match n.kind {
            "goal" if n.leaf => {
                *out.subjects.entry("PLAN001").or_default() += 1;
                *out.subjects.entry("PLAN005").or_default() += 1;
            }
            "scenario" => {
                *out.subjects.entry("PLAN003").or_default() += n.uses.len();
                *out.subjects.entry("PLAN005").or_default() += 1;
                *out.subjects.entry("PLAN002").or_default() += 1;
                *out.subjects.entry("PLAN010").or_default() += 1;
            }
            "impl" | "page" => {
                *out.subjects.entry("PLAN004").or_default() += 1;
                *out.subjects.entry("PLAN005").or_default() += 1;
                if n.kind == "page" || !n.pages.is_empty() {
                    *out.subjects.entry("PLAN008").or_default() += 1;
                }
                if n.kind == "impl" {
                    if n.clauses.iter().any(|c| c.realization_kind.is_some()) {
                        *out.subjects.entry("PLAN007").or_default() += 1;
                    }
                    if n.node.is_some() {
                        *out.subjects.entry("PLAN009").or_default() += 1;
                    }
                }
            }
            _ => {}
        }
    }
    let site: BTreeMap<&str, (&str, (usize, usize))> = model
        .plan
        .iter()
        .map(|p| {
            (
                p.node.anchor.as_str(),
                (p.file.as_str(), (p.node.span.start, p.node.span.end)),
            )
        })
        .collect();
    let mut obs = typed_obligations(&cx);
    obs.extend(finding_obligations(&cx, owners));
    for ob in obs {
        if ob.sys004_dup {
            tracing::debug!(anchor = %ob.anchor, "PLAN004 on an empty selector is SYS004; not reported twice");
            continue;
        }
        let at = site.get(ob.anchor.as_str()).copied();
        tracing::debug!(rule = ob.rule, anchor = %ob.anchor, undecided = ob.undecided, "plan obligation lifted");
        out.findings.push(if ob.undecided {
            BindFinding::unresolved(ob.rule, Reason::MayOnlyOwner, &ob.detail, &ob.anchor, at)
        } else {
            BindFinding {
                rule: ob.rule,
                severity: Severity::Error,
                file: at.map(|(f, _)| f.to_owned()),
                range: at.map(|(_, r)| r),
                message: ob.detail,
                reason: None,
                anchor: ob.anchor,
            }
        });
    }
    tracing::info!(
        findings = out.findings.len(),
        "plan obligations lifted to findings"
    );
    out
}

fn edge_json(e: &PlanEdge) -> Value {
    let mut v = json!({
        "kind": e.kind, "from": e.from, "to": e.to, "anchor": null, "contract": null,
    });
    if let Some(s) = &e.scenario {
        v["scenario"] = json!(s);
    }
    v
}

/// Compute statuses, roll-ups, edges and obligations of the planning graph.
pub fn report(model: &Model, rel: &Relation) -> PlanReport {
    if model.plan.is_empty() {
        return PlanReport::default();
    }
    let cx = Cx::build(model, rel);
    let mut fields = BTreeMap::new();
    for n in cx.nodes.values() {
        let mut m = Map::new();
        m.insert("status".into(), json!(cx.status(n, false).word()));
        m.insert("status_hi".into(), json!(cx.status(n, true).word()));
        m.insert("level".into(), level(n));
        m.insert("system".into(), json!(n.system));
        if let Some(p) = plan_object(n) {
            m.insert("plan".into(), p);
        }
        if let Some(r) = cx.rollup(n) {
            m.insert("rollup".into(), r);
        }
        fields.insert(n.anchor.clone(), m);
    }
    let out = PlanReport {
        fields,
        edges: model.plan_edges.iter().map(edge_json).collect(),
        obligations: obligations(&cx),
    };
    tracing::info!(
        entities = out.fields.len(),
        edges = out.edges.len(),
        obligations = out.obligations.len(),
        "plan report built"
    );
    out
}
