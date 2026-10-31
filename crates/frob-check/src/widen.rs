//! Growing a ticket's scope to the files its diff touches (frob:ticket 01M4KW3A47K7S9WGD3NBVVPJB4).
//!
//! Shared by `frob lease widen --from-diff` (planning only) and `frob check --ticket --widen`
//! (planning plus applying). A changed file is absorbed only when no other live lease holds it.

use frob_lease::widen::{Absorb, plan_absorb};
use frob_lease::{LeaseError, LeaseStore};
use frob_ledger::ops::Patch;
use frob_ledger::{Ledger, TicketId};

use crate::scope::{branch_changes, effective_base};

/// Why a diff-driven widen failed.
#[derive(Debug, thiserror::Error)]
pub enum WidenError {
    /// The diff could not be taken.
    #[error("cannot diff the branch: {0}")]
    Diff(String),
    /// The lease store refused (or failed).
    #[error(transparent)]
    Lease(#[from] LeaseError),
    /// The ledger refused (or failed).
    #[error("ledger: {0}")]
    Ledger(String),
    /// Someone else holds this ticket's lease.
    #[error("ticket {ticket} is leased by {holder}; only the holder can widen it")]
    NotHolder {
        /// The ticket.
        ticket: TicketId,
        /// The actor holding the lease.
        holder: String,
    },
}

/// Plan which diff files ticket `id` may absorb: those outside its scope that no other live lease holds.
///
/// The diff is taken against `explicit`, else the lease's pinned base, else `default_base`.
///
/// # Errors
///
/// [`WidenError`] when the diff, the ledger or the lease store fails.
pub fn plan_from_diff(
    ledger: &Ledger,
    store: &LeaseStore,
    id: TicketId,
    explicit: Option<&str>,
    default_base: &str,
) -> Result<Absorb, WidenError> {
    let view = ledger
        .show(id)
        .map_err(|e| WidenError::Ledger(e.to_string()))?;
    let live = store.live_lease(id)?;
    // The effective scope is the lease's when one is live, else the ticket's.
    let scope = live
        .as_ref()
        .map_or_else(|| view.ticket.front.scope.clone(), |l| l.scope.clone());
    let base = match &live {
        Some(l) => effective_base(explicit, l, default_base),
        None => explicit.unwrap_or(default_base).to_owned(),
    };
    let changed: Vec<String> = branch_changes(ledger.repo(), &base, ledger.config())
        .map_err(|e| WidenError::Diff(e.to_string()))?
        .into_iter()
        .map(|p| p.as_str().to_owned())
        .collect();
    let others = store.live_snapshot()?;
    let plan = plan_absorb(id, &scope, &changed, &others, store.shared())?;
    tracing::info!(%id, %base, add = plan.add.len(), held = plan.held.len(), "diff widen planned");
    Ok(plan)
}

/// Plan and apply a diff-driven widen: rescope the lease, then commit the ledger scope change.
///
/// Idempotent: a second run finds nothing outside the scope and records no event. The lease is
/// restored when the ledger commit fails.
///
/// # Errors
///
/// [`WidenError`] when planning fails, the caller is not the lease holder, or an update is refused.
pub fn apply_from_diff(
    ledger: &Ledger,
    store: &LeaseStore,
    id: TicketId,
    explicit: Option<&str>,
    default_base: &str,
) -> Result<Absorb, WidenError> {
    let plan = plan_from_diff(ledger, store, id, explicit, default_base)?;
    if plan.add.is_empty() {
        tracing::debug!(%id, "diff widen has nothing to absorb");
        return Ok(plan);
    }
    let patch = Patch {
        add_scope: plan.add.clone(),
        ..Patch::default()
    };
    let restore = match store.live_lease(id)? {
        Some(l) => {
            let actor = ledger
                .actor()
                .map_err(|e| WidenError::Ledger(e.to_string()))?;
            if l.holder.actor != actor {
                return Err(WidenError::NotHolder {
                    ticket: id,
                    holder: l.holder.actor,
                });
            }
            let new = ledger
                .scope_after(id, &patch)
                .map_err(|e| WidenError::Ledger(e.to_string()))?;
            store.rescope(id, &l.holder, &new, store.config())?;
            tracing::info!(%id, "lease rescoped ahead of the ledger commit");
            Some((l.holder, l.scope))
        }
        None => None,
    };
    if let Err(e) = ledger.update(id, &patch) {
        if let Some((holder, old)) = restore
            && let Err(r) = store.rescope(id, &holder, &old, store.config())
        {
            tracing::warn!(%id, error = %r, "restoring the lease after a failed update failed");
        }
        return Err(WidenError::Ledger(e.to_string()));
    }
    tracing::info!(%id, added = ?plan.add, "scope widened from the diff");
    Ok(plan)
}

/// The `check --ticket REF --widen` pre-step: open the repo at `root`, resolve `reference`, and apply the diff widen.
///
/// # Errors
///
/// [`WidenError`] when the repository, config, ticket or an update fails.
pub fn widen_ticket(
    root: &std::path::Path,
    reference: &str,
    explicit: Option<&str>,
    clock: std::sync::Arc<dyn gob_time::Clock>,
) -> Result<Absorb, WidenError> {
    let repo = gob_git::Repo::discover(root).map_err(|e| WidenError::Diff(e.to_string()))?;
    let cfg = frob_ledger::config::load_ledger_config(root).map_err(WidenError::Ledger)?;
    let ledger = Ledger::open(repo, cfg, clock.clone());
    let id = ledger
        .resolve(reference)
        .map_err(|e| WidenError::Ledger(format!("{reference}: {e}")))?;
    let lease_cfg =
        frob_lease::LeaseConfig::load(root).map_err(|e| WidenError::Ledger(e.to_string()))?;
    let (store, _) = frob_lease::open_store_in(ledger.repo(), lease_cfg, clock)?;
    let table =
        gob_check::CheckTable::load(root, "frob").map_err(|e| WidenError::Ledger(e.to_string()))?;
    apply_from_diff(&ledger, &store, id, explicit, &table.base)
}

/// [`widen_ticket`], logging each absorbed file and each file skipped because another lease holds it.
///
/// # Errors
///
/// As [`widen_ticket`].
pub fn widen_and_log(
    root: &std::path::Path,
    reference: &str,
    explicit: Option<&str>,
    clock: std::sync::Arc<dyn gob_time::Clock>,
) -> Result<Absorb, WidenError> {
    let plan = widen_ticket(root, reference, explicit, clock)?;
    for path in &plan.add {
        tracing::warn!(%path, "--widen: scope widened to this file");
    }
    for (path, other) in &plan.held {
        tracing::warn!(%path, %other, "--widen: not absorbed, held by another live lease");
    }
    Ok(plan)
}
