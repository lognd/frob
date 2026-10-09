//! Edge atoms and bounded `reaches` over a [`Relation`] (grl-spec.md 7.0.2 and 7.0.3).
//!
//! A relation's stored `Yes` pairs are `R_lo` (Must edges), its stored `Unknown` pairs are
//! `R_hi` minus `R_lo` (May edges) and its `unknown_out` nodes are the frontier: an edge out of one
//! of them may go anywhere. An atom is Yes in `R_lo`, No outside `R_hi` and Unknown between; the
//! doubt names the May edge or the frontier node.

use std::collections::BTreeSet;

use gob_ir::{NodeId, Relation, Truth};

use super::super::core::{Doubt, Verdict};
use crate::plan::Certainty;

/// Applies `certainly`/`possibly` to a verdict: `certainly` turns Unknown into No, `possibly`
/// into Yes; the default keeps it. (The assumption is the outcome layer's to record.)
fn collapse(v: Verdict, certainty: Certainty) -> Verdict {
    match (v.truth, certainty) {
        (Truth::Unknown, Certainty::Certainly) => Verdict::no(),
        (Truth::Unknown, Certainty::Possibly) => Verdict::yes(),
        _ => v,
    }
}

/// `a VERB b` over `rel`.
pub(crate) fn verb(rel: &Relation, a: NodeId, b: NodeId, certainty: Certainty) -> Verdict {
    let stored = rel
        .image(a)
        .into_iter()
        .find(|&(m, _)| m == b)
        .map(|(_, t)| t);
    let v = match stored {
        Some(Truth::Yes) => Verdict::yes(),
        Some(_) => Verdict::unknown(Doubt::MayEdge { from: a, to: b }),
        None if rel.is_unknown_out(a) => Verdict::unknown(Doubt::Frontier { nodes: vec![a] }),
        None => Verdict::no(),
    };
    collapse(v, certainty)
}

/// Nodes first reached from `layer` by one more edge of `rel`, not yet in `reached`.
fn step(
    rel: &Relation,
    layer: &BTreeSet<NodeId>,
    reached: &BTreeSet<NodeId>,
    only_yes: bool,
) -> BTreeSet<NodeId> {
    layer
        .iter()
        .flat_map(|&n| rel.image(n))
        .filter(|&(m, t)| (!only_yes || t == Truth::Yes) && !reached.contains(&m))
        .map(|(m, _)| m)
        .collect()
}

/// The nodes reachable from `from` by 1..=`steps` edges (the Yes edges only when `only_yes`),
/// and whether one more step would add nothing (the search was exhausted).
fn within(rel: &Relation, from: NodeId, steps: u16, only_yes: bool) -> (BTreeSet<NodeId>, bool) {
    let mut reached = BTreeSet::new();
    let mut layer = BTreeSet::from([from]);
    for _ in 0..steps {
        layer = step(rel, &layer, &reached, only_yes);
        if layer.is_empty() {
            return (reached, true);
        }
        reached.extend(layer.iter().copied());
    }
    let exhausted = step(rel, &layer, &reached, only_yes).is_empty();
    (reached, exhausted)
}

/// `from reaches to via rel within n`.
///
/// Yes iff a path of at most `n` certain edges leads to `to`; else Unknown `may-edge` if `to` is
/// within `n` possible edges; else Unknown with the frontier if a node within `n` possible edges
/// (`from` included) is on it; else No if the possible-edge search was exhausted; else Unknown
/// `budget`. A certain path longer than `n` is therefore a budget Unknown, never No (7.0.3).
pub(crate) fn reaches(
    rel: &Relation,
    from: NodeId,
    to: NodeId,
    n: u16,
    certainty: Certainty,
) -> Verdict {
    let (sure, _) = within(rel, from, n, true);
    let v = if sure.contains(&to) {
        Verdict::yes()
    } else {
        let (hi, exhausted) = within(rel, from, n, false);
        if hi.contains(&to) {
            Verdict::unknown(Doubt::MayEdge { from, to })
        } else {
            let frontier: Vec<NodeId> = std::iter::once(from)
                .chain(hi.iter().copied())
                .collect::<BTreeSet<_>>()
                .into_iter()
                .filter(|&x| rel.is_unknown_out(x))
                .collect();
            if !frontier.is_empty() {
                Verdict::unknown(Doubt::Frontier { nodes: frontier })
            } else if exhausted {
                Verdict::no()
            } else {
                Verdict::unknown(Doubt::Budget { from, within: n })
            }
        }
    };
    tracing::trace!(?from, ?to, n, truth = ?v.truth, "reaches");
    collapse(v, certainty)
}

#[cfg(test)]
mod tests {
    use gob_ir::{GroupOrder, Location, NodeSpec, Operator, TermBuilder};
    use gob_text::FileInterner;

    use super::*;

    /// Ten distinct nodes of one small term.
    fn ids() -> Vec<NodeId> {
        let file = FileInterner::new().intern("a.rs");
        let mut b = TermBuilder::new("a.rs", "rust");
        let mut out = Vec::new();
        for i in 0..10u32 {
            let spec = NodeSpec::new(
                Operator::lit("int", "1"),
                Location::text(file, i * 2, i * 2 + 1),
            );
            out.push(b.node(spec, &[]).unwrap());
        }
        let root = NodeSpec::new(
            Operator::group(GroupOrder::Sequence),
            Location::text(file, 0, 20),
        );
        b.node(root, &out).unwrap();
        out
    }

    fn chain(ids: &[NodeId], len: usize, t: Truth) -> Relation {
        let mut r = Relation::new();
        for i in 0..len {
            r.insert(ids[i], ids[i + 1], t);
        }
        r
    }

    // frob:tests crates/gob-plan/src/exec/relations/edges.rs::reaches
    #[test]
    fn a_certain_path_longer_than_the_bound_is_budget_unknown() {
        let n = ids();
        let r = chain(&n, 4, Truth::Yes);
        assert_eq!(
            reaches(&r, n[0], n[4], 4, Certainty::Default).truth,
            Truth::Yes
        );
        let v = reaches(&r, n[0], n[4], 3, Certainty::Default);
        assert_eq!(v.truth, Truth::Unknown);
        assert_eq!(
            v.doubts,
            vec![Doubt::Budget {
                from: n[0],
                within: 3
            }]
        );
    }

    #[test]
    fn an_exhausted_search_is_no_and_a_may_edge_is_unknown() {
        let n = ids();
        let r = chain(&n, 2, Truth::Yes);
        assert_eq!(
            reaches(&r, n[0], n[9], 5, Certainty::Default).truth,
            Truth::No
        );
        let mut m = chain(&n, 1, Truth::Yes);
        m.insert(n[1], n[2], Truth::Unknown);
        let v = reaches(&m, n[0], n[2], 2, Certainty::Default);
        assert_eq!(
            v.doubts,
            vec![Doubt::MayEdge {
                from: n[0],
                to: n[2]
            }]
        );
        assert_eq!(
            reaches(&m, n[0], n[2], 2, Certainty::Certainly).truth,
            Truth::No
        );
        assert_eq!(
            reaches(&m, n[0], n[2], 2, Certainty::Possibly).truth,
            Truth::Yes
        );
    }

    #[test]
    fn a_frontier_node_in_reach_blocks_no_and_cycles_terminate() {
        let n = ids();
        let mut r = chain(&n, 1, Truth::Yes);
        r.mark_unknown_out(n[1]);
        let v = reaches(&r, n[0], n[7], 3, Certainty::Default);
        assert_eq!(v.doubts, vec![Doubt::Frontier { nodes: vec![n[1]] }]);
        let mut c = chain(&n, 1, Truth::Yes);
        c.insert(n[1], n[0], Truth::Yes);
        assert_eq!(
            reaches(&c, n[0], n[0], 2, Certainty::Default).truth,
            Truth::Yes
        );
        let line = chain(&n, 1, Truth::Yes);
        assert_eq!(
            reaches(&line, n[0], n[0], 4, Certainty::Default).truth,
            Truth::No
        );
    }

    // frob:tests crates/gob-plan/src/exec/relations/edges.rs::verb
    #[test]
    fn verb_atoms_follow_lo_hi_and_the_frontier() {
        let n = ids();
        let mut r = Relation::new();
        r.insert(n[0], n[1], Truth::Yes);
        r.insert(n[0], n[2], Truth::Unknown);
        r.mark_unknown_out(n[5]);
        assert_eq!(verb(&r, n[0], n[1], Certainty::Default).truth, Truth::Yes);
        assert_eq!(
            verb(&r, n[0], n[2], Certainty::Default).truth,
            Truth::Unknown
        );
        assert_eq!(verb(&r, n[0], n[3], Certainty::Default).truth, Truth::No);
        assert_eq!(
            verb(&r, n[5], n[3], Certainty::Default).truth,
            Truth::Unknown
        );
        assert_eq!(verb(&r, n[0], n[2], Certainty::Certainly).truth, Truth::No);
    }
}
