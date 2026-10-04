//! Wiring for verbs: build a pass [`Env`] from the ledger, lease store and config, and run it.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::time::SystemTime;

use frob_lease::LeaseStore;
use frob_ledger::Ledger;
use frob_ledger::index::ListFilter;
use frob_ledger::model::Category;

use super::config::GcConfig;
use super::pass::{self, Env, Mode, Report, TicketOracle, TicketState};
use super::{artifacts, free};
use crate::config::WorktreeConfig;
use crate::work::{primary_root, worktree_parent};

/// The ledger answering the pass's questions about tickets.
struct LedgerOracle<'a> {
    ledger: &'a Ledger,
}

impl TicketOracle for LedgerOracle<'_> {
    fn state(&self, handle: &str) -> TicketState {
        let shown = self
            .ledger
            .resolve(handle)
            .and_then(|id| self.ledger.show(id));
        match shown {
            Ok(v) if v.summary.category == Category::Done => TicketState::Closed,
            Ok(_) => TicketState::Open,
            Err(e) => {
                tracing::debug!(handle, error = %e, "gc could not resolve a ticket");
                TicketState::Unknown
            }
        }
    }

    fn referenced_digests(&self) -> Option<BTreeSet<String>> {
        let tip = self.ledger.ledger_ref().ok()?;
        let open = self.ledger.list(&ListFilter::default()).ok()?;
        let mut found = BTreeSet::new();
        for s in open.iter().filter(|s| s.category != Category::Done) {
            let events = self.ledger.read_events_at(&tip, s.id).ok()?;
            artifacts::digests_in(&format!("{events:?}"), &mut found);
        }
        Some(found)
    }
}

/// Run a pass for the repository behind `ledger` in `mode`; never fails (errors are warnings in the report).
pub fn run_for(
    ledger: &Ledger,
    leases: &LeaseStore,
    worktree: &WorktreeConfig,
    gc: &GcConfig,
    mode: Mode,
) -> Report {
    let repo = ledger.repo();
    let primary = primary_root(ledger);
    let parent = worktree_parent(&primary, worktree);
    let live: Vec<PathBuf> = match leases.live_snapshot() {
        Ok(l) => l.into_iter().map(|l| l.holder.worktree).collect(),
        Err(e) => {
            tracing::warn!(error = %e, "gc could not read leases; no worktree will be removed");
            // Without the lease list nothing may be assumed idle: treat the parent as live.
            vec![parent.clone()]
        }
    };
    let base = crate::work::base_branch(ledger);
    let oracle = LedgerOracle { ledger };
    let adapters = pass::default_adapters();
    let env = Env {
        repo,
        primary: &primary,
        worktree_parent: &parent,
        base: &base,
        config: gc,
        tickets: &oracle,
        live_worktrees: &live,
        now: SystemTime::now(),
        free_bytes: &free::free_bytes,
        adapters: &adapters,
    };
    pass::run(&env, mode)
}

/// The warnings a verb should show for `report`: its problems, and each worktree kept because it holds unsaved work.
pub fn notices(report: &Report) -> Vec<String> {
    let mut out = report.warnings.clone();
    out.extend(
        report
            .kept
            .iter()
            .map(|k| format!("gc kept {}: {}", k.target, k.reason)),
    );
    out
}
