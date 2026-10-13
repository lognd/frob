//! Hot-context reachability: which symbols run inside vocabulary-declared hot roots.

use std::collections::{BTreeMap, VecDeque};

use crate::answer::Answer;
use crate::scope::Status;
use crate::status_relation::StatusRelation;

/// How surely a symbol executes in a hot context.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Hotness {
    /// Not reached from any root, and no reached symbol has an unresolved call.
    Cold,
    /// Not reached, but an unresolved call on a hot path may reach it.
    Unresolved,
    /// Reached only through a May edge (candidate among several targets).
    May,
    /// Reached from a root through Must edges only.
    Must,
}

/// Reachability from hot roots over a call relation, with a pack-enabled switch.
///
/// ```
/// use gob_ir::{Answer, HotContext, Hotness, Status, StatusRelation};
///
/// let mut calls = StatusRelation::new();
/// calls.insert("Update", "helper", Status::Must);
/// calls.insert("helper", "GetComponent", Status::Must);
/// calls.insert("Update", "iface", Status::May);
/// let hot = HotContext::new(&calls, ["Update"]);
/// assert_eq!(hot.hotness(&"GetComponent"), Hotness::Must);
/// assert_eq!(hot.hotness(&"iface"), Hotness::May);
/// assert_eq!(hot.answer(&"cold"), Answer::Exact(false));
/// assert_eq!(HotContext::<&str>::disabled().answer(&"x"), Answer::NotApplicable);
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HotContext<K: Ord> {
    enabled: bool,
    reached: BTreeMap<K, Status>,
    poisoned: bool,
}

impl<K: Ord + Clone> HotContext<K> {
    /// Propagate from `roots` along `calls`, taking the best path status per symbol; a reached
    /// symbol on the Unknown frontier poisons every unreached symbol to `Unresolved`.
    pub fn new(calls: &StatusRelation<K>, roots: impl IntoIterator<Item = K>) -> Self {
        let mut adj: BTreeMap<&K, Vec<(&K, Status)>> = BTreeMap::new();
        for (a, b, s) in calls.iter() {
            adj.entry(a).or_default().push((b, s));
        }
        let mut reached: BTreeMap<K, Status> = BTreeMap::new();
        let mut queue = VecDeque::new();
        for r in roots {
            reached.insert(r.clone(), Status::Must);
            queue.push_back(r);
        }
        while let Some(n) = queue.pop_front() {
            let here = reached[&n];
            for &(next, s) in adj.get(&n).into_iter().flatten() {
                let st = here.meet(s);
                if reached.get(next).is_none_or(|b| st > *b) {
                    reached.insert(next.clone(), st);
                    queue.push_back(next.clone());
                }
            }
        }
        let poisoned = reached.keys().any(|k| calls.is_unknown_out(k));
        tracing::debug!(reached = reached.len(), poisoned, "hot context propagated");
        Self {
            enabled: true,
            reached,
            poisoned,
        }
    }

    /// A context for a disabled pack: every query answers `NotApplicable`.
    pub fn disabled() -> Self {
        Self {
            enabled: false,
            reached: BTreeMap::new(),
            poisoned: false,
        }
    }

    /// The hotness of `k` (`Cold` when the pack is disabled).
    pub fn hotness(&self, k: &K) -> Hotness {
        match self.reached.get(k) {
            Some(Status::Must) => Hotness::Must,
            Some(_) => Hotness::May,
            None if self.poisoned => Hotness::Unresolved,
            None => Hotness::Cold,
        }
    }

    /// `hot(region)` as an [`Answer`]: Must is `Exact(true)`, May a `false..true` bound,
    /// Unresolved `Unknown`, Cold `Exact(false)`, a disabled pack `NotApplicable`.
    pub fn answer(&self, k: &K) -> Answer<bool> {
        if !self.enabled {
            return Answer::NotApplicable;
        }
        match self.hotness(k) {
            Hotness::Must => Answer::Exact(true),
            Hotness::May => Answer::Bounds {
                lo: false,
                hi: true,
            },
            Hotness::Unresolved => Answer::Unknown,
            Hotness::Cold => Answer::Exact(false),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/gob-ir/src/hot.rs::HotContext.new
    fn helper_called_from_update_is_must_hot() {
        let mut c = StatusRelation::new();
        c.insert("Update", "helper", Status::Must);
        c.insert("helper", "GetComponent", Status::Must);
        let h = HotContext::new(&c, ["Update"]);
        assert_eq!(h.answer(&"GetComponent"), Answer::Exact(true));
        assert_eq!(h.answer(&"other"), Answer::Exact(false));
    }

    #[test]
    // frob:tests crates/gob-ir/src/hot.rs::HotContext.answer
    fn may_edge_gives_may_and_unknown_edge_gives_unresolved() {
        let mut c = StatusRelation::new();
        c.insert("Update", "impl_a", Status::May);
        c.insert("impl_a", "deep", Status::Must);
        c.mark_unknown_out("Update");
        let h = HotContext::new(&c, ["Update"]);
        assert_eq!(h.hotness(&"deep"), Hotness::May);
        assert_eq!(h.hotness(&"elsewhere"), Hotness::Unresolved);
        assert_eq!(h.answer(&"elsewhere"), Answer::Unknown);
    }

    #[test]
    // frob:tests crates/gob-ir/src/hot.rs::HotContext.disabled
    fn disabled_pack_is_not_applicable() {
        assert_eq!(
            HotContext::<&str>::disabled().answer(&"a"),
            Answer::NotApplicable
        );
    }
}
