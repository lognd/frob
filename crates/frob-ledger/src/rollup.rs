//! Derived story points: a parent's points are the rollup of its pointed children.
//!
//! A ticket with at least one pointed descendant is estimated by them: its
//! derived points are the sum over its children of each child's effective
//! points, where a child's effective points are its own derived points when it
//! has pointed children and its entered points otherwise. Unpointed children
//! add nothing and closed children still count (the work was part of the story).
//! Capacity counts leaves only, so a member whose ancestor is also a member is
//! covered by that ancestor and counted as zero (pm-enforcement.md section 4).
// frob:ticket 01M4FDAKV07ZFX861ZHJKMRAQ6

use std::collections::{BTreeMap, BTreeSet};

use crate::id::TicketId;
use crate::index::Summary;

/// The points of one ticket, entered and derived.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Rolled {
    /// Points typed on the ticket itself.
    pub entered: Option<u32>,
    /// Sum of the children's effective points; `None` when no descendant is pointed.
    pub derived: Option<u32>,
}

impl Rolled {
    /// The points that count: derived when children are pointed, else entered.
    #[must_use]
    pub fn effective(self) -> Option<u32> {
        self.derived.or(self.entered)
    }

    /// True when both are present and differ.
    #[must_use]
    pub fn mismatched(self) -> bool {
        matches!((self.entered, self.derived), (Some(e), Some(d)) if e != d)
    }
}

/// Entered and derived points of every ticket, built once from the summaries.
#[derive(Debug, Clone, Default)]
pub struct Rollup {
    rolled: BTreeMap<TicketId, Rolled>,
    parent: BTreeMap<TicketId, TicketId>,
}

impl Rollup {
    /// Roll up `all`; a cycle in the parent chain is cut where it closes.
    #[must_use]
    pub fn build(all: &[Summary]) -> Self {
        let mut kids: BTreeMap<TicketId, Vec<TicketId>> = BTreeMap::new();
        let mut parent = BTreeMap::new();
        for s in all {
            if let Some(p) = s.parent {
                kids.entry(p).or_default().push(s.id);
                parent.insert(s.id, p);
            }
        }
        let entered: BTreeMap<TicketId, Option<u32>> = all
            .iter()
            .map(|s| (s.id, s.points.map(u32::from)))
            .collect();
        let mut rolled = BTreeMap::new();
        for s in all {
            let mut path = BTreeSet::new();
            Self::visit(s.id, &kids, &entered, &mut rolled, &mut path);
        }
        Self { rolled, parent }
    }

    fn visit(
        id: TicketId,
        kids: &BTreeMap<TicketId, Vec<TicketId>>,
        entered: &BTreeMap<TicketId, Option<u32>>,
        rolled: &mut BTreeMap<TicketId, Rolled>,
        path: &mut BTreeSet<TicketId>,
    ) -> Rolled {
        if let Some(r) = rolled.get(&id) {
            return *r;
        }
        if !path.insert(id) {
            tracing::warn!(ticket = %id, "parent cycle cut while deriving points");
            return Rolled::default();
        }
        let mut sum: Option<u32> = None;
        for k in kids.get(&id).into_iter().flatten() {
            if let Some(p) = Self::visit(*k, kids, entered, rolled, path).effective() {
                sum = Some(sum.unwrap_or(0).saturating_add(p));
            }
        }
        path.remove(&id);
        let r = Rolled {
            entered: entered.get(&id).copied().flatten(),
            derived: sum,
        };
        rolled.insert(id, r);
        r
    }

    /// The entered and derived points of `id` (empty for an unknown ticket).
    #[must_use]
    pub fn get(&self, id: TicketId) -> Rolled {
        self.rolled.get(&id).copied().unwrap_or_default()
    }

    /// The points that count toward capacity for `id`.
    #[must_use]
    pub fn effective(&self, id: TicketId) -> Option<u32> {
        self.get(id).effective()
    }

    /// True when `id` has a pointed descendant, so its points are derived.
    #[must_use]
    pub fn is_derived(&self, id: TicketId) -> bool {
        self.get(id).derived.is_some()
    }

    /// Every ticket whose entered points differ from its derived points.
    #[must_use]
    pub fn mismatches(&self) -> Vec<(TicketId, Rolled)> {
        self.rolled
            .iter()
            .filter(|(_, r)| r.mismatched())
            .map(|(i, r)| (*i, *r))
            .collect()
    }

    /// True when an ancestor of `id` is in `members`, so the ancestor's points already cover it.
    #[must_use]
    pub fn covered_by(&self, id: TicketId, members: &BTreeSet<TicketId>) -> bool {
        let mut seen = BTreeSet::from([id]);
        let mut at = id;
        while let Some(p) = self.parent.get(&at) {
            if !seen.insert(*p) {
                return false;
            }
            if members.contains(p) && self.is_derived(*p) {
                return true;
            }
            at = *p;
        }
        false
    }
}

#[cfg(test)]
#[allow(clippy::many_single_char_names)]
mod tests {
    use super::*;
    use crate::model::{Category, Class, Priority, TicketType};

    fn s(id: TicketId, parent: Option<TicketId>, points: Option<u8>) -> Summary {
        Summary {
            id,
            handle: id.to_string(),
            title: "t".into(),
            ty: TicketType::Task,
            category: Category::Todo,
            outcome: None,
            priority: Priority::Medium,
            class: Class::Standard,
            due: None,
            points,
            parent,
            created: gob_time::Stamp::from_unix(0),
            updated: gob_time::Stamp::from_unix(0),
            blocked: false,
        }
    }

    // frob:tests Rollup.build
    #[test]
    fn nested_and_mixed_children_sum_pointed_descendants() {
        let (a, b, c, d, e) = (
            TicketId::mint(),
            TicketId::mint(),
            TicketId::mint(),
            TicketId::mint(),
            TicketId::mint(),
        );
        let all = [
            s(a, None, None),
            s(b, Some(a), None),
            s(c, Some(b), Some(2)),
            s(d, Some(b), Some(3)),
            s(e, Some(a), None),
        ];
        let r = Rollup::build(&all);
        assert_eq!(r.effective(b), Some(5));
        assert_eq!(r.effective(a), Some(5));
        assert_eq!(r.effective(e), None);
        assert!(r.is_derived(a));
        assert!(!r.is_derived(c));
    }

    // frob:tests Rollup.mismatches
    #[test]
    fn entered_points_that_differ_are_mismatches() {
        let (a, b) = (TicketId::mint(), TicketId::mint());
        let r = Rollup::build(&[s(a, None, Some(8)), s(b, Some(a), Some(3))]);
        assert_eq!(r.mismatches().len(), 1);
        assert_eq!(r.effective(a), Some(3));
        let r = Rollup::build(&[s(a, None, Some(3)), s(b, Some(a), Some(3))]);
        assert!(r.mismatches().is_empty());
    }

    // frob:tests Rollup.build
    #[test]
    fn parent_cycles_terminate() {
        let (a, b) = (TicketId::mint(), TicketId::mint());
        let r = Rollup::build(&[s(a, Some(b), Some(2)), s(b, Some(a), Some(3))]);
        assert!(r.effective(a).is_some());
        assert!(!r.covered_by(a, &BTreeSet::new()));
    }

    // frob:tests Rollup.covered_by
    #[test]
    fn members_under_a_derived_member_are_covered() {
        let (a, b) = (TicketId::mint(), TicketId::mint());
        let r = Rollup::build(&[s(a, None, None), s(b, Some(a), Some(2))]);
        let members = BTreeSet::from([a, b]);
        assert!(r.covered_by(b, &members));
        assert!(!r.covered_by(a, &members));
    }

    // frob:tests crates/frob-ledger/src/doctor.rs::points_mismatch_issues
    #[test]
    fn a_story_whose_entered_points_differ_from_its_children_is_reported() {
        let (a, b, c) = (TicketId::mint(), TicketId::mint(), TicketId::mint());
        let all = [
            s(a, None, Some(5)),
            s(b, Some(a), Some(2)),
            s(c, Some(a), Some(2)),
        ];
        let issues = crate::doctor::points_mismatch_issues(&all);
        assert_eq!(issues.len(), 1);
        assert_eq!(issues[0].code, "E-DOCTOR-POINTS-ROLLUP");
        assert_eq!(issues[0].ticket, a);
        assert!(issues[0].message.contains("entered 5") && issues[0].message.contains("derive 4"));
        let agree = [
            s(a, None, Some(4)),
            s(b, Some(a), Some(2)),
            s(c, Some(a), Some(2)),
        ];
        assert!(crate::doctor::points_mismatch_issues(&agree).is_empty());
    }
}
