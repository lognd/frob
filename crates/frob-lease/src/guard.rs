//! The [`LeaseCheck`] `doable` consults: hide tickets whose scope overlaps a live lease.

use std::collections::HashMap;
use std::path::Path;

use frob_ledger::TicketId;
use frob_ledger::claim_cover::Claim;
use frob_ledger::guards::LeaseCheck;
use frob_ledger::index::Summary;

use crate::error::LeaseError;
use crate::model::Lease;
use crate::overlap::{effective_overlap, effective_scope};
use crate::store::LeaseStore;

/// A snapshot of the live leases that answers `is_free` for candidate tickets.
#[derive(Debug)]
pub struct LeaseGuard {
    store: LeaseStore,
    live: Vec<Lease>,
    /// Each live lease's exemption-reduced scope, computed once for every candidate.
    // frob:ticket 01M4MGNX6AWFK18T5YJ566VMKA
    held: Vec<Vec<String>>,
}

impl LeaseGuard {
    /// Snapshot the live leases of `store` (read-only, no lock, nothing pruned).
    ///
    /// # Errors
    ///
    /// I/O and format failures reading the lease directory.
    pub fn new(store: LeaseStore) -> Result<Self, LeaseError> {
        let live = store.live_snapshot()?;
        tracing::debug!(live = live.len(), "lease guard snapshot taken");
        let held = live
            .iter()
            .map(|l| effective_scope(&l.scope, store.shared(), l.ticket))
            .collect();
        Ok(Self { store, live, held })
    }

    /// Open the repository containing `cwd` with the caller's `cfg` and snapshot.
    ///
    /// # Errors
    ///
    /// [`LeaseError::Repo`] when `cwd` is not in a work tree, plus [`LeaseGuard::new`] failures.
    pub fn discover(
        cwd: &Path,
        cfg: crate::LeaseConfig,
        clock: std::sync::Arc<dyn gob_time::Clock>,
    ) -> Result<Self, LeaseError> {
        Self::new(crate::open_store(cwd, cfg, clock)?.0)
    }
}

impl LeaseCheck for LeaseGuard {
    // frob:ticket 01M5DJ4K69T67D50C19B4NY6RM
    fn claims(&self) -> HashMap<TicketId, Claim> {
        self.live
            .iter()
            .map(|l| {
                (
                    l.ticket,
                    Claim {
                        holder: l.holder.actor.clone(),
                    },
                )
            })
            .collect()
    }

    fn is_free(&self, ticket: &Summary, scope: &[String]) -> bool {
        // frob:ticket 01M4MGNX6AWFK18T5YJ566VMKA
        let mine = effective_scope(scope, self.store.shared(), ticket.id);
        for (lease, held) in self.live.iter().zip(&self.held) {
            if lease.ticket == ticket.id {
                continue;
            }
            match effective_overlap(
                (&mine, ticket.id),
                (held, lease.ticket),
                self.store.shared(),
                self.store.resolver(),
            ) {
                Ok(None) => {}
                Ok(Some(overlap)) => {
                    tracing::debug!(ticket = %ticket.id, held = %lease.ticket, %overlap, "scope leased");
                    return false;
                }
                Err(e) => {
                    tracing::warn!(ticket = %ticket.id, error = %e, "overlap check failed; hiding ticket");
                    return false;
                }
            }
        }
        true
    }
}
