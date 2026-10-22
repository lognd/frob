//! Derived points as `cycle assign` sees them: a parent counts its children's rollup once, leaves only.
//!
//! The CLI reads every ticket's [`Rollup`] once and asks here what each member and
//! the ticket being assigned count for, so a parent and its children are never
//! committed twice (pm-enforcement.md section 4).
// frob:ticket 01M4FDAKV07ZFX861ZHJKMRAQ6

use std::collections::BTreeSet;

use frob_ledger::TicketId;
use frob_ledger::model::TicketType;
use frob_ledger::rollup::Rollup;

use crate::cycle::assign::TicketFacts;

/// The `(type, points)` of each `(id, type)` member, as the capacity check counts them.
///
/// A member's points are its effective (derived else entered) points; a member whose
/// ancestor is also a member, or is being `adding`-ed, counts 0 because the ancestor's
/// derived points already include it.
#[must_use]
pub fn member_points(
    rollup: &Rollup,
    members: &[(TicketId, TicketType)],
    adding: Option<TicketId>,
) -> Vec<(TicketType, u32)> {
    let set: BTreeSet<TicketId> = members.iter().map(|(i, _)| *i).chain(adding).collect();
    members
        .iter()
        .map(|(id, ty)| {
            let pts = if rollup.covered_by(*id, &set) {
                tracing::debug!(ticket = %id, "member covered by a member ancestor; counted 0");
                0
            } else {
                rollup.effective(*id).unwrap_or(0)
            };
            (*ty, pts)
        })
        .collect()
}

/// `facts` with its points set to what assigning it commits: derived else entered, 0 when a member ancestor covers it.
#[must_use]
pub fn assign_facts(
    rollup: &Rollup,
    mut facts: TicketFacts,
    members: &BTreeSet<TicketId>,
) -> TicketFacts {
    facts.points = if rollup.covered_by(facts.id, members) {
        tracing::debug!(ticket = %facts.handle, "ticket covered by a member ancestor; counted 0");
        rollup.effective(facts.id).map(|_| 0)
    } else {
        rollup.effective(facts.id)
    };
    facts
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cycle::assign::plan_assign;
    use crate::cycle::velocity::Capacity;
    use crate::model::{Cycle, Day, ObjectId, State};
    use frob_ledger::index::Summary;
    use frob_ledger::model::{Category, Class, Priority, Stamp};

    fn summary(id: TicketId, parent: Option<TicketId>, points: Option<u8>) -> Summary {
        Summary {
            id,
            handle: format!("~{id}"),
            title: "t".to_owned(),
            ty: TicketType::Task,
            category: Category::Todo,
            outcome: None,
            priority: Priority::Medium,
            class: Class::Standard,
            due: None,
            points,
            parent,
            created: Stamp::from_unix(0),
            updated: Stamp::from_unix(0),
            blocked: false,
        }
    }

    fn cycle(tickets: Vec<TicketId>) -> Cycle {
        let day: Day = "2026-01-05".parse().expect("day");
        Cycle {
            id: ObjectId::mint(),
            start: day,
            end: "2026-01-19".parse().expect("day"),
            ended: None,
            goal: "g".to_owned(),
            capacity_points: None,
            state: State::Open,
            tickets,
            created: Stamp::from_unix(0),
            updated: Stamp::from_unix(0),
            ordinal: 1,
        }
    }

    fn facts(id: TicketId, ty: TicketType) -> TicketFacts {
        TicketFacts {
            id,
            handle: "~S".to_owned(),
            ty,
            points: None,
        }
    }

    // frob:tests assign_facts
    // frob:tests member_points
    #[test]
    fn story_with_pointed_subtasks_assigns_with_derived_points_counted_once() {
        let (story, a, b, c) = (
            TicketId::mint(),
            TicketId::mint(),
            TicketId::mint(),
            TicketId::mint(),
        );
        let rollup = Rollup::build(&[
            summary(story, None, None),
            summary(a, Some(story), Some(2)),
            summary(b, Some(story), Some(2)),
            summary(c, Some(story), Some(3)),
        ]);
        let target = cycle(Vec::new());
        let f = assign_facts(&rollup, facts(story, TicketType::Story), &BTreeSet::new());
        assert_eq!(f.points, Some(7));
        assert!(rollup.is_derived(story));
        let plan = plan_assign(&target, &[], &f, &[], Capacity::Set(100), false).expect("accepted");
        let crate::cycle::assign::AssignPlan::Add { committed, .. } = plan else {
            panic!("expected an add")
        };
        assert_eq!(committed, 7);
        // Subtask `a` already a member: the story's 7 replaces it, never adds to it.
        let members = member_points(&rollup, &[(a, TicketType::Task)], Some(story));
        assert_eq!(members, vec![(TicketType::Task, 0)]);
        let plan =
            plan_assign(&target, &[], &f, &members, Capacity::Set(100), false).expect("accepted");
        let crate::cycle::assign::AssignPlan::Add { committed, .. } = plan else {
            panic!("expected an add")
        };
        assert_eq!(committed, 7);
    }

    // frob:tests assign_facts
    #[test]
    fn a_child_under_a_member_parent_counts_zero() {
        let (p, k) = (TicketId::mint(), TicketId::mint());
        let rollup = Rollup::build(&[summary(p, None, None), summary(k, Some(p), Some(5))]);
        let f = assign_facts(&rollup, facts(k, TicketType::Task), &BTreeSet::from([p]));
        assert_eq!(f.points, Some(0));
    }
}
