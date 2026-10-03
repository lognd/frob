//! The repository WIP limit (`[pm.wip] in_progress`): who holds the slots and when `work` and `start` must refuse.
//!
//! Only in-progress tickets with a live lease count. An in-progress ticket whose
//! lease expired is stale: it is named in the refusal (with a requeue hint) but
//! never occupies a slot. The decision is a pure function over those two lists
//! so it can be tested without a repository, and so the expedite lane of
//! `releases.md` section 2 can later raise the `ceiling` it takes.

// frob:ticket 01M4069T76A6WSNHT3NZERXHAH

use std::fmt::Write;

use frob_lease::Lease;
use frob_ledger::index::ListFilter;
use frob_ledger::model::Category;
use frob_ledger::model::Stamp;
use frob_ledger::{Ledger, TicketId};
use gob_diagnostics::{Refusal, RefusalClass};

use crate::error::WorktreeError;

/// The refusal code of a repository WIP breach.
pub const CODE: &str = "E-WIP-REPO";

/// One in-progress ticket holding a WIP slot: its live lease.
#[derive(Debug, Clone)]
pub struct Holding {
    /// Handle with `~`.
    pub handle: String,
    /// Ticket title.
    pub title: String,
    /// The live lease (holder, worktree, since).
    pub lease: Lease,
}

/// One in-progress ticket whose lease expired: reported, not counted.
#[derive(Debug, Clone)]
pub struct Stale {
    /// Handle with `~`.
    pub handle: String,
    /// Ticket title.
    pub title: String,
    /// Time of the ticket's latest event.
    pub since: Stamp,
}

/// The refusal for taking one more ticket when `holdings` already fill `ceiling` slots; `None` when there is room or the limit is off (0).
pub fn refusal(
    ceiling: u32,
    holdings: &[Holding],
    stale: &[Stale],
    handle: &str,
) -> Option<Refusal> {
    if ceiling == 0 || holdings.len() < ceiling as usize {
        return None;
    }
    let mut msg = format!(
        "the repository is at its in-progress limit ({} of {ceiling}); taking {handle} would exceed [pm.wip] in_progress. Current holders:",
        holdings.len()
    );
    for h in holdings {
        let _ = write!(
            msg,
            "\n  {} {} - holder {}, worktree {}, since {}",
            h.handle,
            h.title,
            h.lease.holder.actor,
            h.lease.holder.worktree.display(),
            h.lease.acquired_at
        );
    }
    if !stale.is_empty() {
        msg.push_str("\nStale (in progress, lease expired; not counted):");
        for s in stale {
            let _ = write!(
                msg,
                "\n  {} {} - since {}; requeue it with: frob requeue {} --reason stale",
                s.handle, s.title, s.since, s.handle
            );
        }
    }
    let remedy = "finish or requeue one of the holders (frob requeue <ticket> --reason <why>), or raise [pm.wip] in_progress in frob.toml";
    Some(Refusal::new(CODE, RefusalClass::GuardNeedsAction, msg).with_remedy(remedy))
}

/// Check that taking `id` (handle `handle`) fits under `limit`; a limit of 0 skips the check.
///
/// # Errors
///
/// `E-WIP-REPO` naming every holder when the repository is at its limit; ledger and lease failures.
pub fn check(
    ledger: &Ledger,
    leases: &frob_lease::LeaseStore,
    limit: u32,
    id: TicketId,
    handle: &str,
) -> Result<(), WorktreeError> {
    if limit == 0 {
        tracing::debug!(%id, "repository wip limit off");
        return Ok(());
    }
    let filter = ListFilter {
        category: Some(Category::InProgress),
        ..ListFilter::default()
    };
    let live = leases.live_snapshot()?;
    let mut holdings = Vec::new();
    let mut stale = Vec::new();
    for s in ledger.list(&filter)? {
        if s.id == id {
            continue;
        }
        match live.iter().find(|l| l.ticket == s.id) {
            Some(lease) => holdings.push(Holding {
                handle: s.handle,
                title: s.title,
                lease: lease.clone(),
            }),
            None => stale.push(Stale {
                handle: s.handle,
                title: s.title,
                since: s.updated,
            }),
        }
    }
    tracing::debug!(%id, limit, holders = holdings.len(), stale = stale.len(), "repository wip counted");
    match refusal(limit, &holdings, &stale, handle) {
        Some(r) => {
            tracing::info!(%id, limit, holders = holdings.len(), "work refused: repository wip limit");
            Err(WorktreeError::Refused(r))
        }
        None => Ok(()),
    }
}
