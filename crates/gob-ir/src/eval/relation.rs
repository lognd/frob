//! Binary relations over nodes with Kleene truth and a least-fixpoint closure.

use std::collections::{BTreeMap, BTreeSet};

use crate::answer::Truth;
use crate::term::NodeId;

/// A finite binary relation over nodes; each stored pair is `Yes` or `Unknown`.
///
/// An absent pair is `No` as far as the relation knows (see [`crate::eval::Ctx::holds`]
/// for the poison-aware reading). Composition is max-min, so a path is as certain as
/// its weakest edge and alternatives are as certain as their strongest.
///
/// ```
/// use gob_ir::{Relation, Truth};
/// # use gob_ir::NodeId;
/// let _ = (Relation::new(), Truth::Yes);
/// ```
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Relation {
    pairs: BTreeMap<(NodeId, NodeId), Truth>,
}

impl Relation {
    /// The empty relation.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add `(a, b)` at truth `t`, keeping the stronger of old and new; `No` is ignored.
    pub fn insert(&mut self, a: NodeId, b: NodeId, t: Truth) {
        if t == Truth::No {
            return;
        }
        let e = self.pairs.entry((a, b)).or_insert(t);
        *e = (*e).max(t);
    }

    /// The stored truth of `(a, b)`; `No` when absent.
    pub fn get(&self, a: NodeId, b: NodeId) -> Truth {
        self.pairs.get(&(a, b)).copied().unwrap_or(Truth::No)
    }

    /// Number of stored pairs.
    pub fn len(&self) -> usize {
        self.pairs.len()
    }

    /// True when no pair is stored.
    pub fn is_empty(&self) -> bool {
        self.pairs.is_empty()
    }

    /// Stored pairs in order.
    pub fn iter(&self) -> impl Iterator<Item = (NodeId, NodeId, Truth)> + '_ {
        self.pairs.iter().map(|(&(a, b), &t)| (a, b, t))
    }

    /// Successors of `a` with their truth.
    pub fn image(&self, a: NodeId) -> Vec<(NodeId, Truth)> {
        self.pairs
            .range((a, NodeId(0))..=(a, NodeId(u32::MAX)))
            .map(|(&(_, b), &t)| (b, t))
            .collect()
    }

    /// Union (disjunction).
    #[must_use]
    pub fn union(&self, other: &Self) -> Self {
        let mut out = self.clone();
        for (a, b, t) in other.iter() {
            out.insert(a, b, t);
        }
        out
    }

    /// Relational composition `self ; other` (conjunction along, disjunction across).
    #[must_use]
    pub fn compose(&self, other: &Self) -> Self {
        let mut out = Self::new();
        for (a, b, t1) in self.iter() {
            for (c, t2) in other.image(b) {
                out.insert(a, c, t1.and(t2));
            }
        }
        out
    }

    /// Transitive closure: the least fixpoint of `R = self union (R ; self)`.
    ///
    /// A pair is `Yes` when a path of `Yes` edges exists, `Unknown` when only paths
    /// using some `Unknown` edge exist.
    #[must_use]
    pub fn closure(&self) -> Self {
        let mut adj: BTreeMap<NodeId, Vec<(NodeId, Truth)>> = BTreeMap::new();
        for (a, b, t) in self.iter() {
            adj.entry(a).or_default().push((b, t));
        }
        let mut out = Self::new();
        for &src in adj.keys() {
            let sure = reach(&adj, src, true);
            let any = reach(&adj, src, false);
            for n in &any {
                out.insert(
                    src,
                    *n,
                    if sure.contains(n) {
                        Truth::Yes
                    } else {
                        Truth::Unknown
                    },
                );
            }
        }
        out
    }
}

fn reach(
    adj: &BTreeMap<NodeId, Vec<(NodeId, Truth)>>,
    src: NodeId,
    only_yes: bool,
) -> BTreeSet<NodeId> {
    let mut seen = BTreeSet::new();
    let mut stack = vec![src];
    while let Some(n) = stack.pop() {
        for &(m, t) in adj.get(&n).map_or(&[][..], Vec::as_slice) {
            if (only_yes && t != Truth::Yes) || !seen.insert(m) {
                continue;
            }
            stack.push(m);
        }
    }
    seen
}
