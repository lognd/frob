//! The pending-proposal count of `frob check` and the ledger scan behind `frob ticket proposals`.
//!
//! Pending tracker proposals (mirror.md 3.5) are advisory: they never fail a run,
//! the summary only reports how many await a decision.
// frob:ticket 01M3ZXGAWKZPVY6HF9NJ8GAFQV

use std::collections::BTreeSet;
use std::path::Path;
use std::sync::Arc;

use frob_ledger::proposal::{Proposal, pending};
use frob_ledger::{Ledger, LedgerConfig, Result, TicketId};

/// The pending proposals of one ticket.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TicketProposals {
    /// The ticket they are held on.
    pub ticket: TicketId,
    /// Its pending proposals, one per (item, field).
    pub pending: Vec<Proposal>,
}

/// Every ticket of `ledger` (or only `only`) that holds a pending proposal, in ticket order.
///
/// # Errors
///
/// Store failures, or [`frob_ledger::LedgerError::NotFound`] when `only` names an absent ticket.
pub fn pending_by_ticket(ledger: &Ledger, only: Option<TicketId>) -> Result<Vec<TicketProposals>> {
    let ids: BTreeSet<TicketId> = match only {
        Some(id) => BTreeSet::from([id]),
        None => ledger.ticket_ids()?,
    };
    let events = ledger.events_many(&ids)?;
    let found: Vec<TicketProposals> = events
        .into_iter()
        .filter_map(|(ticket, evs)| {
            let pending = pending(&evs);
            (!pending.is_empty()).then_some(TicketProposals { ticket, pending })
        })
        .collect();
    tracing::debug!(tickets = found.len(), "tickets with pending proposals");
    Ok(found)
}

/// How many proposals are pending across the ledger.
///
/// # Errors
///
/// Store failures reading the ledger.
pub fn pending_count(ledger: &Ledger) -> Result<usize> {
    let n = pending_by_ticket(ledger, None)?
        .iter()
        .map(|t| t.pending.len())
        .sum();
    tracing::info!(pending = n, "pending proposals counted");
    Ok(n)
}

/// The pending count of the repository at `root`, or `None` when it has no readable ledger.
///
/// A missing or unreadable ledger is the ledger rules' business, never this summary's.
pub fn pending_count_at(root: &Path, clock: Arc<dyn gob_time::Clock>) -> Option<usize> {
    let repo = gob_git::Repo::discover(root).ok()?;
    repo.work_dir()?;
    let cfg = frob_evidence::workspace::ledger_config(root).unwrap_or_else(|err| {
        tracing::warn!(%err, "ledger config unreadable; using defaults");
        LedgerConfig::default()
    });
    let ledger = Ledger::open(repo, cfg, clock);
    match pending_count(&ledger) {
        Ok(n) => Some(n),
        Err(err) => {
            tracing::debug!(%err, "pending proposals not counted");
            None
        }
    }
}

/// The advisory summary line for `count` pending proposals, or `None` when there are none.
pub fn summary_line(count: usize) -> Option<String> {
    (count > 0).then(|| {
        format!(
            "{count} pending proposal(s) from the tracker; review with `frob ticket proposals list` (advisory, does not affect the exit status)"
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-check/src/proposals_summary.rs::summary_line
    #[test]
    fn no_pending_proposals_print_nothing_and_some_print_the_count() {
        assert_eq!(summary_line(0), None);
        let line = summary_line(3).expect("a line");
        assert!(line.starts_with("3 pending proposal(s)"), "{line}");
        assert!(line.contains("does not affect the exit status"), "{line}");
    }
}
