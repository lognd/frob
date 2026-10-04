//! Leases of terminal tickets: release on every terminal transition, reap leftovers.
//!
//! `ticket close` and `ticket drop` both end in [`release_on_terminal`], so a
//! done ticket never keeps blocking its scope or the holder's WIP limit.
//! [`stale_leases`] finds leases an older binary left behind; `ticket doctor`
//! reports them and `--fix` removes them with [`reap`].

// frob:ticket 01M42MGN8882Y65TVXH0V1WTNR

use frob_ledger::index::ListFilter;
use frob_ledger::model::Category;
use frob_ledger::{Ledger, TicketId};
use gob_cli::{CliError, Context};

use super::{cli_err, open_lease_store};

/// Release the lease on terminal ticket `id`; a failure is a warning because the transition is already committed.
pub(crate) fn release_on_terminal(ctx: &Context, id: TicketId) -> Vec<String> {
    let released = open_lease_store(ctx)
        .map_err(|e| e.to_string())
        .and_then(|(store, _)| store.release(id, None).map_err(|e| e.to_string()));
    match released {
        Ok(Some(lease)) => {
            tracing::info!(ticket = %id, holder = %lease.holder, "lease released on terminal transition");
            Vec::new()
        }
        Ok(None) => {
            tracing::debug!(ticket = %id, "terminal transition: no lease to release");
            Vec::new()
        }
        Err(e) => {
            tracing::warn!(ticket = %id, error = %e, "lease release failed after a terminal transition");
            vec![format!(
                "the lease on {id} was not released: {e}; `frob ticket doctor --fix` removes it"
            )]
        }
    }
}

/// Live leases whose ticket is done in the ledger, as `(ticket, holder)`.
pub(crate) fn stale_leases(
    ctx: &Context,
    ledger: &Ledger,
) -> Result<Vec<(TicketId, String)>, CliError> {
    let (store, _) = open_lease_store(ctx)?;
    let done: std::collections::HashSet<TicketId> = ledger
        .list(&ListFilter {
            category: Some(Category::Done),
            ..Default::default()
        })
        .map_err(cli_err)?
        .into_iter()
        .map(|s| s.id)
        .collect();
    let stale: Vec<_> = store
        .live_snapshot()?
        .into_iter()
        .filter(|l| done.contains(&l.ticket))
        .map(|l| (l.ticket, l.holder.to_string()))
        .collect();
    tracing::debug!(count = stale.len(), "leases of terminal tickets found");
    Ok(stale)
}

/// Remove the leases of the given terminal tickets, logging each; returns the ones removed.
pub(crate) fn reap(ctx: &Context, stale: &[(TicketId, String)]) -> Result<Vec<TicketId>, CliError> {
    let (store, _) = open_lease_store(ctx)?;
    let mut reaped = Vec::new();
    for (id, holder) in stale {
        if store.release(*id, None)?.is_some() {
            tracing::info!(ticket = %id, %holder, "reaped the lease of a terminal ticket");
            reaped.push(*id);
        }
    }
    Ok(reaped)
}
