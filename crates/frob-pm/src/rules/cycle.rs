//! `PM036`: an active cycle is past its end date and still not closed.
//!
//! A cycle never becomes "overdue" by itself (`state_on` keeps it active until a
//! close event), so a team can drift for days with work landing outside any
//! cycle and nothing firing. The pure core [`overdue`] takes folded cycles and
//! the UTC day; [`evaluate`] reads them from a ledger for `frob-check`, and the
//! `work`/`start` gate calls [`overdue_of`] so both agree on what is overdue.
//!
//! The sprint gate shares the same reading: [`sprint_check`] decides whether a
//! ticket may start while a cycle is active, and [`assign_unplanned`] records
//! the `--unplanned --reason` escape as a member plus an over-commit event.

// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ
// frob:ticket 01M4CT016NKN4QRVY0Y57FX1J2

use frob_ledger::{Ledger, TicketId};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::cycle::lifecycle::state_on;
use crate::error::Result;
use crate::event::{CycleEventData, CycleOp, MemberData, Op, PmBody};
use crate::model::{Cycle, Day, Object, ObjectKind, State};
use crate::rules::membership::Evaluation;
use crate::store::PmStore;

/// An active cycle is past its end date and has not been closed.
///
/// Fires once per overdue cycle, naming it and the days overdue. While it
/// stands, `frob work` and `frob start` refuse standard tickets with
/// `E-PM-CYCLE-OVERDUE` (an expedite ticket still starts).
///
/// ## Remedy
///
/// Close the cycle with `frob cycle close --retro TEXT`, which carries the
/// incomplete work to the next cycle and records the retro.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM036",
    slug = "cycle-overdue",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm036;

fn rule_id() -> RuleId {
    Pm036
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// An active cycle past its end date.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Overdue {
    /// The cycle's alias (`START..END`).
    pub alias: String,
    /// Its planned last day.
    pub end: Day,
    /// Whole days from `end` to today (at least 1).
    pub days: i64,
}

/// Every cycle of the ledger, folded; unreadable ones are skipped by the store.
///
/// # Errors
///
/// Ledger read failures.
pub fn cycles(ledger: &Ledger) -> Result<Vec<Cycle>> {
    Ok(PmStore::new(ledger)
        .list(ObjectKind::Cycle)?
        .into_iter()
        .filter_map(|o| match o {
            Object::Cycle(c) => Some(c),
            Object::Milestone(_) => None,
        })
        .collect())
}

/// The cycles that are active on `today` (started, not closed), the set the work gates judge by.
pub fn active(cycles: &[Cycle], today: Day) -> Vec<&Cycle> {
    cycles
        .iter()
        .filter(|c| state_on(c, today) == State::Active)
        .collect()
}

/// The active cycles in `cycles` whose planned end is before `today`.
pub fn overdue(cycles: &[Cycle], today: Day) -> Vec<Overdue> {
    active(cycles, today)
        .into_iter()
        .filter(|c| today > c.end)
        .map(|c| Overdue {
            alias: c.alias(),
            end: c.end,
            days: today.days_since(c.end),
        })
        .collect()
}

/// The overdue active cycles of `ledger` on its clock's UTC day.
///
/// # Errors
///
/// Ledger read failures.
pub fn overdue_of(ledger: &Ledger) -> Result<Vec<Overdue>> {
    let today = PmStore::new(ledger).today();
    let found = overdue(&cycles(ledger)?, today);
    tracing::debug!(%today, overdue = found.len(), "overdue cycles read");
    Ok(found)
}

/// The message naming an overdue cycle, shared by the finding and the work refusal.
pub fn describe(o: &Overdue) -> String {
    format!(
        "cycle {} ended {} and is still active ({} day(s) overdue)",
        o.alias, o.end, o.days
    )
}

/// Evaluate `PM036` over `overdue`; `subjects` is how many active cycles were examined.
pub fn pm036(overdue: &[Overdue], subjects: usize) -> Evaluation {
    let findings = overdue
        .iter()
        .map(|o| {
            tracing::debug!(cycle = %o.alias, days = o.days, "PM036: cycle overdue");
            Finding::new(
                rule_id(),
                Severity::Warn,
                None,
                format!(
                    "{}; close it with `frob cycle close --retro TEXT` (new work is refused until then)",
                    describe(o)
                ),
                &format!("cycle:{}", o.alias),
            )
        })
        .collect();
    Evaluation { findings, subjects }
}

/// Read the cycles from `ledger` and run [`pm036`] on its clock's UTC day; empty without cycles.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger) -> Result<Evaluation> {
    let today = PmStore::new(ledger).today();
    let all = cycles(ledger)?;
    let subjects = active(&all, today).len();
    let out = pm036(&overdue(&all, today), subjects);
    tracing::info!(subjects, findings = out.findings.len(), "PM036 evaluated");
    Ok(out)
}

/// The sprint gate's reading of the active cycles for one ticket.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SprintCheck {
    /// No cycle is active: nothing to be outside of.
    NoActiveCycle,
    /// The ticket is a member of an active cycle.
    Planned,
    /// The ticket is not in the active cycle `alias`; `elsewhere` names the other open or planned cycle that holds it, if any.
    Unplanned {
        /// Alias of the active cycle the ticket would join.
        alias: String,
        /// Alias of another open or planned cycle that holds the ticket.
        elsewhere: Option<String>,
    },
}

/// Judge `ticket` against the cycles active on `today`: the first active cycle by start is the sprint, and membership of any active cycle counts as planned.
pub fn sprint_check(cycles: &[Cycle], today: Day, ticket: TicketId) -> SprintCheck {
    let mut live = active(cycles, today);
    live.sort_by_key(|c| c.start);
    let Some(first) = live.first() else {
        return SprintCheck::NoActiveCycle;
    };
    if live.iter().any(|c| c.tickets.contains(&ticket)) {
        return SprintCheck::Planned;
    }
    let elsewhere = cycles
        .iter()
        .find(|c| c.state != State::Closed && c.tickets.contains(&ticket))
        .map(Cycle::alias);
    SprintCheck::Unplanned {
        alias: first.alias(),
        elsewhere,
    }
}

/// The alias of the sprint cycle `ticket` would join under `--unplanned`: the first active cycle by start.
pub fn sprint_cycle(cycles: &[Cycle], today: Day) -> Option<&Cycle> {
    active(cycles, today).into_iter().min_by_key(|c| c.start)
}

/// Assign `ticket` to the active cycle `target` as unplanned work: leave any other open or planned cycle, join `target` and record an `over-commit` event carrying `reason`.
///
/// The event has no point totals: unplanned work is judged by the reason in the retro, not by capacity.
///
/// # Errors
///
/// Ledger and store failures.
pub fn assign_unplanned(
    ledger: &Ledger,
    cycles: &[Cycle],
    target: &Cycle,
    ticket: TicketId,
    reason: &str,
) -> Result<()> {
    let store = PmStore::new(ledger);
    for old in cycles
        .iter()
        .filter(|c| c.id != target.id && c.state != State::Closed && c.tickets.contains(&ticket))
    {
        tracing::info!(from = %old.alias(), %ticket, "unplanned work leaves its other cycle");
        store.set_member(ObjectKind::Cycle, old.id, ticket, Op::Remove)?;
    }
    store.append_many(
        ObjectKind::Cycle,
        target.id,
        vec![
            PmBody::Member(MemberData {
                op: Op::Add,
                ticket,
            }),
            PmBody::Cycle(Box::new(CycleEventData {
                op: CycleOp::OverCommit,
                ticket: Some(ticket),
                to: None,
                committed: None,
                done: None,
                text: Some(reason.to_owned()),
                capacity: None,
            })),
        ],
    )?;
    tracing::info!(cycle = %target.alias(), %ticket, reason, "unplanned work joined the active cycle");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cycle_on(start: &str, end: &str, tickets: Vec<TicketId>) -> Cycle {
        use crate::model::ObjectId;
        Cycle {
            id: ObjectId::mint(),
            start: start.parse().unwrap(),
            end: end.parse().unwrap(),
            ended: None,
            goal: "g".to_owned(),
            capacity_points: None,
            state: State::Planned,
            tickets,
            created: frob_ledger::model::Stamp::from_unix(1_800_000_000),
            updated: frob_ledger::model::Stamp::from_unix(1_800_000_000),
            ordinal: 1,
        }
    }

    #[test]
    fn sprint_check_distinguishes_planned_unplanned_and_no_cycle() {
        // frob:tests crates/frob-pm/src/rules/cycle.rs::sprint_check
        // frob:tests crates/frob-pm/src/rules/cycle.rs::sprint_cycle
        let (member, stranger, parked) = (TicketId::mint(), TicketId::mint(), TicketId::mint());
        let today: Day = "2026-10-08".parse().unwrap();
        let current = cycle_on("2026-10-07", "2026-10-09", vec![member]);
        let next = cycle_on("2026-10-10", "2026-10-16", vec![parked]);
        let all = [current.clone(), next];
        assert_eq!(sprint_check(&[], today, member), SprintCheck::NoActiveCycle);
        assert_eq!(sprint_check(&all, today, member), SprintCheck::Planned);
        assert_eq!(
            sprint_check(&all, today, stranger),
            SprintCheck::Unplanned {
                alias: current.alias(),
                elsewhere: None
            }
        );
        let SprintCheck::Unplanned { elsewhere, .. } = sprint_check(&all, today, parked) else {
            panic!("a ticket parked in a planned cycle is outside the sprint");
        };
        assert_eq!(elsewhere.as_deref(), Some("2026-10-10..2026-10-16"));
        assert_eq!(sprint_cycle(&all, today).map(|c| c.id), Some(current.id));
    }

    #[test]
    fn no_overdue_is_clean() {
        // frob:tests crates/frob-pm/src/rules/cycle.rs::pm036
        assert!(pm036(&[], 0).findings.is_empty());
    }

    #[test]
    fn describe_names_cycle_and_days() {
        // frob:tests crates/frob-pm/src/rules/cycle.rs::describe
        let o = Overdue {
            alias: "2026-10-01..2026-10-05".into(),
            end: "2026-10-05".parse().unwrap(),
            days: 2,
        };
        let text = describe(&o);
        assert!(text.contains("2026-10-01..2026-10-05") && text.contains("2 day(s)"));
    }
}
