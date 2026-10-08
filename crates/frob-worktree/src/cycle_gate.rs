//! The cycle gates of `work` and `start`: refuse new work while the sprint discipline is broken.
//!
//! `E-PM-CYCLE-OVERDUE` fires when an active cycle is past its end date
//! (the same set `PM036` reports, from `frob_pm::rules::cycle`); an expedite
//! ticket is exempt because it must be able to start whatever the state of the
//! plan. Only a ticket taking a fresh slot is judged; re-entering a ticket that
//! already holds its lease changes nothing.

// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ

use frob_ledger::Ledger;
use frob_ledger::model::Class;
use frob_pm::rules::cycle::{self, Overdue};
use gob_diagnostics::{Refusal, RefusalClass};

use crate::error::WorktreeError;

/// The refusal code of starting work while an active cycle is overdue.
pub const OVERDUE_CODE: &str = "E-PM-CYCLE-OVERDUE";

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_overdue_cycle_means_no_refusal() {
        // frob:tests crates/frob-worktree/src/cycle_gate.rs::overdue_refusal
        assert!(overdue_refusal(&[], "~ABC").is_none());
    }
}
