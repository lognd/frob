//! `cycle assign` as pure rules: default cycle, eligibility, the move rule and the capacity check.
//!
//! A ticket belongs to at most one open or planned cycle: assigning it to another
//! moves it (a `remove` on the old cycle, an `add` on the new one). Epics never
//! count toward velocity, so they are refused, and a ticket needs points so
//! capacity can be measured. Past capacity the assignment is refused unless the
//! caller over-commits with a reason (pm-enforcement.md section 4).
// frob:ticket 01M4069SHBAEWRX9WWCSS2FEHN

use frob_ledger::TicketId;
use frob_ledger::model::TicketType;

use crate::cycle::velocity::{Capacity, committed, counts};
use crate::model::{Cycle, Day, ObjectId, State};

/// An assignment that cannot be honoured, each with the fix the caller needs.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum AssignError {
    /// No open cycle holds today and none is planned.
    #[error("there is no open cycle containing {today} and no planned cycle to default to")]
    NoDefaultCycle {
        /// The day the default was sought for.
        today: Day,
    },
    /// The target cycle is closed.
    #[error("cycle {alias} is closed and its membership cannot change")]
    Closed {
        /// Alias of the closed cycle.
        alias: String,
    },
    /// The ticket is an epic (or another type that never counts toward velocity).
    #[error("{handle} is {} and cannot be assigned to a cycle: epics never count toward velocity", article(*ty))]
    NotAssignable {
        /// Handle of the ticket.
        handle: String,
        /// Its type.
        ty: TicketType,
    },
    /// The ticket has no points, so capacity cannot be measured.
    #[error("{handle} has no story points, and a cycle needs them to measure capacity")]
    NoPoints {
        /// Handle of the ticket.
        handle: String,
    },
    /// The assignment would push committed points past the limit.
    #[error(
        "assigning {handle} would commit {committed} points to cycle {alias}, over its {limit}-point limit ({why})"
    )]
    OverCapacity {
        /// Handle of the ticket.
        handle: String,
        /// Alias of the target cycle.
        alias: String,
        /// Committed points with the ticket.
        committed: u32,
        /// The enforced limit.
        limit: u32,
        /// Where the limit came from.
        why: String,
    },
}

fn article(ty: TicketType) -> String {
    format!("an {ty}")
}

/// What `cycle assign` needs to know about the ticket.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TicketFacts {
    /// The ticket.
    pub id: TicketId,
    /// Its handle, for messages.
    pub handle: String,
    /// Its type.
    pub ty: TicketType,
    /// Story points when estimated.
    pub points: Option<u32>,
}

/// What assigning will do.
#[derive(Debug, Clone, PartialEq)]
pub enum AssignPlan {
    /// The ticket is already a member: nothing to write.
    Already,
    /// Add the ticket, possibly moving it out of another cycle.
    Add {
        /// The open or planned cycle the ticket leaves first.
        moved_from: Option<(ObjectId, String)>,
        /// Committed points of the target cycle after the assignment.
        committed: u32,
        /// The capacity that applied.
        capacity: Capacity,
        /// True when the limit is exceeded and the caller over-committed: record the reason.
        over_commit: bool,
    },
}

/// The cycle assign defaults to: the open one containing `today`, else the next planned one by start.
///
/// # Errors
///
/// [`AssignError::NoDefaultCycle`] when neither exists.
pub fn default_cycle(all: &[Cycle], today: Day) -> Result<&Cycle, AssignError> {
    let open = || all.iter().filter(|c| c.state != State::Closed);
    open()
        .find(|c| c.start <= today && today <= c.effective_end())
        .or_else(|| open().filter(|c| c.start > today).min_by_key(|c| c.start))
        .ok_or(AssignError::NoDefaultCycle { today })
}

/// Plan `cycle assign`: idempotency, eligibility, the move and the capacity check.
///
/// `members` are the `(type, points)` of the target's current members; `all` is every cycle.
///
/// # Errors
///
/// [`AssignError::Closed`], [`AssignError::NotAssignable`], [`AssignError::NoPoints`] or
/// [`AssignError::OverCapacity`] (the last only without `over_commit`).
pub fn plan_assign(
    target: &Cycle,
    all: &[Cycle],
    ticket: &TicketFacts,
    members: &[(TicketType, u32)],
    capacity: Capacity,
    over_commit: bool,
) -> Result<AssignPlan, AssignError> {
    if target.tickets.contains(&ticket.id) {
        tracing::debug!(cycle = %target.alias(), ticket = %ticket.handle, "assign repeats a membership");
        return Ok(AssignPlan::Already);
    }
    if target.state == State::Closed {
        return Err(AssignError::Closed {
            alias: target.alias(),
        });
    }
    if ticket.ty == TicketType::Epic {
        return Err(AssignError::NotAssignable {
            handle: ticket.handle.clone(),
            ty: ticket.ty,
        });
    }
    let Some(points) = ticket.points else {
        return Err(AssignError::NoPoints {
            handle: ticket.handle.clone(),
        });
    };
    let total = committed(members) + if counts(ticket.ty) { points } else { 0 };
    let exceeds = capacity.limit().is_some_and(|l| total > l);
    if exceeds && !over_commit {
        tracing::info!(cycle = %target.alias(), ticket = %ticket.handle, total, "assign refused: over capacity");
        return Err(AssignError::OverCapacity {
            handle: ticket.handle.clone(),
            alias: target.alias(),
            committed: total,
            limit: capacity.limit().unwrap_or(0),
            why: capacity.describe(),
        });
    }
    let moved_from = all
        .iter()
        .find(|c| c.id != target.id && c.state != State::Closed && c.tickets.contains(&ticket.id))
        .map(|c| (c.id, c.alias()));
    Ok(AssignPlan::Add {
        moved_from,
        committed: total,
        capacity,
        over_commit: exceeds,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_ledger::model::Stamp;

    fn day(s: &str) -> Day {
        s.parse().expect("day")
    }

    fn cycle(start: &str, end: &str, state: State) -> Cycle {
        Cycle {
            id: ObjectId::mint(),
            start: day(start),
            end: day(end),
            ended: None,
            goal: "g".to_owned(),
            capacity_points: None,
            state,
            tickets: Vec::new(),
            created: Stamp::now(),
            updated: Stamp::now(),
        }
    }

    fn ticket(ty: TicketType, points: Option<u32>) -> TicketFacts {
        TicketFacts {
            id: TicketId::mint(),
            handle: "~T".to_owned(),
            ty,
            points,
        }
    }

    #[test]
    fn default_prefers_the_open_cycle_holding_today_then_the_next_planned() {
        // frob:tests crates/frob-pm/src/cycle/assign.rs::default_cycle
        let active = cycle("2026-10-05", "2026-10-11", State::Active);
        let next = cycle("2026-10-12", "2026-10-18", State::Planned);
        let later = cycle("2026-10-19", "2026-10-25", State::Planned);
        let all = [later, next.clone(), active.clone()];
        assert_eq!(default_cycle(&all, day("2026-10-07")), Ok(&active));
        assert_eq!(default_cycle(&all, day("2026-10-11")), Ok(&active));
        assert_eq!(default_cycle(&all, day("2026-10-02")), Ok(&active));
        assert_eq!(default_cycle(&all[..2], day("2026-10-13")), Ok(&next));
        assert!(matches!(
            default_cycle(
                &[cycle("2026-10-05", "2026-10-11", State::Closed)],
                day("2026-10-07")
            ),
            Err(AssignError::NoDefaultCycle { .. })
        ));
    }

    #[test]
    fn eligibility_and_capacity_decide_the_plan() {
        // frob:tests crates/frob-pm/src/cycle/assign.rs::plan_assign
        let c = cycle("2026-10-05", "2026-10-11", State::Planned);
        let none = Capacity::Unenforced { have: 0, need: 3 };
        let t = ticket(TicketType::Task, Some(3));
        assert!(matches!(
            plan_assign(
                &c,
                &[],
                &ticket(TicketType::Epic, Some(3)),
                &[],
                none.clone(),
                false
            ),
            Err(AssignError::NotAssignable { .. })
        ));
        assert!(matches!(
            plan_assign(
                &c,
                &[],
                &ticket(TicketType::Task, None),
                &[],
                none.clone(),
                false
            ),
            Err(AssignError::NoPoints { .. })
        ));
        let limit = Capacity::Set(5);
        let members = [(TicketType::Task, 4)];
        assert!(matches!(
            plan_assign(&c, &[], &t, &members, limit.clone(), false),
            Err(AssignError::OverCapacity {
                committed: 7,
                limit: 5,
                ..
            })
        ));
        let over = plan_assign(&c, &[], &t, &members, limit.clone(), true).expect("over");
        assert!(matches!(
            over,
            AssignPlan::Add {
                over_commit: true,
                committed: 7,
                ..
            }
        ));
        let fits = plan_assign(&c, &[], &t, &[], limit, false).expect("fits");
        assert!(matches!(
            fits,
            AssignPlan::Add {
                over_commit: false,
                committed: 3,
                ..
            }
        ));
    }

    #[test]
    fn a_member_elsewhere_moves_and_a_repeat_is_already() {
        // frob:tests crates/frob-pm/src/cycle/assign.rs::plan_assign
        let t = ticket(TicketType::Task, Some(2));
        let mut old = cycle("2026-10-05", "2026-10-11", State::Active);
        old.tickets.push(t.id);
        let new = cycle("2026-10-12", "2026-10-18", State::Planned);
        let none = Capacity::Unenforced { have: 0, need: 3 };
        let all = [old.clone(), new.clone()];
        let p = plan_assign(&new, &all, &t, &[], none.clone(), false).expect("plan");
        assert!(matches!(p, AssignPlan::Add { moved_from: Some((id, _)), .. } if id == old.id));
        assert_eq!(
            plan_assign(&old, &all, &t, &[], none, false),
            Ok(AssignPlan::Already)
        );
        let closed = cycle("2026-09-28", "2026-10-04", State::Closed);
        assert!(matches!(
            plan_assign(&closed, &[], &t, &[], Capacity::Set(9), false),
            Err(AssignError::Closed { .. })
        ));
    }
}
