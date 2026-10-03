//! The [`LeaseCheck`] `doable` consults: hide tickets whose scope overlaps a live lease.

use std::path::Path;

use frob_ledger::guards::LeaseCheck;
use frob_ledger::index::Summary;

use crate::error::LeaseError;
use crate::model::Lease;
use crate::overlap::scopes_overlap;
use crate::store::LeaseStore;

/// A snapshot of the live leases that answers `is_free` for candidate tickets.
#[derive(Debug)]
pub struct LeaseGuard {
    store: LeaseStore,
    live: Vec<Lease>,
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
        Ok(Self { store, live })
    }

    /// Open the repository containing `cwd` with the caller's `cfg` and snapshot.
    ///
    /// # Errors
    ///
    /// [`LeaseError::Repo`] when `cwd` is not in a work tree, plus [`LeaseGuard::new`] failures.
    pub fn discover(cwd: &Path, cfg: crate::LeaseConfig) -> Result<Self, LeaseError> {
        Self::new(crate::open_store(cwd, cfg)?.0)
    }
}

impl LeaseCheck for LeaseGuard {
    fn is_free(&self, ticket: &Summary, scope: &[String]) -> bool {
        for lease in self.live.iter().filter(|l| l.ticket != ticket.id) {
            match scopes_overlap(
                scope,
                &lease.scope,
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
