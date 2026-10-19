//! Claim verdicts over the declared flows (grmb-spec 4.4): `noflow` and `reach` are decided on
//! the flow graph, `bound` is Unresolved while the model carries nothing to compute it from.

// frob:ticket 01M4FGYHSXQXJD0JXFV2AZCED5

use std::collections::{BTreeMap, VecDeque};

use crate::ast::{EntityKind, Header, RefPath};
use crate::model::Index;

/// The verdict on one claim proposition.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Verdict {
    /// The proposition holds on the declared flows.
    Satisfied,
    /// The proposition fails; the message carries the witness.
    Refuted(String),
    /// The model cannot decide it; the message gives the reason.
    Unresolved(String),
}

/// Resolve `path` from `ctx` to a node record index of `idx`, if it names a node.
fn node_of(idx: &Index<'_>, ctx: &[String], path: &RefPath) -> Option<usize> {
    let r = idx.resolve(ctx, path)?;
    (idx.kind(r.rec) == EntityKind::Node).then_some(r.rec)
}

/// The shortest declared flow path from node `from` to node `to`, as flow names; `None` when none.
fn flow_path(idx: &Index<'_>, from: usize, to: usize) -> Option<Vec<String>> {
    let mut edges: BTreeMap<usize, Vec<(usize, String)>> = BTreeMap::new();
    for rec in idx
        .entities
        .iter()
        .filter(|r| r.entity.kind == EntityKind::Flow)
    {
        if let Header::Flow { from: f, to: t } = &rec.entity.header
            && let (Some(a), Some(b)) = (node_of(idx, &rec.ctx, f), node_of(idx, &rec.ctx, t))
        {
            edges.entry(a).or_default().push((b, rec.full.clone()));
        }
    }
    let mut prev: BTreeMap<usize, (usize, String)> = BTreeMap::new();
    let mut queue = VecDeque::from([from]);
    while let Some(n) = queue.pop_front() {
        if n == to && n != from {
            break;
        }
        for (next, flow) in edges.get(&n).into_iter().flatten() {
            if *next != from && !prev.contains_key(next) {
                prev.insert(*next, (n, flow.clone()));
                queue.push_back(*next);
            }
        }
    }
    let mut path = Vec::new();
    let mut at = to;
    while let Some((p, flow)) = prev.get(&at) {
        path.push(flow.clone());
        at = *p;
    }
    path.reverse();
    (!path.is_empty()).then_some(path)
}

/// Decide `noflow`/`reach` `a -> b` stated inside prefix `ctx`.
///
/// `degraded` is true when a hole or unread file may hide flows, so a missing path proves nothing.
pub fn flow_verdict(
    idx: &Index<'_>,
    ctx: &[String],
    (src, dst): (&RefPath, &RefPath),
    reach: bool,
    degraded: bool,
) -> Verdict {
    let (Some(from), Some(to)) = (node_of(idx, ctx, src), node_of(idx, ctx, dst)) else {
        return Verdict::Unresolved(format!(
            "`{} -> {}`: an operand resolves to no node, so no verdict can be given",
            src.written(),
            dst.written()
        ));
    };
    let path = flow_path(idx, from, to);
    let verdict = match (reach, path, degraded) {
        (false, Some(names), _) => Verdict::Refuted(format!(
            "`noflow {} -> {}` is refuted by the declared flow path {}",
            src.written(),
            dst.written(),
            names.join(" -> ")
        )),
        (_, None, true) => Verdict::Unresolved(format!(
            "no declared flow path from `{}` to `{}`, but the model has holes or unread files that may declare one",
            src.written(),
            dst.written()
        )),
        (false, None, false) | (true, Some(_), _) => Verdict::Satisfied,
        (true, None, false) => Verdict::Refuted(format!(
            "`reach {} -> {}` is refuted: no declared flow path connects them",
            src.written(),
            dst.written()
        )),
    };
    tracing::debug!(?verdict, reach, "flow claim decided");
    verdict
}

/// Decide `bound METRIC TARGET <= Q`: the model carries no measured values, so it is Unresolved.
pub fn bound_verdict(metric: &str, target: &RefPath) -> Verdict {
    Verdict::Unresolved(format!(
        "`bound {metric} {}`: the model declares no measured `{metric}` for it, so the bound cannot be computed",
        target.written()
    ))
}

/// Decide the evidence side of a claim: above L1 with no evidence and not `assumed` is Unresolved.
pub fn evidence_verdict(claim: &str, proof: &str, has_evidence: bool) -> Verdict {
    if has_evidence || proof == "L1" {
        return Verdict::Satisfied;
    }
    let verdict = Verdict::Unresolved(format!(
        "claim `{claim}` requires proof {proof} but has no evidence and is not assumed, so it cannot be satisfied"
    ));
    tracing::debug!(claim, proof, "claim has no evidence");
    verdict
}
