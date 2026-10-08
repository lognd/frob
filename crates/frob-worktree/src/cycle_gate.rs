//! The cycle gates of `work` and `start`: refuse new work while the sprint discipline is broken.
//!
//! `E-PM-CYCLE-OVERDUE` fires when an active cycle is past its end date
//! (the same set `PM036` reports, from `frob_pm::rules::cycle`); an expedite
//! ticket is exempt because it must be able to start whatever the state of the
//! plan. Only a ticket taking a fresh slot is judged; re-entering a ticket that
//! already holds its lease changes nothing.
//!
//! `E-PM-NOT-IN-CYCLE` is the sprint gate (`[pm] sprint_gate`): while a cycle is
//! active, a standard ticket outside it is refused unless the caller starts it
//! `--unplanned --reason TEXT`, which assigns it to the active cycle as an
//! over-commit (visible in the retro and the commitment ratio).

// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ
// frob:ticket 01M4CT016NKN4QRVY0Y57FX1J2

use frob_ledger::model::Class;
use frob_ledger::{Ledger, TicketId};
use frob_pm::PmStore;
use frob_pm::rules::cycle::{self, Overdue, SprintCheck};
use gob_diagnostics::{Refusal, RefusalClass};

use crate::error::WorktreeError;

/// The refusal code of starting work while an active cycle is overdue.
pub const OVERDUE_CODE: &str = "E-PM-CYCLE-OVERDUE";

/// The refusal code of starting a ticket outside the active cycle.
pub const NOT_IN_CYCLE_CODE: &str = "E-PM-NOT-IN-CYCLE";

/// The refusal for taking `handle` while `overdue` cycles are still active; `None` when there are none.
pub fn overdue_refusal(overdue: &[Overdue], handle: &str) -> Option<Refusal> {
    if overdue.is_empty() {
        return None;
    }
    let named: Vec<String> = overdue.iter().map(cycle::describe).collect();
    let msg = format!(
        "cannot start {handle}: {}. Close the finished cycle before starting new work",
        named.join("; ")
    );
    let remedy = "close it with `frob cycle close --retro TEXT` (carries unfinished work to the next cycle), or start an expedite ticket";
    Some(Refusal::new(OVERDUE_CODE, RefusalClass::GuardNeedsAction, msg).with_remedy(remedy))
}

/// Refuse to start `handle` of `class` while an active cycle is past its end date; expedite always passes.
///
/// # Errors
///
/// `E-PM-CYCLE-OVERDUE` naming each overdue cycle; ledger read failures.
pub fn check_overdue(ledger: &Ledger, class: Class, handle: &str) -> Result<(), WorktreeError> {
    if class == Class::Expedite {
        tracing::debug!(handle, "cycle overdue gate skipped: expedite ticket");
        return Ok(());
    }
    let overdue = cycle::overdue_of(ledger)?;
    match overdue_refusal(&overdue, handle) {
        Some(r) => {
            tracing::info!(
                handle,
                cycles = overdue.len(),
                "work refused: active cycle overdue"
            );
            Err(WorktreeError::Refused(r))
        }
        None => Ok(()),
    }
}

/// The refusal for starting `handle` outside the active cycle `alias`; `elsewhere` names another open or planned cycle holding it.
pub fn not_in_cycle_refusal(alias: &str, elsewhere: Option<&str>, handle: &str) -> Refusal {
    let held = elsewhere.map_or_else(String::new, |e| format!(" (it sits in cycle {e})"));
    let msg = format!(
        "cannot start {handle}: it is not in the active cycle {alias}{held}. Work comes from the sprint backlog"
    );
    let remedy = format!(
        "add it to the cycle with `frob cycle assign {handle}`, or start it as unplanned work with `frob work {handle} --unplanned --reason TEXT` (recorded as an over-commit for the retro); expedite tickets are exempt"
    );
    Refusal::new(NOT_IN_CYCLE_CODE, RefusalClass::GuardNeedsAction, msg).with_remedy(remedy)
}

/// Apply the sprint gate to `handle` (`id`, `class`) when `sprint_gate` is on.
///
/// Expedite tickets and repositories with no active cycle pass. A ticket outside the
/// active cycle is refused with `E-PM-NOT-IN-CYCLE`, or, when `unplanned` carries a
/// reason, assigned to that cycle as an over-commit and let through.
///
/// # Errors
///
/// `E-PM-NOT-IN-CYCLE`; ledger and store failures.
pub fn check_sprint(
    ledger: &Ledger,
    sprint_gate: bool,
    taking: (TicketId, Class, &str),
    unplanned: Option<&str>,
) -> Result<(), WorktreeError> {
    let (id, class, handle) = taking;
    if !sprint_gate {
        tracing::debug!(handle, "sprint gate off");
        return Ok(());
    }
    if class == Class::Expedite {
        tracing::debug!(handle, "sprint gate skipped: expedite ticket");
        return Ok(());
    }
    let all = cycle::cycles(ledger)?;
    let today = PmStore::new(ledger).today();
    match cycle::sprint_check(&all, today, id) {
        SprintCheck::NoActiveCycle => {
            tracing::debug!(handle, "sprint gate: no active cycle");
            Ok(())
        }
        SprintCheck::Planned => {
            tracing::debug!(handle, "sprint gate: ticket is in the active cycle");
            Ok(())
        }
        SprintCheck::Unplanned { alias, elsewhere } => {
            let Some(reason) = unplanned else {
                tracing::info!(handle, cycle = %alias, "work refused: ticket outside the active cycle");
                return Err(WorktreeError::Refused(not_in_cycle_refusal(
                    &alias,
                    elsewhere.as_deref(),
                    handle,
                )));
            };
            let target = cycle::sprint_cycle(&all, today)
                .unwrap_or_else(|| unreachable!("an unplanned verdict names an active cycle"));
            cycle::assign_unplanned(ledger, &all, target, id, reason)?;
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_overdue_cycle_means_no_refusal() {
        // frob:tests crates/frob-worktree/src/cycle_gate.rs::overdue_refusal
        assert!(overdue_refusal(&[], "~ABC").is_none());
    }

    #[test]
    fn not_in_cycle_hint_names_assign_and_unplanned() {
        // frob:tests crates/frob-worktree/src/cycle_gate.rs::not_in_cycle_refusal
        let r = not_in_cycle_refusal("2026-10-07..2026-10-09", None, "~ABC");
        let hint = r.remedy.unwrap_or_default();
        assert!(
            hint.contains("cycle assign") && hint.contains("--unplanned"),
            "{hint}"
        );
    }
}
