//! `PM036`: an active cycle is past its end date and still not closed.
//!
//! A cycle never becomes "overdue" by itself (`state_on` keeps it active until a
//! close event), so a team can drift for days with work landing outside any
//! cycle and nothing firing. The pure core [`overdue`] takes folded cycles and
//! the UTC day; [`evaluate`] reads them from a ledger for `frob-check`, and the
//! `work`/`start` gate calls [`overdue_of`] so both agree on what is overdue.

// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ

use frob_ledger::Ledger;
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::cycle::lifecycle::state_on;
use crate::error::Result;
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

#[cfg(test)]
mod tests {
    use super::*;

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
