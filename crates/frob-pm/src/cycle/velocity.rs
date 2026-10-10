//! Velocity and capacity: points delivered per closed cycle, and the commitment limit derived from them.
//!
//! Velocity of a closed cycle is the points done among the tickets committed
//! to it, by the same definition `cycle close` records as its ratio (see
//! [`delivery`]); work done in the window but never assigned does not count,
//! and carried work counts only where it finished. [`delivered`] still
//! measures the whole window for the unplanned surplus. Capacity is
//! `rolling_mean - k * stddev` over the last closed cycles, or the cycle's own
//! `capacity_points`, and is not enforced until `[pm] min_history` cycles have
//! closed. Pure functions over [`DoneFact`]s, so `cycle velocity` reuses them.
// frob:ticket 01M4069SHBAEWRX9WWCSS2FEHN
// frob:ticket 01M4069SYRHMYXCFAZH0AN408B

use std::collections::BTreeMap;

use frob_ledger::Ledger;
use frob_ledger::event::EventBody;
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Outcome, TicketType};

use crate::cycle::lifecycle::{MemberFacts, commitment};
use crate::error::Result;
use crate::model::{Cycle, Day, ObjectId, State};

/// Closed cycles the rolling mean looks back over (at least `[pm] min_history`).
pub const ROLLING_CYCLES: usize = 6;

/// True for the ticket types whose points count as velocity and as committed points.
pub const fn counts(ty: TicketType) -> bool {
    matches!(
        ty,
        TicketType::Story | TicketType::Task | TicketType::Bug | TicketType::Chore
    )
}

/// A ticket that finished its work: when, how big and of what type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DoneFact {
    /// The ticket's type.
    pub ty: TicketType,
    /// Story points, 0 when unestimated.
    pub points: u32,
    /// The UTC day of the latest transition to `done`.
    pub done_on: Day,
}

/// Every ticket that reached `done` with a completing outcome (fixed or done), read from ticket events.
///
/// # Errors
///
/// Store failures reading the index or a ticket's events.
pub fn done_facts(ledger: &Ledger) -> Result<Vec<DoneFact>> {
    let done = ledger.list(&ListFilter {
        category: Some(Category::Done),
        ..ListFilter::default()
    })?;
    let counted: Vec<_> = done
        .into_iter()
        .filter(|s| matches!(s.outcome, Some(Outcome::Fixed | Outcome::Done)))
        .collect();
    // One sync and one tree walk for every counted ticket's events, not one per ticket.
    let ids: std::collections::BTreeSet<_> = counted.iter().map(|s| s.id).collect();
    let mut events = ledger.events_many(&ids)?;
    let mut out = Vec::new();
    for s in counted {
        let at = events
            .remove(&s.id)
            .unwrap_or_default()
            .iter()
            .rev()
            .find(|e| matches!(&e.body, EventBody::Transition(t) if t.to == Category::Done))
            .map(|e| e.at);
        let Some(at) = at else {
            tracing::warn!(ticket = %s.id, "done ticket has no transition to done; skipped for velocity");
            continue;
        };
        out.push(DoneFact {
            ty: s.ty,
            points: u32::from(s.points.unwrap_or(0)),
            done_on: Day::from_unix(at.unix()),
        });
    }
    tracing::debug!(count = out.len(), "done facts gathered");
    Ok(out)
}

/// Points of every counted ticket done inside the window of `cycle` (planned end, or the close day when closed early), planned or not.
///
/// Velocity does not use this; it exists so the surplus over a cycle's own delivery can be shown as unplanned work.
pub fn delivered(cycle: &Cycle, facts: &[DoneFact]) -> u32 {
    facts
        .iter()
        .filter(|f| counts(f.ty) && cycle.start <= f.done_on && f.done_on <= cycle.effective_end())
        .map(|f| f.points)
        .sum()
}

/// Points of the velocity-counting tickets among `tickets` as `(type, points)` pairs.
pub fn committed(tickets: &[(TicketType, u32)]) -> u32 {
    tickets
        .iter()
        .filter(|(ty, _)| counts(*ty))
        .map(|(_, p)| p)
        .sum()
}

/// Delivered points of the most recent closed cycles and their statistics.
#[derive(Debug, Clone, PartialEq)]
pub struct Velocity {
    /// `(alias, points)` of each cycle used, oldest first.
    pub per_cycle: Vec<(String, u32)>,
    /// Mean points per cycle; 0 with no cycles.
    pub mean: f64,
    /// Population standard deviation; 0 with fewer than two cycles.
    pub stddev: f64,
}

/// The last `last` closed cycles of `cycles` by start, oldest first.
pub fn recent_closed(cycles: &[Cycle], last: usize) -> Vec<&Cycle> {
    let mut closed: Vec<&Cycle> = cycles.iter().filter(|c| c.state == State::Closed).collect();
    closed.sort_by_key(|c| (c.start, c.end));
    let skip = closed.len().saturating_sub(last);
    closed.split_off(skip)
}

/// What a closed cycle delivered, by the close-time definition: points done among the tickets committed to it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Delivery {
    /// Points committed when the cycle closed, when known (absent for cycles closed before ratios were recorded).
    pub committed: Option<u32>,
    /// Points of committed tickets that finished.
    pub done: u32,
}

/// The delivery of a closed cycle: the recorded `(committed, done)` ratio event when there is one, else the finished members' points.
///
/// Both go through [`commitment`], the definition `cycle close` records; carried tickets left
/// the cycle at close, so work carried over counts only in the cycle that completes it.
pub fn delivery(recorded: Option<(u32, u32)>, members: &[MemberFacts]) -> Delivery {
    match recorded {
        Some((committed, done)) => Delivery {
            committed: Some(committed),
            done,
        },
        None => Delivery {
            committed: None,
            done: commitment(members).1,
        },
    }
}

/// Velocity over the last `last` closed cycles of `cycles` (by start), from each cycle's done points in `done`.
pub fn velocity(cycles: &[Cycle], done: &BTreeMap<ObjectId, u32>, last: usize) -> Velocity {
    let per_cycle: Vec<(String, u32)> = recent_closed(cycles, last)
        .iter()
        .map(|c| (c.alias(), done.get(&c.id).copied().unwrap_or(0)))
        .collect();
    let n = per_cycle.len();
    let count = f64::from(u32::try_from(n).unwrap_or(u32::MAX));
    let (mean, stddev) = if n == 0 {
        (0.0, 0.0)
    } else {
        let mean = per_cycle.iter().map(|(_, p)| f64::from(*p)).sum::<f64>() / count;
        let var = per_cycle
            .iter()
            .map(|(_, p)| (f64::from(*p) - mean).powi(2))
            .sum::<f64>()
            / count;
        (mean, var.sqrt())
    };
    Velocity {
        per_cycle,
        mean,
        stddev,
    }
}

/// The commitment limit of a cycle and where it came from.
#[derive(Debug, Clone, PartialEq)]
pub enum Capacity {
    /// `capacity_points` was set on the cycle.
    Set(u32),
    /// Too little history: nothing is enforced yet.
    Unenforced {
        /// Closed cycles that exist.
        have: u32,
        /// `[pm] min_history`.
        need: u32,
    },
    /// `floor(max(0, mean - k * stddev))` over the recent closed cycles.
    Computed {
        /// The limit in points.
        limit: u32,
        /// Rolling mean.
        mean: f64,
        /// Standard deviation.
        stddev: f64,
        /// The safety factor used.
        k: f64,
        /// Cycles in the window.
        cycles: usize,
    },
}

impl Capacity {
    /// The enforced limit, `None` when unenforced.
    pub const fn limit(&self) -> Option<u32> {
        match self {
            Self::Set(l) | Self::Computed { limit: l, .. } => Some(*l),
            Self::Unenforced { .. } => None,
        }
    }

    /// A one-line statement of the capacity for output and refusals.
    pub fn describe(&self) -> String {
        match self {
            Self::Set(l) => format!("capacity {l} points (capacity_points set on the cycle)"),
            Self::Unenforced { have, need } => {
                format!("capacity not enforced yet: {have} of {need} cycles of history")
            }
            Self::Computed {
                limit,
                mean,
                stddev,
                k,
                cycles,
            } => format!(
                "capacity {limit} points (mean {mean:.1} - {k} x stddev {stddev:.1} over the last {cycles} closed cycles)"
            ),
        }
    }
}

/// The capacity that applies to `cycle` given every cycle, the done facts and the `[pm]` knobs.
pub fn capacity(
    cycle: &Cycle,
    cycles: &[Cycle],
    done: &BTreeMap<ObjectId, u32>,
    min_history: u32,
    k: f64,
) -> Capacity {
    if let Some(p) = cycle.capacity_points {
        return Capacity::Set(p);
    }
    history_capacity(cycles, done, min_history, k)
}

/// The capacity derived from closed-cycle history alone: what a cycle without `capacity_points` gets.
///
/// This is the single computation behind `cycle assign` and `cycle velocity`.
pub fn history_capacity(
    cycles: &[Cycle],
    done: &BTreeMap<ObjectId, u32>,
    min_history: u32,
    k: f64,
) -> Capacity {
    let have = cycles.iter().filter(|c| c.state == State::Closed).count();
    let have_u32 = u32::try_from(have).unwrap_or(u32::MAX);
    if have_u32 < min_history {
        return Capacity::Unenforced {
            have: have_u32,
            need: min_history,
        };
    }
    let v = velocity(cycles, done, ROLLING_CYCLES.max(min_history as usize));
    let raw = (v.mean - k * v.stddev).max(0.0).floor();
    // Truncation is the intent: a non-negative floor of a mean of u32 values.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let limit = raw as u32;
    Capacity::Computed {
        limit,
        mean: v.mean,
        stddev: v.stddev,
        k,
        cycles: v.per_cycle.len(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cycle::lifecycle::MemberStatus;
    use crate::model::ObjectId;
    use frob_ledger::model::Stamp;

    fn day(s: &str) -> Day {
        s.parse().expect("day")
    }

    fn cycle(start: &str, end: &str, state: State, cap: Option<u32>) -> Cycle {
        Cycle {
            id: ObjectId::mint(),
            start: day(start),
            end: day(end),
            ended: None,
            goal: "g".to_owned(),
            capacity_points: cap,
            state,
            tickets: Vec::new(),
            created: Stamp::from_unix(1_800_000_000),
            updated: Stamp::from_unix(1_800_000_000),
            ordinal: 1,
        }
    }

    fn fact(ty: TicketType, points: u32, on: &str) -> DoneFact {
        DoneFact {
            ty,
            points,
            done_on: day(on),
        }
    }

    #[test]
    fn epics_and_out_of_window_work_never_count() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::delivered
        let c = cycle("2026-10-05", "2026-10-11", State::Closed, None);
        let facts = [
            fact(TicketType::Task, 3, "2026-10-05"),
            fact(TicketType::Story, 5, "2026-10-11"),
            fact(TicketType::Epic, 8, "2026-10-07"),
            fact(TicketType::Bug, 2, "2026-10-12"),
        ];
        assert_eq!(delivered(&c, &facts), 8);
        assert_eq!(
            committed(&[(TicketType::Epic, 8), (TicketType::Chore, 2)]),
            2
        );
    }

    /// A done map giving each cycle in order the matching points.
    fn done_map(cycles: &[Cycle], points: &[u32]) -> BTreeMap<ObjectId, u32> {
        cycles
            .iter()
            .map(|c| c.id)
            .zip(points.iter().copied())
            .collect()
    }

    #[test]
    fn capacity_is_set_unenforced_or_mean_minus_k_stddev() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::capacity
        let open = cycle("2026-11-02", "2026-11-08", State::Planned, None);
        let set = cycle("2026-11-02", "2026-11-08", State::Planned, Some(7));
        let closed = [
            cycle("2026-10-05", "2026-10-11", State::Closed, None),
            cycle("2026-10-12", "2026-10-18", State::Closed, None),
            cycle("2026-10-19", "2026-10-25", State::Closed, None),
        ];
        let mut all = closed.to_vec();
        all.push(open.clone());
        let done = done_map(&closed, &[8, 12, 10]);
        assert_eq!(capacity(&set, &all, &done, 3, 0.5), Capacity::Set(7));
        assert_eq!(
            capacity(&open, &all[..2], &done, 3, 0.5),
            Capacity::Unenforced { have: 2, need: 3 }
        );
        // mean 10, population stddev sqrt(8/3) = 1.63, 10 - 0.82 = 9.18 -> 9.
        let c = capacity(&open, &all, &done, 3, 0.5);
        assert_eq!(c.limit(), Some(9));
        assert!(c.describe().contains("capacity 9 points"));
    }

    #[test]
    fn an_early_close_truncates_the_window() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::delivered
        let mut c = cycle("2026-10-05", "2026-10-11", State::Closed, None);
        c.ended = Some(day("2026-10-06"));
        let facts = [
            fact(TicketType::Task, 3, "2026-10-06"),
            fact(TicketType::Task, 5, "2026-10-07"),
        ];
        assert_eq!(delivered(&c, &facts), 3);
        let next = cycle("2026-10-07", "2026-10-08", State::Closed, None);
        assert_eq!(delivered(&next, &facts), 5);
    }

    fn member(points: u32, status: MemberStatus) -> MemberFacts {
        MemberFacts {
            id: frob_ledger::TicketId::mint(),
            handle: "~X".to_owned(),
            status,
            live_lease: false,
            points,
        }
    }

    #[test]
    fn velocity_over_three_closed_cycles_is_the_hand_computed_mean_and_stddev() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::velocity
        let cycles = [
            cycle("2026-10-05", "2026-10-11", State::Closed, None),
            cycle("2026-10-12", "2026-10-18", State::Closed, None),
            cycle("2026-10-19", "2026-10-25", State::Closed, None),
            cycle("2026-10-26", "2026-11-01", State::Planned, None),
        ];
        let done = done_map(&cycles, &[8, 12, 10, 9]);
        let v = velocity(&cycles, &done, 6);
        let points: Vec<u32> = v.per_cycle.iter().map(|(_, p)| *p).collect();
        assert_eq!(points, [8, 12, 10]);
        // mean 10; population variance (4 + 4 + 0) / 3.
        assert!((v.mean - 10.0).abs() < 1e-9);
        assert!((v.stddev - (8.0_f64 / 3.0).sqrt()).abs() < 1e-9);
        let last_two = velocity(&cycles, &done, 2);
        assert_eq!(last_two.per_cycle.len(), 2);
        assert!((last_two.mean - 11.0).abs() < 1e-9);
        assert!((last_two.stddev - 1.0).abs() < 1e-9);
    }

    #[test]
    fn delivery_agrees_with_the_close_definition_and_prefers_the_recorded_ratio() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::delivery
        use crate::cycle::lifecycle::commitment;
        let members = [
            member(5, MemberStatus::Finished),
            member(3, MemberStatus::Finished),
            member(2, MemberStatus::Dropped),
        ];
        let (committed, done) = commitment(&members);
        assert_eq!((committed, done), (10, 8));
        // Legacy close without a ratio event: the finished members' points, no commitment.
        assert_eq!(
            delivery(None, &members),
            Delivery {
                committed: None,
                done: 8
            }
        );
        // A recorded ratio wins, including points that carried out of the cycle.
        assert_eq!(
            delivery(Some((13, 8)), &members),
            Delivery {
                committed: Some(13),
                done: 8
            }
        );
    }

    #[test]
    fn carry_over_counts_only_in_the_completing_cycle() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::delivery
        // A carried ticket left A at close (A recorded 5 of 10 done) and finished in B.
        let a = delivery(Some((10, 5)), &[member(5, MemberStatus::Finished)]);
        let b = delivery(None, &[member(5, MemberStatus::Finished)]);
        assert_eq!((a.done, b.done), (5, 5));
        assert_eq!(a.done + b.done, 10, "the carried 5 is not in A's done");
    }

    #[test]
    fn history_capacity_matches_capacity_for_a_cycle_without_a_set_limit() {
        // frob:tests crates/frob-pm/src/cycle/velocity.rs::history_capacity
        let open = cycle("2026-11-02", "2026-11-08", State::Planned, None);
        let mut all = vec![
            cycle("2026-10-05", "2026-10-11", State::Closed, None),
            cycle("2026-10-12", "2026-10-18", State::Closed, None),
        ];
        all.push(cycle("2026-10-19", "2026-10-25", State::Closed, None));
        all.push(open.clone());
        let done = done_map(&all, &[8, 4, 6]);
        assert_eq!(
            history_capacity(&all[..2], &done, 3, 0.5),
            capacity(&open, &all[..2], &done, 3, 0.5)
        );
        assert_eq!(
            history_capacity(&all, &done, 3, 0.5),
            capacity(&open, &all, &done, 3, 0.5)
        );
    }
}
