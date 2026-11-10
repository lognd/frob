//! Push this clone's claimed `ticket/<handle>` branches as WIP during `frob refresh` (`distributed-tickets.md` section 5.2 step 4).
//!
//! Pushing is what keeps a working holder visibly alive to other clones. It is a plain
//! compare-and-swap against the cached remote tip, so it can only fast-forward the remote
//! branch: a branch that is behind or diverged is reported and left alone, code is never
//! merged or forced.

// frob:ticket 01M7179W20SP4SF3GP0G32HAM7

use std::time::Duration;

use frob_lease::LeaseStore;
use frob_ledger::{Ledger, TicketId};
use gob_git::{RemoteRun, Repo};

use crate::claim::{cached_remote_claim, sync_settings};
use crate::error::WorktreeError;

/// What the WIP push did for one claim branch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WipOutcome {
    /// The remote branch was fast-forwarded to the local tip.
    Pushed,
    /// Local and remote tips are equal; nothing to push.
    UpToDate,
    /// The remote has no such branch in the cache; the claim republish owns creating it.
    NotPublished,
    /// The remote is ahead of this clone (pushed from elsewhere); never merged here.
    Behind,
    /// Both sides have commits the other lacks, or the remote moved since the last fetch; never merged or forced.
    Diverged,
    /// The push could not run or did not land; the text says why.
    Failed(String),
}

/// How a local tip relates to the cached remote tip.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Relation {
    Equal,
    Ahead,
    Behind,
    Diverged,
}

/// Push the claim branch of every live lease as WIP; returns `(branch, outcome)` per lease that has a local branch.
///
/// Best effort per claim: failures are outcomes and are logged, never errors.
///
/// # Errors
/// Lease or ledger read failures.
// frob:ticket 01M7179W20SP4SF3GP0G32HAM7
pub fn push_wip(
    ledger: &Ledger,
    leases: &LeaseStore,
) -> Result<Vec<(String, WipOutcome)>, WorktreeError> {
    let repo = ledger.repo();
    let (remote, timeout) = sync_settings(repo);
    let mut done = Vec::new();
    for lease in leases.live_snapshot()? {
        let Some(branch) = local_claim_branch(ledger, lease.ticket)? else {
            continue;
        };
        let outcome = push_branch(repo, &remote, &branch, timeout);
        tracing::info!(%branch, ?outcome, "WIP push of a claim branch");
        done.push((branch, outcome));
    }
    Ok(done)
}

/// Name the ticket's claim branch when it exists locally, else `None` (nothing to push).
fn local_claim_branch(ledger: &Ledger, ticket: TicketId) -> Result<Option<String>, WorktreeError> {
    let view = ledger.show(ticket)?;
    let branch = format!("ticket/{}", view.summary.handle.trim_start_matches('~'));
    if ledger
        .repo()
        .rev_parse(&format!("refs/heads/{branch}"))
        .is_err()
    {
        tracing::debug!(%branch, "no local claim branch; no WIP to push");
        return Ok(None);
    }
    Ok(Some(branch))
}

/// Push one local claim branch to `remote` when it is strictly ahead of the cached remote tip.
fn push_branch(repo: &Repo, remote: &str, branch: &str, timeout: Duration) -> WipOutcome {
    let local_ref = format!("refs/heads/{branch}");
    let Some(theirs) = cached_remote_claim(repo, remote, branch) else {
        return WipOutcome::NotPublished;
    };
    let Ok(ours) = repo.rev_parse(&local_ref).map(|o| o.to_string()) else {
        return WipOutcome::Failed("the local branch vanished".to_owned());
    };
    match relation(repo, &ours, &theirs) {
        Relation::Equal => WipOutcome::UpToDate,
        Relation::Behind => {
            tracing::warn!(branch, "claim branch is behind its remote copy; not pushed");
            WipOutcome::Behind
        }
        Relation::Diverged => {
            tracing::warn!(
                branch,
                "claim branch diverged from its remote copy; not pushed"
            );
            WipOutcome::Diverged
        }
        Relation::Ahead => {
            match repo.push_cas(remote, &local_ref, &local_ref, Some(&theirs), timeout) {
                Ok(RemoteRun::Done) => WipOutcome::Pushed,
                Ok(RemoteRun::Rejected(why)) => {
                    tracing::warn!(branch, %why, "remote claim branch moved; WIP not pushed");
                    WipOutcome::Diverged
                }
                Ok(other) => {
                    tracing::warn!(branch, outcome = ?other, "WIP push did not land");
                    WipOutcome::Failed(format!("{other:?}"))
                }
                Err(e) => {
                    tracing::warn!(branch, error = %e, "WIP push could not start");
                    WipOutcome::Failed(e.to_string())
                }
            }
        }
    }
}

/// Where `ours` stands against `theirs` by merge base; an unreadable history counts as diverged.
fn relation(repo: &Repo, ours: &str, theirs: &str) -> Relation {
    if ours == theirs {
        return Relation::Equal;
    }
    match repo.merge_base(ours, theirs) {
        Ok(Some(mb)) if mb == theirs => Relation::Ahead,
        Ok(Some(mb)) if mb == ours => Relation::Behind,
        Ok(_) => Relation::Diverged,
        Err(e) => {
            tracing::warn!(error = %e, "merge base lookup failed; treating as diverged");
            Relation::Diverged
        }
    }
}
