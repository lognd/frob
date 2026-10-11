//! The node kinds a file must contain for a plan to run (grl-spec.md 7.4, plugins.md 6.2).

use crate::plan::{Op, OpId, StrId};

// frob:ticket 01M3ZX7EQ5NARR4Z2SAY4H23AQ
/// The sorted, deduplicated kinds bound by the top-level `find` clauses.
///
/// Only clause binders count: a file lacking such a kind has no candidate for the clause, so the
/// rule cannot fire. Kinds under `no`, `count` or `or` are not required and are left out.
pub fn prefilter_kinds(ops: &[Op], clauses: &[OpId]) -> Vec<StrId> {
    let mut kinds: Vec<StrId> = clauses
        .iter()
        .filter_map(|&c| match ops.get(c as usize) {
            Some(Op::Find { kind, .. }) => Some(*kind),
            _ => None,
        })
        .collect();
    kinds.sort_unstable();
    kinds.dedup();
    kinds
}
