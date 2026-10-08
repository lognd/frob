//! Binary relations over nodes with Kleene truth and a least-fixpoint closure.

use std::collections::{BTreeMap, BTreeSet};

use crate::answer::Truth;
use crate::term::NodeId;

/// A finite binary relation over nodes; each stored pair is `Yes` or `Unknown`.
///
/// An absent pair is `No` unless its source is in the `unknown_out` frontier: a node with an
/// Unknown or unclassified outgoing edge may relate to anything, so every absent pair from it is
/// `Unknown` (the top of the hi bound). Composition is max-min, so a path is as certain as
/// its weakest edge and alternatives are as certain as their strongest.
///
/// ```
/// use gob_ir::{Location, NodeSpec, Operator, Relation, TermBuilder, Truth};
/// use gob_text::FileInterner;
///
/// let mut files = FileInterner::new();
/// let f = files.intern("a.rs");
/// let mut b = TermBuilder::new("a.rs", "rust");
/// let x = b.node(NodeSpec::new(Operator::lit("int", "1"), Location::text(f, 0, 1)), &[]).unwrap();
/// let y = b.node(NodeSpec::new(Operator::lit("int", "2"), Location::text(f, 1, 2)), &[]).unwrap();
/// let mut r = Relation::new();
/// r.insert(x, y, Truth::Unknown);
/// assert_eq!(r.get(x, y), Truth::Unknown);
/// assert_eq!(r.get(y, x), Truth::No);
/// assert_eq!(r.closure().get(x, y), Truth::Unknown);
/// ```
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Relation {
    pairs: BTreeMap<(NodeId, NodeId), Truth>,
    unknown_out: BTreeSet<NodeId>,
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

    /// Mark `a` as having an Unknown or unclassified outgoing edge (it may relate to anything).
    pub fn mark_unknown_out(&mut self, a: NodeId) {
        self.unknown_out.insert(a);
    }

    /// True when `a` is on the Unknown frontier.
    pub fn is_unknown_out(&self, a: NodeId) -> bool {
        self.unknown_out.contains(&a)
    }

    /// The nodes on the Unknown frontier.
    pub fn unknown_out(&self) -> impl Iterator<Item = NodeId> + '_ {
        self.unknown_out.iter().copied()
    }

    /// The truth of `(a, b)`: the stored pair, else `Unknown` on the frontier, else `No`.
    pub fn get(&self, a: NodeId, b: NodeId) -> Truth {
        self.pairs
            .get(&(a, b))
            .copied()
            .unwrap_or(if self.unknown_out.contains(&a) {
                Truth::Unknown
            } else {
                Truth::No
            })
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
        out.unknown_out.extend(other.unknown_out.iter().copied());
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
            if other.unknown_out.contains(&b) {
                out.unknown_out.insert(a);
            }
        }
        out.unknown_out.extend(self.unknown_out.iter().copied());
        out
    }

    /// Transitive closure: the least fixpoint of `R = self union (R ; self)`.
    ///
    /// A pair is `Yes` when a path of `Yes` edges exists, `Unknown` when only paths
    /// using some `Unknown` edge exist. Every node that can reach the `unknown_out` frontier
    /// joins it, so its absent pairs read `Unknown` rather than `No`.
    #[must_use]
    pub fn closure(&self) -> Self {
        let mut adj: BTreeMap<NodeId, Vec<(NodeId, Truth)>> = BTreeMap::new();
        for (a, b, t) in self.iter() {
            adj.entry(a).or_default().push((b, t));
        }
        let mut out = Self::new();
        out.unknown_out = self.frontier_closure();
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

    /// `unknown_out` plus every node with a stored path to it.
    fn frontier_closure(&self) -> BTreeSet<NodeId> {
        let mut rev: BTreeMap<NodeId, Vec<NodeId>> = BTreeMap::new();
        for (a, b, _) in self.iter() {
            rev.entry(b).or_default().push(a);
        }
        let mut seen = self.unknown_out.clone();
        let mut stack: Vec<NodeId> = seen.iter().copied().collect();
        while let Some(n) = stack.pop() {
            for &m in rev.get(&n).map_or(&[][..], Vec::as_slice) {
                if seen.insert(m) {
                    stack.push(m);
                }
            }
        }
        seen
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
