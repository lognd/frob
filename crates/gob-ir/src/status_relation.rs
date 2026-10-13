//! A keyed binary relation whose pairs carry a resolution [`Status`], read as lo/hi bounds.

use std::collections::{BTreeMap, BTreeSet};

use crate::answer::{Answer, Truth};
use crate::scope::Status;

/// A binary relation over keys `K` with a [`Status`] per pair: `Must` pairs form the `lo` bound,
/// `Must` and `May` pairs the `hi` bound, and a source on the Unknown frontier may relate to
/// anything (top of `hi`). This is the one structure rules read for call and import edges.
///
/// ```
/// use gob_ir::{Status, StatusRelation, Truth};
///
/// let mut r = StatusRelation::new();
/// r.insert("a", "b", Status::Must);
/// r.insert("a", "c", Status::May);
/// r.mark_unknown_out("d");
/// assert!(r.lo(&"a", &"b") && !r.lo(&"a", &"c"));
/// assert!(r.hi(&"a", &"c") && !r.hi(&"a", &"z"));
/// assert!(r.hi(&"d", &"z") && !r.lo(&"d", &"z"));
/// assert_eq!(r.truth(&"a", &"c"), Truth::Unknown);
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StatusRelation<K: Ord> {
    pairs: BTreeMap<(K, K), Status>,
    unknown_out: BTreeSet<K>,
}

impl<K: Ord> Default for StatusRelation<K> {
    fn default() -> Self {
        Self {
            pairs: BTreeMap::new(),
            unknown_out: BTreeSet::new(),
        }
    }
}

impl<K: Ord + Clone> StatusRelation<K> {
    /// The empty relation.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add `(a, b)` at `status`, keeping the stronger of old and new; `Unknown` marks `a`
    /// on the frontier instead of storing a pair.
    pub fn insert(&mut self, a: K, b: K, status: Status) {
        if status == Status::Unknown {
            self.unknown_out.insert(a);
            return;
        }
        let e = self.pairs.entry((a, b)).or_insert(status);
        *e = (*e).max(status);
    }

    /// Mark `a` as having an Unknown outgoing edge (it may relate to anything).
    pub fn mark_unknown_out(&mut self, a: K) {
        self.unknown_out.insert(a);
    }

    /// True when `a` is on the Unknown frontier.
    pub fn is_unknown_out(&self, a: &K) -> bool {
        self.unknown_out.contains(a)
    }

    /// The status stored for `(a, b)`, if any.
    pub fn status(&self, a: &K, b: &K) -> Option<Status> {
        self.pairs.get(&(a.clone(), b.clone())).copied()
    }

    /// The lo bound: the pair is proved (`Must`).
    pub fn lo(&self, a: &K, b: &K) -> bool {
        self.status(a, b) == Some(Status::Must)
    }

    /// The hi bound: the pair may hold (`Must`, `May`, or `a` is on the Unknown frontier).
    pub fn hi(&self, a: &K, b: &K) -> bool {
        self.status(a, b).is_some() || self.unknown_out.contains(a)
    }

    /// Kleene truth of `(a, b)`: `Yes` at lo, `Unknown` inside hi only, else `No`.
    pub fn truth(&self, a: &K, b: &K) -> Truth {
        if self.lo(a, b) {
            Truth::Yes
        } else if self.hi(a, b) {
            Truth::Unknown
        } else {
            Truth::No
        }
    }

    /// The bounds of `(a, b)` as an [`Answer`].
    pub fn answer(&self, a: &K, b: &K) -> Answer<bool> {
        Answer::Bounds {
            lo: self.lo(a, b),
            hi: self.hi(a, b),
        }
    }

    /// Successors of `a` with their status, in order.
    pub fn image<'a>(&'a self, a: &K) -> impl Iterator<Item = (&'a K, Status)> + 'a {
        let a = a.clone();
        self.pairs
            .iter()
            .filter(move |((x, _), _)| *x == a)
            .map(|((_, y), &s)| (y, s))
    }

    /// Stored pairs in order.
    pub fn iter(&self) -> impl Iterator<Item = (&K, &K, Status)> + '_ {
        self.pairs.iter().map(|((a, b), &s)| (a, b, s))
    }

    /// The Unknown frontier.
    pub fn unknown_out(&self) -> impl Iterator<Item = &K> + '_ {
        self.unknown_out.iter()
    }

    /// Number of stored pairs.
    pub fn len(&self) -> usize {
        self.pairs.len()
    }

    /// True when no pair is stored.
    pub fn is_empty(&self) -> bool {
        self.pairs.is_empty()
    }
}
