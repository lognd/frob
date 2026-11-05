//! SYS015 over owner-derived nodes: the behaviour-to-architecture check.
//!
//! `grimble-model` checks `succ` pairs whose steps sit in a *declared* node (an impl `in node`, or
//! the actor's `node`). This pass adds the node an impl takes from the owner of the code its
//! `realization` selectors hit (`owner(u)` of the bound identities), which only binding can know.
//! It reports only pairs where an endpoint's node was derived, so the model's findings are never
//! repeated; a node it cannot decide is Unresolved, never reported clean.

// frob:ticket 01M4FDBHWDCX31YDY4ZHDTTYWR

use std::collections::BTreeSet;

use gob_rules::Severity;
use grimble_model::plan_index::PlanNode;

use crate::model::Model;
use crate::owner::Owners;
use crate::plan::Cx;
use crate::types::{BindFinding, Reason};

const RULE: &str = "SYS015";

/// A node name without its `node/` anchor prefix.
fn bare(node: &str) -> &str {
    node.trim_start_matches("node/")
}

/// Where a step use sits, and whether binding (not the model) decided it.
struct Placed {
    node: String,
    derived: bool,
}

/// The unique node owning every code unit the realization clauses of `imp` hit, if there is one.
fn derived_node(cx: &Cx<'_>, owners: &Owners, imp: &PlanNode) -> Option<String> {
    let mut found: BTreeSet<String> = BTreeSet::new();
    for c in imp.clauses.iter().filter(|c| c.realization_kind.is_some()) {
        let res = cx.results.get(c.anchor.as_str())?;
        for (hit, _) in &res.matches {
            match &owners.units.get(&hit.symref)?.merged.owner {
                gob_walk::Owner::Must(n) => {
                    found.insert(bare(n.as_str()).to_owned());
                }
                _ => return None,
            }
        }
    }
    (found.len() == 1).then(|| found.into_iter().next().unwrap_or_default())
}

/// The actor path that owns `step` (`step/a.b.name` is owned by actor `a.b`).
fn actor_path(step: &str) -> Option<&str> {
    step.strip_prefix("step/")?.rsplit_once('.').map(|(a, _)| a)
}

/// The declared node of the actor owning `step`.
fn actor_node(cx: &Cx<'_>, step: &str) -> Option<String> {
    let actor = actor_path(step)?;
    let tail = format!(".{actor}");
    let want = format!("actor/{actor}");
    let found = cx
        .nodes
        .values()
        .find(|n| n.kind == "actor" && (n.anchor == want || n.anchor.ends_with(&tail)))?;
    found.node.as_deref().map(|n| bare(n).to_owned())
}

/// What binding can say about the node of a step use.
enum Place {
    /// Decided.
    At(Placed),
    /// An impl places the step but binding cannot name one node for it.
    Undecided,
    /// No impl and no actor node: the model owns that case.
    Absent,
}

/// The node of `step` as used in `scenario`.
fn place(cx: &Cx<'_>, owners: &Owners, scenario: &str, step: &str) -> Place {
    let impls = cx.impls_of(step, scenario);
    if impls.is_empty() {
        return actor_node(cx, step).map_or(Place::Absent, |node| {
            Place::At(Placed {
                node,
                derived: false,
            })
        });
    }
    let mut placed: Vec<Placed> = Vec::new();
    for i in impls {
        let one = match i.node.as_deref() {
            Some(n) => Some(Placed {
                node: bare(n).to_owned(),
                derived: false,
            }),
            None => derived_node(cx, owners, i).map(|node| Placed {
                node,
                derived: true,
            }),
        };
        match one {
            Some(p) => placed.push(p),
            None => return Place::Undecided,
        }
    }
    let first = placed.first().map(|p| p.node.clone()).unwrap_or_default();
    if placed.iter().any(|p| p.node != first) {
        return Place::Undecided;
    }
    Place::At(Placed {
        node: first,
        derived: placed.iter().any(|p| p.derived),
    })
}

/// Is there a flow from node `from` to node `to`?
fn has_flow(model: &Model, from: &str, to: &str) -> bool {
    model
        .entities
        .values()
        .any(|e| matches!(&e.ends, Some((Some(a), Some(b))) if bare(a) == from && bare(b) == to))
}

/// Lift one SYS015 Error for each `succ` pair that crosses nodes on a derived endpoint with no flow.
pub(crate) fn lift(model: &Model, cx: &Cx<'_>, owners: &Owners) -> Vec<BindFinding> {
    let mut out = Vec::new();
    let mut seen: BTreeSet<(String, String)> = BTreeSet::new();
    for e in model.plan_edges.iter().filter(|e| e.kind == "succ") {
        let Some(scenario) = e.scenario.as_deref() else {
            continue;
        };
        let site = model.plan.iter().find(|p| p.node.anchor == scenario);
        let (a, b) = match (
            place(cx, owners, scenario, &e.from),
            place(cx, owners, scenario, &e.to),
        ) {
            (Place::At(a), Place::At(b)) => (a, b),
            (Place::Undecided, _) | (_, Place::Undecided) => {
                if seen.insert((e.from.clone(), e.to.clone())) {
                    tracing::debug!(from = %e.from, to = %e.to, "SYS015 node undecided; Unresolved");
                    out.push(BindFinding::unresolved(
                        RULE,
                        Reason::MayOnlyOwner,
                        &format!(
                            "{} fires {}, but the node of a step use is not decidable",
                            e.from, e.to
                        ),
                        scenario,
                        site.map(|p| (p.file.as_str(), (p.node.span.start, p.node.span.end))),
                    ));
                }
                continue;
            }
            _ => continue,
        };
        if !(a.derived || b.derived) || a.node == b.node || has_flow(model, &a.node, &b.node) {
            continue;
        }
        if !seen.insert((e.from.clone(), e.to.clone())) {
            continue;
        }
        tracing::debug!(from = %e.from, to = %e.to, "SYS015 pair crosses nodes with no flow");
        out.push(BindFinding {
            rule: RULE,
            severity: Severity::Error,
            file: site.map(|p| p.file.clone()),
            range: site.map(|p| (p.node.span.start, p.node.span.end)),
            message: format!(
                "{} fires {}, but node {} has no flow to node {}",
                e.from, e.to, a.node, b.node
            ),
            reason: None,
            anchor: scenario.to_owned(),
        });
    }
    out
}
