//! Velocity and capacity: points delivered per closed cycle, and the commitment limit derived from them.
//!
//! Velocity counts the points of story, task, bug and chore tickets that
//! reached `done` with a completing outcome inside a cycle's window (epics and
//! milestones never count; pm-enforcement.md section 4). Capacity is
//! `rolling_mean - k * stddev` over the last closed cycles, or the cycle's own
//! `capacity_points`, and is not enforced until `[pm] min_history` cycles have
//! closed. Pure functions over [`DoneFact`]s, so `cycle velocity` reuses them.
// frob:ticket 01M4069SHBAEWRX9WWCSS2FEHN

use frob_ledger::Ledger;
use frob_ledger::event::EventBody;
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Outcome, TicketType};

use crate::error::Result;
use crate::model::{Cycle, Day, State};

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
    let mut out = Vec::new();
    for s in done {
        if !matches!(s.outcome, Some(Outcome::Fixed | Outcome::Done)) {
            continue;
        }
        let at = ledger
            .events(s.id)?
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

/// Points delivered inside the window of `cycle`.
pub fn delivered(cycle: &Cycle, facts: &[DoneFact]) -> u32 {
    facts
        .iter()
        .filter(|f| counts(f.ty) && cycle.start <= f.done_on && f.done_on <= cycle.end)
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

/// Velocity over the last `last` closed cycles of `cycles` (by start), from `facts`.
pub fn velocity(cycles: &[Cycle], facts: &[DoneFact], last: usize) -> Velocity {
    let mut closed: Vec<&Cycle> = cycles.iter().filter(|c| c.state == State::Closed).collect();
    closed.sort_by_key(|c| (c.start, c.end));
    let skip = closed.len().saturating_sub(last);
    let per_cycle: Vec<(String, u32)> = closed[skip..]
        .iter()
        .map(|c| (c.alias(), delivered(c, facts)))
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
    facts: &[DoneFact],
    min_history: u32,
    k: f64,
) -> Capacity {
    if let Some(p) = cycle.capacity_points {
        return Capacity::Set(p);
    }
    let have = cycles.iter().filter(|c| c.state == State::Closed).count();
    let have_u32 = u32::try_from(have).unwrap_or(u32::MAX);
    if have_u32 < min_history {
        return Capacity::Unenforced {
            have: have_u32,
            need: min_history,
        };
    }
    let v = velocity(cycles, facts, ROLLING_CYCLES.max(min_history as usize));
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
            goal: "g".to_owned(),
            capacity_points: cap,
            state,
            tickets: Vec::new(),
            created: Stamp::now(),
            updated: Stamp::now(),
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
        let facts = [
            fact(TicketType::Task, 8, "2026-10-06"),
            fact(TicketType::Task, 12, "2026-10-13"),
            fact(TicketType::Task, 10, "2026-10-20"),
        ];
        assert_eq!(capacity(&set, &all, &facts, 3, 0.5), Capacity::Set(7));
        assert_eq!(
            capacity(&open, &all[..2], &facts, 3, 0.5),
            Capacity::Unenforced { have: 2, need: 3 }
        );
        // mean 10, population stddev sqrt(8/3) = 1.63, 10 - 0.82 = 9.18 -> 9.
        let c = capacity(&open, &all, &facts, 3, 0.5);
        assert_eq!(c.limit(), Some(9));
        assert!(c.describe().contains("capacity 9 points"));
    }
}
