//! The cycle lifecycle as pure rules: `new` window and idempotency, `close` planning.
// frob:ticket 01M4069RPPQE1ES1914K6V6Y0D

use frob_ledger::TicketId;

use crate::milestone::distance;
use crate::model::{Cycle, Day, ObjectId, State};

/// A cycle request that cannot be honoured, each with the fix the caller needs.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CycleError {
    /// The window ends before it starts, or the derived end is out of range.
    #[error("cycle window {start}..{end} is invalid: {reason}")]
    BadWindow {
        /// First day as given.
        start: String,
        /// Last day as given or derived.
        end: String,
        /// What is wrong with it.
        reason: String,
    },
    /// The window shares days with a cycle that is not closed.
    #[error("cycle {start}..{end} overlaps open cycle {with} ({state})")]
    Overlap {
        /// First day of the requested window.
        start: Day,
        /// Last day of the requested window.
        end: Day,
        /// Alias of the cycle in the way.
        with: String,
        /// Its state.
        state: State,
        /// The first free day after it.
        next_free: Day,
    },
    /// A cycle with this window exists with different fields.
    #[error("cycle `{alias}` already exists with different {}", fields.join(", "))]
    Conflict {
        /// The shared alias.
        alias: String,
        /// Names of the fields that differ (`goal`, `capacity_points`).
        fields: Vec<&'static str>,
    },
    /// No cycle matches the reference.
    #[error("no cycle matches `{input}`")]
    Unknown {
        /// The reference as given.
        input: String,
        /// Existing aliases closest to the input, best first.
        suggestions: Vec<String>,
    },
    /// Members are in progress under a live lease; the cycle cannot close.
    #[error("cycle {alias} cannot close: {} in progress with a live lease", handles.join(", "))]
    LiveLease {
        /// The cycle's alias.
        alias: String,
        /// Handles of the blocking tickets.
        handles: Vec<String>,
    },
    /// Incomplete members need a later cycle and none exists.
    #[error("cycle {alias} has {carrying} incomplete ticket(s) to carry and no later open cycle")]
    NoNextCycle {
        /// The closing cycle's alias.
        alias: String,
        /// How many tickets need a home.
        carrying: usize,
        /// The first free day after the closing cycle, for the suggested `cycle new`.
        suggest_start: Day,
    },
    /// The `--carry-to` cycle cannot take the work.
    #[error("cannot carry to cycle {target}: {reason}")]
    BadCarryTarget {
        /// Alias of the chosen cycle.
        target: String,
        /// Why not.
        reason: &'static str,
    },
}

/// The last day of a window: `end` when given, else `start + cycle_days - 1`.
///
/// # Errors
///
/// [`CycleError::BadWindow`] when the end precedes the start, `cycle_days` is 0 with no `end`, or the date is out of range.
pub fn resolve_end(start: Day, end: Option<Day>, cycle_days: u32) -> Result<Day, CycleError> {
    let bad = |end: String, reason: String| {
        tracing::debug!(%start, %end, %reason, "cycle window refused");
        CycleError::BadWindow {
            start: start.to_string(),
            end,
            reason,
        }
    };
    let end = match end {
        Some(e) => e,
        None if cycle_days == 0 => {
            return Err(bad(
                "?".to_owned(),
                "[pm] cycle_days is 0, so pass --end".to_owned(),
            ));
        }
        None => start
            .plus_days(i64::from(cycle_days) - 1)
            .map_err(|m| bad("?".to_owned(), m))?,
    };
    if end < start {
        return Err(bad(
            end.to_string(),
            "the end is before the start".to_owned(),
        ));
    }
    Ok(end)
}

/// What `cycle new` should do given the cycles that already exist.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NewPlan {
    /// The window is free: create the cycle.
    Create,
    /// An identical cycle exists: nothing to write.
    Already(Box<Cycle>),
}

/// Decide `cycle new`: create, report `already`, or refuse a conflicting or overlapping request.
///
/// # Errors
///
/// [`CycleError::Conflict`] when the same window exists with another goal or capacity;
/// [`CycleError::Overlap`] when it shares days with a cycle that is not closed.
pub fn plan_new(
    existing: &[Cycle],
    start: Day,
    end: Day,
    goal: &str,
    capacity_points: Option<u32>,
) -> Result<NewPlan, CycleError> {
    if let Some(c) = existing.iter().find(|c| c.start == start && c.end == end) {
        let mut fields = Vec::new();
        if c.goal != goal {
            fields.push("goal");
        }
        if c.capacity_points != capacity_points {
            fields.push("capacity_points");
        }
        return if fields.is_empty() {
            tracing::debug!(alias = %c.alias(), "cycle new repeats an identical cycle");
            Ok(NewPlan::Already(Box::new(c.clone())))
        } else {
            Err(CycleError::Conflict {
                alias: c.alias(),
                fields,
            })
        };
    }
    if let Some(c) = existing
        .iter()
        .find(|c| c.state != State::Closed && c.start <= end && start <= c.effective_end())
    {
        let next_free = c
            .effective_end()
            .plus_days(1)
            .map_err(|m| CycleError::BadWindow {
                start: start.to_string(),
                end: end.to_string(),
                reason: m,
            })?;
        return Err(CycleError::Overlap {
            start,
            end,
            with: c.alias(),
            state: c.state,
            next_free,
        });
    }
    Ok(NewPlan::Create)
}

/// The [`CycleError::Unknown`] for `input`, suggesting the closest aliases of `existing`.
pub fn unknown_cycle(existing: &[Cycle], input: &str) -> CycleError {
    let mut scored: Vec<(usize, String)> = existing
        .iter()
        .map(|c| (distance(&c.alias(), input), c.alias()))
        .filter(|(d, _)| *d <= 6)
        .collect();
    scored.sort_unstable();
    CycleError::Unknown {
        input: input.to_owned(),
        suggestions: scored.into_iter().take(3).map(|(_, a)| a).collect(),
    }
}

/// A member ticket's standing for the close rules.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemberStatus {
    /// Triage or todo: not started.
    Open,
    /// Being worked.
    InProgress,
    /// Done with a completing outcome (fixed or done): its points count as delivered.
    Finished,
    /// Done without completing the work (wont-fix, duplicate, invalid): finished business, no points delivered.
    Dropped,
}

impl MemberStatus {
    /// True in category `done`, whatever the outcome.
    pub const fn is_done(self) -> bool {
        matches!(self, Self::Finished | Self::Dropped)
    }
}

/// What the close rules need to know about one member ticket.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MemberFacts {
    /// The ticket.
    pub id: TicketId,
    /// Its handle, for messages.
    pub handle: String,
    /// Where the ticket is in its workflow.
    pub status: MemberStatus,
    /// True when a live lease is held on it.
    pub live_lease: bool,
    /// Story points, 0 when unestimated.
    pub points: u32,
}

/// What closing a cycle will record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClosePlan {
    /// The effective end to record: the close day when it falls before the planned end, else `None`.
    pub ended: Option<Day>,
    /// The cycle that takes the carried tickets; `None` when nothing carries.
    pub target: Option<ObjectId>,
    /// Alias of `target`, for messages.
    pub target_alias: Option<String>,
    /// Incomplete members, moving on.
    pub carried: Vec<TicketId>,
    /// Points of every member at close.
    pub committed: u32,
    /// Points of members that completed.
    pub done: u32,
}

impl ClosePlan {
    /// Done over committed points; `None` when nothing was committed.
    pub fn ratio(&self) -> Option<f64> {
        ratio(self.committed, self.done)
    }
}

/// `done / committed`, `None` when `committed` is 0.
pub fn ratio(committed: u32, done: u32) -> Option<f64> {
    (committed > 0).then(|| f64::from(done) / f64::from(committed))
}

/// The cycle that follows `cycle`: the open or planned one with the earliest start after its own.
pub fn next_cycle<'a>(cycle: &Cycle, others: &'a [Cycle]) -> Option<&'a Cycle> {
    others
        .iter()
        .filter(|c| c.id != cycle.id && c.state != State::Closed && c.start > cycle.start)
        .min_by_key(|c| c.start)
}

/// Plan `cycle close`: refuse on live in-progress members, find where incomplete work goes, total the points.
///
/// `carry_to` is the explicit `--carry-to` cycle, which overrides the next-by-start rule.
/// `closed_on` is the close day (UTC); before the planned end it becomes the effective end.
///
/// # Errors
///
/// [`CycleError::LiveLease`] naming the blocking tickets; [`CycleError::BadCarryTarget`] for a
/// closed or same cycle; [`CycleError::NoNextCycle`] when work must carry and no target exists.
pub fn plan_close(
    cycle: &Cycle,
    others: &[Cycle],
    carry_to: Option<&Cycle>,
    members: &[MemberFacts],
    closed_on: Day,
) -> Result<ClosePlan, CycleError> {
    let effective = closed_on.max(cycle.start).min(cycle.end);
    let ended = (effective < cycle.end).then_some(effective);
    tracing::debug!(cycle = %cycle.alias(), %closed_on, ?ended, "cycle close window");
    let blocking: Vec<String> = members
        .iter()
        .filter(|m| m.status == MemberStatus::InProgress && m.live_lease)
        .map(|m| m.handle.clone())
        .collect();
    if !blocking.is_empty() {
        tracing::info!(cycle = %cycle.alias(), ?blocking, "cycle close refused: live leases");
        return Err(CycleError::LiveLease {
            alias: cycle.alias(),
            handles: blocking,
        });
    }
    let carried: Vec<TicketId> = members
        .iter()
        .filter(|m| !m.status.is_done())
        .map(|m| m.id)
        .collect();
    let committed = members.iter().map(|m| m.points).sum();
    let done = members
        .iter()
        .filter(|m| m.status == MemberStatus::Finished)
        .map(|m| m.points)
        .sum();
    let target = if carried.is_empty() {
        None
    } else if let Some(t) = carry_to {
        if t.id == cycle.id {
            return Err(CycleError::BadCarryTarget {
                target: t.alias(),
                reason: "it is the cycle being closed",
            });
        }
        if t.state == State::Closed {
            return Err(CycleError::BadCarryTarget {
                target: t.alias(),
                reason: "it is already closed",
            });
        }
        Some(t)
    } else {
        let Some(t) = next_cycle(cycle, others) else {
            let suggest_start = effective.plus_days(1).unwrap_or(effective);
            return Err(CycleError::NoNextCycle {
                alias: cycle.alias(),
                carrying: carried.len(),
                suggest_start,
            });
        };
        Some(t)
    };
    Ok(ClosePlan {
        ended,
        target: target.map(|t| t.id),
        target_alias: target.map(Cycle::alias),
        carried,
        committed,
        done,
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

    fn member(status: MemberStatus, live: bool, points: u32) -> MemberFacts {
        MemberFacts {
            id: TicketId::mint(),
            handle: "~T".to_owned(),
            status,
            live_lease: live,
            points,
        }
    }

    #[test]
    fn end_defaults_to_start_plus_days_minus_one() {
        assert_eq!(
            resolve_end(day("2026-10-05"), None, 7),
            Ok(day("2026-10-11"))
        );
        assert_eq!(
            resolve_end(day("2026-10-05"), None, 1),
            Ok(day("2026-10-05"))
        );
        assert!(resolve_end(day("2026-10-05"), None, 0).is_err());
        assert!(resolve_end(day("2026-10-05"), Some(day("2026-10-04")), 7).is_err());
    }

    #[test]
    fn overlap_with_an_open_cycle_is_refused_but_closed_is_ignored() {
        let open = cycle("2026-10-05", "2026-10-11", State::Planned);
        let closed = cycle("2026-09-28", "2026-10-04", State::Closed);
        let e = plan_new(
            &[open.clone(), closed],
            day("2026-10-11"),
            day("2026-10-17"),
            "g",
            None,
        );
        assert!(
            matches!(e, Err(CycleError::Overlap { next_free, .. }) if next_free == day("2026-10-12"))
        );
        let ok = plan_new(&[open], day("2026-10-12"), day("2026-10-18"), "g", None);
        assert_eq!(ok, Ok(NewPlan::Create));
    }

    #[test]
    fn unknown_reference_suggests_the_nearest_alias() {
        let c = cycle("2026-10-05", "2026-10-11", State::Planned);
        let e = unknown_cycle(std::slice::from_ref(&c), "2026-10-05..2026-10-12");
        assert!(
            matches!(e, CycleError::Unknown { ref suggestions, .. } if suggestions == &["2026-10-05..2026-10-11"])
        );
        let far = unknown_cycle(&[c], "zzz");
        assert!(
            matches!(far, CycleError::Unknown { ref suggestions, .. } if suggestions.is_empty())
        );
    }

    #[test]
    fn same_window_is_already_or_a_conflict() {
        let c = cycle("2026-10-05", "2026-10-11", State::Planned);
        let again = plan_new(std::slice::from_ref(&c), c.start, c.end, "g", None);
        assert!(matches!(again, Ok(NewPlan::Already(_))));
        let other = plan_new(std::slice::from_ref(&c), c.start, c.end, "x", Some(5));
        assert!(
            matches!(other, Err(CycleError::Conflict { ref fields, .. }) if fields == &["goal", "capacity_points"])
        );
    }

    #[test]
    fn close_blocks_on_live_leases_then_carries_and_totals() {
        let c = cycle("2026-10-05", "2026-10-11", State::Active);
        let next = cycle("2026-10-12", "2026-10-18", State::Planned);
        let later = cycle("2026-10-19", "2026-10-25", State::Planned);
        let others = [later, next.clone(), c.clone()];
        let live = [member(MemberStatus::InProgress, true, 3)];
        assert!(matches!(
            plan_close(&c, &others, None, &live, day("2026-10-11")),
            Err(CycleError::LiveLease { .. })
        ));
        let ms = [
            member(MemberStatus::Finished, false, 5),
            member(MemberStatus::InProgress, false, 3),
            member(MemberStatus::Open, false, 2),
        ];
        let p = plan_close(&c, &others, None, &ms, day("2026-10-11")).expect("plan");
        assert_eq!(p.target, Some(next.id));
        assert_eq!((p.committed, p.done, p.carried.len()), (10, 5, 2));
        assert_eq!(p.ratio(), Some(0.5));
    }

    #[test]
    fn close_needs_a_target_only_when_something_carries() {
        let c = cycle("2026-10-05", "2026-10-11", State::Active);
        let all_done = [member(MemberStatus::Dropped, false, 1)];
        assert_eq!(
            plan_close(&c, &[], None, &all_done, day("2026-10-11"))
                .expect("plan")
                .target,
            None
        );
        let todo = [member(MemberStatus::Open, false, 1)];
        assert!(matches!(
            plan_close(&c, &[], None, &todo, day("2026-10-11")),
            Err(CycleError::NoNextCycle { suggest_start, .. }) if suggest_start == day("2026-10-12")
        ));
        let closed = cycle("2026-10-12", "2026-10-18", State::Closed);
        assert!(matches!(
            plan_close(&c, &[], Some(&closed), &todo, day("2026-10-11")),
            Err(CycleError::BadCarryTarget { .. })
        ));
        assert_eq!(ratio(0, 0), None);
    }

    #[test]
    fn closing_early_records_the_close_day_and_moves_the_suggested_start() {
        // frob:tests crates/frob-pm/src/cycle/lifecycle.rs::plan_close
        let c = cycle("2026-10-05", "2026-10-11", State::Active);
        let todo = [member(MemberStatus::Open, false, 1)];
        let done = [member(MemberStatus::Finished, false, 1)];
        let early = plan_close(&c, &[], None, &done, day("2026-10-06")).expect("plan");
        assert_eq!(early.ended, Some(day("2026-10-06")));
        let on_end = plan_close(&c, &[], None, &done, day("2026-10-11")).expect("plan");
        assert_eq!(on_end.ended, None);
        let late = plan_close(&c, &[], None, &done, day("2026-10-20")).expect("plan");
        assert_eq!(late.ended, None);
        let before = plan_close(&c, &[], None, &done, day("2026-10-01")).expect("plan");
        assert_eq!(before.ended, Some(day("2026-10-05")));
        assert!(matches!(
            plan_close(&c, &[], None, &todo, day("2026-10-06")),
            Err(CycleError::NoNextCycle { suggest_start, .. }) if suggest_start == day("2026-10-07")
        ));
    }

    #[test]
    fn an_early_closed_cycle_does_not_block_the_next_day() {
        // frob:tests crates/frob-pm/src/cycle/lifecycle.rs::plan_new
        let mut c = cycle("2026-10-05", "2026-10-11", State::Closed);
        c.ended = Some(day("2026-10-05"));
        let ok = plan_new(&[c], day("2026-10-06"), day("2026-10-07"), "g", None);
        assert_eq!(ok, Ok(NewPlan::Create));
    }
}
