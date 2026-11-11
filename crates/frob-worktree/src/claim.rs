//! Publishing the claim: the create-only push of `ticket/<handle>` that `frob work` makes (`distributed-tickets.md` section 3.3).
//!
//! The branch's existence on the remote IS the claim. The push is a
//! compare-and-swap against "absent", so exactly one clone wins; the rest see
//! their push rejected and read the winner's tip. Offline is not an error
//! (decision D-5): the claim stays unpublished, `work` warns and proceeds.

// frob:ticket 01M5CW04QCRZ860BZMT46BECG2
// frob:ticket 01M5DBVTCDGK4Z096B1ZXVW75J

use std::time::Duration;

use frob_lease::LeaseStore;
use frob_ledger::Ledger;
use frob_ledger::config::SyncTable;
use gob_git::{RemoteProbe, RemoteRun, Repo};

use crate::error::WorktreeError;

/// Warning code when the claim could not be published.
pub const W_CLAIM_UNPUBLISHED: &str = "W-CLAIM-UNPUBLISHED";

/// Refusal code when another clone's create-only push won the claim.
pub const E_CLAIM_LOST: &str = "E-CLAIM-LOST";

/// Where `work` stands with the remote after trying to publish its claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Publication {
    /// The remote has no usable remote configured; the claim is local only.
    LocalOnly,
    /// The create-only push succeeded: this clone holds the claim.
    Published,
    /// The branch already exists on the remote at an oid this clone holds: a resume of its own claim.
    Resumed,
    /// The remote branch was made by the same actor on another clone; it was fetched and the claim moves here.
    Moved {
        /// Oid of `ticket/<handle>` on the remote, now also the local branch tip.
        tip: String,
    },
    /// The remote could not be reached; the claim is unpublished and a later sync publishes it.
    Unpublished(String),
    /// Another clone's push won; `tip` is the winner's oid.
    Lost {
        /// Oid of `ticket/<handle>` on the remote.
        tip: String,
    },
}

/// The remote name and probe timeout from `[sync]` in the repository's `frob.toml` (defaults when absent).
pub(crate) fn sync_settings(repo: &Repo) -> (String, Duration) {
    let table = repo
        .work_dir()
        .and_then(|root| gob_config::load::<SyncTable>(root, "frob").ok())
        .map(|l| l.value);
    table.map_or_else(
        || ("origin".to_owned(), Duration::from_millis(2500)),
        |t| {
            (
                t.remote,
                Duration::from_millis(u64::from(t.probe_timeout_ms)),
            )
        },
    )
}

/// The oid of `refs/heads/<branch>` on `remote`, `Ok(None)` when absent, `Err(text)` when the remote did not answer.
///
/// This is the unrecorded-claim probe: a branch on the remote with no ledger event is still a claim.
///
/// # Errors
/// [`WorktreeError::Git`] when git cannot be started.
pub fn remote_claim(
    repo: &Repo,
    remote: &str,
    branch: &str,
    timeout: Duration,
) -> Result<Result<Option<String>, String>, WorktreeError> {
    let name = format!("refs/heads/{branch}");
    let probe = repo.ls_remote(remote, std::slice::from_ref(&name), timeout)?;
    Ok(match probe {
        RemoteProbe::Refs { refs, .. } => {
            Ok(refs.into_iter().find(|r| r.name == name).map(|r| r.oid))
        }
        RemoteProbe::TimedOut => Err("the remote timed out".to_owned()),
        RemoteProbe::Failed { text, .. } => Err(text.trim().to_owned()),
    })
}

/// The cached oid of `refs/remotes/<remote>/<branch>`, `None` when this clone has not fetched that claim branch; never touches the network.
///
/// This is the offline form of [`remote_claim`] that read verbs use: it sees only what the last sync fetched.
// frob:ticket 01M5DBVT9HH0MRR30JVCJZYRTY
pub fn cached_remote_claim(repo: &Repo, remote: &str, branch: &str) -> Option<String> {
    let tip = repo
        .rev_parse(&format!("refs/remotes/{remote}/{branch}"))
        .ok()
        .map(|o| o.to_string());
    tracing::debug!(
        remote,
        branch,
        claimed = tip.is_some(),
        "cached claim lookup"
    );
    tip
}

/// Push `src` (a ref or oid) to `refs/heads/<branch>` on the configured remote, create-only.
///
/// `src` must be what the worktree branch starts from, so the remote branch and
/// the local one agree. A rejected push is classified: the remote tip being
/// `src` itself, or an ancestor of the local `<branch>`, is a resume of this
/// clone's own claim. Otherwise the branch is fetched and, when its tip was
/// authored by `actor`, the claim moves here ([`Publication::Moved`]); anything
/// else is [`Publication::Lost`].
///
/// # Errors
/// [`WorktreeError::Git`] when git cannot be started or `src` does not resolve.
pub fn publish(
    repo: &Repo,
    branch: &str,
    src: &str,
    actor: &str,
) -> Result<Publication, WorktreeError> {
    let (remote, timeout) = sync_settings(repo);
    if repo.remote_url(&remote).is_none() {
        tracing::debug!(branch, remote, "no remote configured; claim stays local");
        return Ok(Publication::LocalOnly);
    }
    let dst = format!("refs/heads/{branch}");
    let oid = repo.rev_parse(src)?.to_string();
    let run = repo.push_cas(&remote, &oid, &dst, None, timeout)?;
    match run {
        RemoteRun::Done => {
            tracing::info!(branch, remote, %oid, "claim published");
            Ok(Publication::Published)
        }
        RemoteRun::Rejected(_) => classify_rejection(repo, (&remote, branch, &oid), actor, timeout),
        RemoteRun::TimedOut => Ok(unpublished(branch, "the push timed out".to_owned())),
        RemoteRun::Failed { text, .. } => Ok(unpublished(branch, text.trim().to_owned())),
    }
}

/// Decide whether a rejected create-only push means the claim is ours already or lost.
fn classify_rejection(
    repo: &Repo,
    (remote, branch, oid): (&str, &str, &str),
    actor: &str,
    timeout: Duration,
) -> Result<Publication, WorktreeError> {
    let tip = match remote_claim(repo, remote, branch, timeout)? {
        Ok(Some(tip)) => tip,
        Ok(None) => return Ok(unpublished(branch, "the push was rejected".to_owned())),
        Err(why) => return Ok(unpublished(branch, why)),
    };
    let local = repo
        .rev_parse(&format!("refs/heads/{branch}"))
        .ok()
        .map(|o| o.to_string());
    let ours = tip == oid
        || local.is_some_and(|l| {
            repo.merge_base(&tip, &l)
                .ok()
                .flatten()
                .is_some_and(|mb| mb == tip)
        });
    if ours {
        tracing::info!(branch, %tip, "claim already on the remote at our history; resuming");
        Ok(Publication::Resumed)
    } else if moved_by(repo, (remote, branch, &tip), actor, timeout)? {
        tracing::info!(branch, %tip, actor, "claim made by this actor on another clone; moving it here");
        Ok(Publication::Moved { tip })
    } else {
        tracing::warn!(branch, %tip, "claim lost: the remote branch is not ours");
        Ok(Publication::Lost { tip })
    }
}

/// Fetch `branch` from `remote` and report whether its tip at `tip` was authored or committed by `actor`; on a match the local branch is created at `tip` when absent.
///
/// A failed fetch or an unreadable author is "not the same actor": the claim stays [`Publication::Lost`].
// frob:ticket 01M5DBVTCDGK4Z096B1ZXVW75J
fn moved_by(
    repo: &Repo,
    (remote, branch, tip): (&str, &str, &str),
    actor: &str,
    timeout: Duration,
) -> Result<bool, WorktreeError> {
    let spec = format!("+refs/heads/{branch}:refs/remotes/{remote}/{branch}");
    match repo.fetch_refs(remote, &[spec], timeout)? {
        RemoteRun::Done => {}
        other => {
            tracing::warn!(branch, outcome = ?other, "could not fetch the remote claim branch");
            return Ok(false);
        }
    }
    let Some(cwd) = repo.work_dir() else {
        return Ok(false);
    };
    let authors = match crate::gc::git::git(repo, cwd, &["log", "-1", "--format=%an%n%cn", tip]) {
        Ok((0, text)) => text,
        Ok((code, text)) => {
            tracing::warn!(branch, code, text = %text.trim(), "could not read the claim tip author");
            return Ok(false);
        }
        Err(why) => {
            tracing::warn!(branch, %why, "could not read the claim tip author");
            return Ok(false);
        }
    };
    if !authors.lines().any(|l| l.trim() == actor) {
        tracing::debug!(branch, actor, "claim tip is not by this actor");
        return Ok(false);
    }
    let local = format!("refs/heads/{branch}");
    if repo.rev_parse(&local).is_err() {
        let oid = repo.rev_parse(tip)?;
        repo.update_ref_cas(&local, None, oid, "frob work: resume claim from remote")?;
        tracing::info!(branch, %tip, "local claim branch created from the remote");
    }
    Ok(true)
}

/// Retry the create-only push for each live lease whose `ticket/<handle>` branch exists here but not on the remote; returns how many claims reached the remote.
///
/// This is the sync half of `W-CLAIM-UNPUBLISHED`: `work` proceeded offline,
/// and the next `frob refresh` publishes the branch. Best effort per claim; a
/// lost claim is logged, never published over.
///
/// # Errors
/// Lease or ledger read failures.
// frob:ticket 01M5DBVT9HH0MRR30JVCJZYRTY
pub fn republish_unpublished(ledger: &Ledger, leases: &LeaseStore) -> Result<usize, WorktreeError> {
    let repo = ledger.repo();
    let (remote, _) = sync_settings(repo);
    let actor = ledger.actor()?;
    let mut published = 0;
    for lease in leases.live_snapshot()? {
        let view = ledger.show(lease.ticket)?;
        let branch = format!("ticket/{}", view.summary.handle.trim_start_matches('~'));
        let local = format!("refs/heads/{branch}");
        if repo.rev_parse(&local).is_err() {
            tracing::debug!(%branch, "no local claim branch; nothing to republish");
            continue;
        }
        if cached_remote_claim(repo, &remote, &branch).is_some() {
            continue;
        }
        match publish(repo, &branch, &local, &actor)? {
            Publication::Published => {
                tracing::info!(%branch, "unpublished claim now on the remote");
                published += 1;
            }
            other => tracing::debug!(%branch, outcome = ?other, "claim republish did not publish"),
        }
    }
    Ok(published)
}

/// An offline outcome, logged.
fn unpublished(branch: &str, why: String) -> Publication {
    tracing::warn!(branch, why = %why, "claim not published");
    Publication::Unpublished(why)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-worktree/src/claim.rs::unpublished
    #[test]
    fn unpublished_keeps_the_reason() {
        assert_eq!(
            unpublished("ticket/x", "offline".to_owned()),
            Publication::Unpublished("offline".to_owned())
        );
    }
}
