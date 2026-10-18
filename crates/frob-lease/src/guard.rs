//! The [`LeaseCheck`] `doable` consults: hide tickets whose scope overlaps a live lease.

use std::collections::BTreeSet;
use std::path::Path;
use std::sync::OnceLock;

use frob_ledger::guards::LeaseCheck;
use frob_ledger::index::Summary;

use crate::error::LeaseError;
use crate::model::Lease;
use crate::overlap::{effective, files_overlap, text_overlap};
use crate::store::LeaseStore;

/// A snapshot of the live leases that answers `is_free` for candidate tickets.
#[derive(Debug)]
pub struct LeaseGuard {
    store: LeaseStore,
    live: Vec<Held>,
}

/// One live lease with its effective scope and its resolved files, each computed at most once.
#[derive(Debug)]
struct Held {
    lease: Lease,
    effective: Vec<String>,
    files: OnceLock<Result<BTreeSet<String>, String>>,
}

// frob:ticket 01M4BMRX5T7R0BH9P7HZZQ6PA9
impl LeaseGuard {
    /// Snapshot the live leases of `store` (read-only, no lock, nothing pruned).
    ///
    /// # Errors
    ///
    /// I/O and format failures reading the lease directory.
    pub fn new(store: LeaseStore) -> Result<Self, LeaseError> {
        let live = store.live_snapshot()?;
        tracing::debug!(live = live.len(), "lease guard snapshot taken");
        let live = live
            .into_iter()
            .map(|lease| Held {
                effective: effective(&lease.scope, store.shared(), lease.ticket),
                lease,
                files: OnceLock::new(),
            })
            .collect();
        Ok(Self { store, live })
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

// frob:ticket 01M4BMRX5T7R0BH9P7HZZQ6PA9
impl LeaseGuard {
    /// How many times the tree was scanned to resolve a scope since the guard was built.
    pub fn resolutions(&self) -> usize {
        self.store.resolver().resolutions()
    }

    /// The files `held` resolves to, walking the tree for it only on the first call.
    fn held_files<'a>(&self, held: &'a Held) -> Result<&'a BTreeSet<String>, String> {
        held.files
            .get_or_init(|| {
                self.store
                    .resolver()
                    .resolve_owned(&held.effective, self.store.shared(), held.lease.ticket)
                    .map_err(|e| e.to_string())
            })
            .as_ref()
            .map_err(Clone::clone)
    }

    /// Describe how `ticket`'s scope collides with a live lease of another ticket, if it does.
    fn conflict(
        &self,
        ticket: &Summary,
        scope: &[String],
    ) -> Result<Option<(String, String)>, String> {
        let others: Vec<&Held> = self
            .live
            .iter()
            .filter(|h| h.lease.ticket != ticket.id)
            .collect();
        let mine = effective(scope, self.store.shared(), ticket.id);
        for h in &others {
            if let Some(o) = text_overlap(&mine, &h.effective).map_err(|e| e.to_string())? {
                return Ok(Some((h.lease.ticket.to_string(), o)));
            }
        }
        if others.is_empty() {
            return Ok(None);
        }
        let mine_files = self
            .store
            .resolver()
            .resolve_owned(&mine, self.store.shared(), ticket.id)
            .map_err(|e| e.to_string())?;
        for h in &others {
            if let Some(o) = files_overlap(&mine_files, self.held_files(h)?) {
                return Ok(Some((h.lease.ticket.to_string(), o)));
            }
        }
        Ok(None)
    }
}

impl LeaseCheck for LeaseGuard {
    fn is_free(&self, ticket: &Summary, scope: &[String]) -> bool {
        match self.conflict(ticket, scope) {
            Ok(None) => true,
            Ok(Some((held, overlap))) => {
                tracing::debug!(ticket = %ticket.id, %held, %overlap, "scope leased");
                false
            }
            Err(e) => {
                tracing::warn!(ticket = %ticket.id, error = %e, "overlap check failed; hiding ticket");
                false
            }
        }
    }
}
