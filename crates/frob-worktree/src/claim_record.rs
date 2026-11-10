//! Recording a claim in the ledger (`distributed-tickets.md` section 3.3.2).
//!
//! After the claim branch push, `work` appends a `lease` event (`take`,
//! `move` or `renew`) naming the actor, this clone, the agent label, the
//! branch and the observed oid, then pushes the ledger. The push is best
//! effort: a failure leaves the event local for the next sync to push, so the
//! claim itself (the branch) is never undone by a ledger hiccup.

use std::fs;
use std::path::PathBuf;

use frob_ledger::claim_hold::{ClaimStamp, claim_event};
use frob_ledger::event::LeaseOp;
use frob_ledger::{EventId, Ledger, RefMode, TicketId};
use gob_git::{RemoteRun, Repo};

use crate::claim::{Publication, sync_settings};
use crate::error::WorktreeError;

/// File under `<common_dir>/frob/` holding this clone's id.
const CLONE_ID_FILE: &str = "clone-id";

/// Where this clone's id lives.
fn clone_id_path(repo: &Repo) -> PathBuf {
    repo.common_dir().join("frob").join(CLONE_ID_FILE)
}

/// This clone's stable id, minted and saved on first use; never derived from a path or host name.
///
/// When the id cannot be saved a fresh one is returned each call (logged), which only weakens the audit trail.
#[must_use]
pub fn clone_id(repo: &Repo) -> String {
    let path = clone_id_path(repo);
    if let Ok(text) = fs::read_to_string(&path) {
        let text = text.trim();
        if !text.is_empty() {
            return text.to_owned();
        }
    }
    let id = EventId::mint().to_string();
    let saved = path
        .parent()
        .map_or(Ok(()), fs::create_dir_all)
        .and_then(|()| fs::write(&path, format!("{id}\n")));
    match saved {
        Ok(()) => tracing::info!(clone_id = %id, "minted clone id"),
        Err(e) => tracing::warn!(error = %e, "could not save the clone id; using a one-off"),
    }
    id
}

/// Which lease op a publication outcome records, `None` when nothing was claimed (lost, or unpublished until a sync).
#[must_use]
pub fn op_for(published: &Publication) -> Option<LeaseOp> {
    match published {
        Publication::Published | Publication::LocalOnly => Some(LeaseOp::Take),
        Publication::Resumed => Some(LeaseOp::Renew),
        Publication::Moved { .. } => Some(LeaseOp::Move),
        Publication::Unpublished(_) | Publication::Lost { .. } => None,
    }
}

/// Everything the claim event needs besides the ledger: who, where and at which oid.
#[derive(Debug, Clone, Copy)]
pub struct Claimed<'a> {
    /// The ticket.
    pub id: TicketId,
    /// The claim branch name.
    pub branch: &'a str,
    /// The oid the branch was observed at.
    pub observed: &'a str,
    /// The `FROB_AGENT` label, `None` for a human.
    pub agent: Option<&'a str>,
}

/// Append the claim's `lease` event `op` and push the ledger; returns a warning when the push did not land.
///
/// # Errors
/// [`WorktreeError`] when the event cannot be appended or the actor is unknown.
// frob:ticket 01M5DBVSNP24G2WVGGSHP5YGDE
pub fn record(
    ledger: &Ledger,
    op: LeaseOp,
    claimed: &Claimed<'_>,
) -> Result<Option<String>, WorktreeError> {
    let actor = ledger.actor()?;
    let clone = clone_id(ledger.repo());
    let body = claim_event(
        op,
        &ClaimStamp {
            actor: &actor,
            clone_id: &clone,
            agent: claimed.agent,
            branch: claimed.branch,
            observed: claimed.observed,
        },
    );
    ledger.append(claimed.id, body)?;
    tracing::info!(ticket = %claimed.id, ?op, branch = claimed.branch, observed = claimed.observed, "claim recorded in the ledger");
    Ok(push_ledger(ledger))
}

/// Push the orphan ledger branch to the remote as a compare-and-swap against the last fetched tip.
///
/// Returns a warning when the push did not land (the event stays local and the next sync pushes it); `None` on
/// success, when no remote is configured, or when the ledger is not an orphan branch (it then rides the base).
#[must_use]
pub fn push_ledger(ledger: &Ledger) -> Option<String> {
    let cfg = ledger.config();
    if cfg.mode != RefMode::Orphan {
        tracing::debug!(mode = ?cfg.mode, "ledger is not an orphan branch; not pushed with the claim");
        return None;
    }
    let repo = ledger.repo();
    let (remote, timeout) = sync_settings(repo);
    if repo.remote_url(&remote).is_none() {
        tracing::debug!(remote, "no remote configured; ledger stays local");
        return None;
    }
    let ours = format!("refs/heads/{}", cfg.branch);
    let expected = repo
        .rev_parse(&format!("refs/remotes/{remote}/{}", cfg.branch))
        .ok()
        .map(|o| o.to_string());
    let run = match repo.push_cas(&remote, &ours, &ours, expected.as_deref(), timeout) {
        Ok(run) => run,
        Err(e) => {
            tracing::warn!(error = %e, "ledger push could not start");
            return Some(format!(
                "the ledger push could not start ({e}); a sync will push it"
            ));
        }
    };
    match run {
        RemoteRun::Done => {
            tracing::info!(remote, branch = %cfg.branch, "ledger pushed after the claim");
            None
        }
        other => {
            tracing::warn!(outcome = ?other, "ledger push after the claim did not land");
            Some("the claim event is recorded locally; a sync will push the ledger".to_owned())
        }
    }
}
