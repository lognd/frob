//! Feed claim activity observation from `frob refresh` (`distributed-tickets.md` section 4.2).
//!
//! Every sync fetches the claim branch of each live lease and folds its new
//! commits and the holder's ledger events into `claims-observed.toml`, so
//! `idle_secs` has data without waiting for a `claim evict`.

// frob:ticket 01M5DDB4ZTR3ZWPJNCMJHN764G

use frob_lease::LeaseStore;
use frob_ledger::Ledger;

use crate::activity::{DEFAULT_BOT_IDENTITIES, ObservedClaims, commit_facts, observed_path};
use crate::claim::sync_settings;
use crate::error::WorktreeError;
use crate::next::fetch_claim_tip;

/// Fetch each live claim branch and record new activity at `now`; returns how many claims recorded something new.
///
/// Best effort per claim: an unreachable remote, a missing branch or a failed
/// walk is logged and skipped. The observation file is saved only when
/// something changed.
///
/// # Errors
/// Lease or ledger read failures.
// frob:ticket 01M5DDB4ZTR3ZWPJNCMJHN764G
pub fn observe_live_claims(
    ledger: &Ledger,
    leases: &LeaseStore,
    now: i64,
) -> Result<usize, WorktreeError> {
    let repo = ledger.repo();
    let (remote, timeout) = sync_settings(repo);
    let path = observed_path(repo);
    let mut observed = ObservedClaims::load(&path);
    let bots: Vec<String> = DEFAULT_BOT_IDENTITIES
        .iter()
        .map(|s| (*s).to_owned())
        .collect();
    let mut recorded = 0;
    let mut dirty = false;
    for lease in leases.live_snapshot()? {
        let id = lease.ticket;
        let key = id.to_string();
        let view = ledger.show(id)?;
        let bare = view.summary.handle.trim_start_matches('~').to_owned();
        let branch = format!("ticket/{bare}");
        match fetch_claim_tip(repo, &remote, &branch, timeout) {
            Ok(true) => {}
            Ok(false) => {
                tracing::debug!(%branch, "claim branch not fetched; skipping observation");
                continue;
            }
            Err(e) => {
                tracing::warn!(%branch, error = %e, "claim fetch failed; skipping observation");
                continue;
            }
        }
        let Ok(tip) = repo.rev_parse(&format!("refs/remotes/{remote}/{branch}")) else {
            tracing::debug!(%branch, "no tracking ref after fetch");
            continue;
        };
        let tip = tip.to_string();
        let since = observed.claims.get(&key).and_then(|c| c.tip.clone());
        let commits = match commit_facts(repo, &tip, since.as_deref()) {
            Ok(c) => c,
            Err(e) => {
                tracing::warn!(%branch, error = %e, "claim walk failed; skipping observation");
                continue;
            }
        };
        let before = observed.claims.get(&key).cloned();
        observed.observe_tip(&key, &tip, &commits, &bots, now);
        for event in &ledger.events(id)? {
            observed.observe_event(&key, event, &lease.holder.actor, now);
        }
        if observed.claims.get(&key) != before.as_ref() {
            dirty = true;
            recorded += 1;
        }
    }
    if dirty && let Err(e) = observed.save(&path) {
        tracing::warn!(error = %e, "could not save the observation file");
    }
    tracing::info!(recorded, "claim activity observed during sync");
    Ok(recorded)
}
