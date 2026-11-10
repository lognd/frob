//! The claim loser's flow (`distributed-tickets.md` section 3.3): park local commits, comment, report.
//!
//! When the create-only push of `ticket/<handle>` loses to another clone,
//! commits already on the local `ticket/<handle>` branch would be stranded.
//! They are pushed, never rewritten, to `parked/<handle>-<n>` (the next free
//! index on the remote), a `comment` event records the loss on the ticket, and
//! the message names the winner and the oid it holds.

// frob:ticket 01M5DBVTFBQCV375510SMKSNHT

use std::time::Duration;

use frob_ledger::event::{CommentData, EventBody};
use frob_ledger::model::CommentSubtype;
use frob_ledger::{Ledger, TicketId};
use gob_git::{RemoteProbe, RemoteRun, Repo};

use crate::claim::sync_settings;
use crate::error::WorktreeError;

/// How many times a parked push is retried at the next index after another loser took the same one.
const PARK_ATTEMPTS: u32 = 5;

/// What the loser knows about the lost claim.
#[derive(Debug, Clone, Copy)]
pub struct LostClaim<'a> {
    /// The ticket.
    pub id: TicketId,
    /// The ticket handle without the tilde.
    pub handle: &'a str,
    /// The claim branch name, `ticket/<handle>`.
    pub branch: &'a str,
    /// The base the claim would have started from.
    pub base: &'a str,
    /// The winner's oid on the remote.
    pub tip: &'a str,
}

/// The next free `parked/<handle>-<n>` index given the existing remote ref names (1 when none).
#[must_use]
pub fn next_index<S: AsRef<str>>(names: &[S], handle: &str) -> u32 {
    let prefix = format!("refs/heads/parked/{handle}-");
    names
        .iter()
        .filter_map(|n| n.as_ref().strip_prefix(&prefix)?.parse::<u32>().ok())
        .max()
        .map_or(1, |m| m + 1)
}

/// The existing `parked/<handle>-*` ref names on `remote`; empty when the remote did not answer.
fn parked_names(repo: &Repo, remote: &str, handle: &str, timeout: Duration) -> Vec<String> {
    let pattern = format!("refs/heads/parked/{handle}-*");
    match repo.ls_remote(remote, &[pattern], timeout) {
        Ok(RemoteProbe::Refs { refs, .. }) => refs.into_iter().map(|r| r.name).collect(),
        Ok(other) => {
            tracing::warn!(handle, outcome = ?other, "could not list parked refs");
            Vec::new()
        }
        Err(e) => {
            tracing::warn!(handle, error = %e, "could not list parked refs");
            Vec::new()
        }
    }
}

/// Run git in the work tree, `Some(trimmed stdout)` on success; failures are logged.
fn git_text(repo: &Repo, args: &[&str]) -> Option<String> {
    let cwd = repo.work_dir()?;
    match crate::gc::git::git(repo, cwd, args) {
        Ok((0, text)) => Some(text.trim().to_owned()),
        Ok((code, text)) => {
            tracing::warn!(code, args = %args.join(" "), text = %text.trim(), "git failed in the loss flow");
            None
        }
        Err(why) => {
            tracing::warn!(%why, "git could not run in the loss flow");
            None
        }
    }
}

/// Who authored the winner's tip, `None` when the tip is not readable here.
fn winner(repo: &Repo, tip: &str) -> Option<String> {
    git_text(repo, &["log", "-1", "--format=%an", tip]).filter(|a| !a.is_empty())
}

/// Whether the local claim branch holds commits beyond both the winner's tip and the base.
fn has_local_commits(repo: &Repo, lost: &LostClaim<'_>) -> bool {
    let local = format!("refs/heads/{}", lost.branch);
    if repo.rev_parse(&local).is_err() {
        return false;
    }
    let tip = format!("^{}", lost.tip);
    let base = format!("^{}", lost.base);
    git_text(repo, &["rev-list", "--count", &local, &tip, &base])
        .and_then(|n| n.parse::<u64>().ok())
        .is_some_and(|n| n > 0)
}

/// Push the local claim branch to the next free `parked/<handle>-<n>`; the ref name on success, `None` otherwise.
fn push_parked(
    repo: &Repo,
    lost: &LostClaim<'_>,
    remote: &str,
    timeout: Duration,
) -> Option<String> {
    let src = format!("refs/heads/{}", lost.branch);
    let mut n = next_index(
        &parked_names(repo, remote, lost.handle, timeout),
        lost.handle,
    );
    for _ in 0..PARK_ATTEMPTS {
        let name = format!("parked/{}-{n}", lost.handle);
        let dst = format!("refs/heads/{name}");
        match repo.push_cas(remote, &src, &dst, None, timeout) {
            Ok(RemoteRun::Done) => {
                tracing::info!(%name, "local commits parked");
                return Some(name);
            }
            Ok(RemoteRun::Rejected(_)) => {
                tracing::debug!(%name, "parked index taken; trying the next");
                n += 1;
            }
            Ok(other) => {
                tracing::warn!(%name, outcome = ?other, "could not park local commits");
                return None;
            }
            Err(e) => {
                tracing::warn!(%name, error = %e, "could not park local commits");
                return None;
            }
        }
    }
    tracing::warn!(handle = lost.handle, "no free parked index found");
    None
}

/// Build the loss report, parking local commits when there are any (best effort, logged).
fn park_and_report(repo: &Repo, lost: &LostClaim<'_>) -> String {
    let (remote, timeout) = sync_settings(repo);
    let who = winner(repo, lost.tip).unwrap_or_else(|| "another clone".to_owned());
    let mut report = format!("claim lost to {who} at {}", lost.tip);
    if !has_local_commits(repo, lost) {
        tracing::debug!(branch = lost.branch, "no local commits to park");
        return report;
    }
    match push_parked(repo, lost, &remote, timeout) {
        Some(name) => {
            report.push_str("; local commits parked at ");
            report.push_str(&name);
        }
        None => report.push_str("; local commits NOT parked (push failed), keep them"),
    }
    report
}

/// Run the loser flow: park local commits, comment on the ticket, push the ledger; returns the report text.
///
/// Parking and the ledger push are best effort (logged); the comment append is not.
///
/// # Errors
/// [`WorktreeError`] when the comment event cannot be appended.
pub fn handle_loss(ledger: &Ledger, lost: &LostClaim<'_>) -> Result<String, WorktreeError> {
    let report = park_and_report(ledger.repo(), lost);
    ledger.append(
        lost.id,
        EventBody::Comment(CommentData {
            subtype: CommentSubtype::Note,
            body: report.clone(),
        }),
    )?;
    tracing::warn!(ticket = %lost.id, %report, "claim loss recorded");
    if let Some(w) = crate::claim_record::push_ledger(ledger) {
        tracing::warn!(warning = %w, "ledger push after the loss did not land");
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-worktree/src/claim_park.rs::next_index
    #[test]
    fn next_index_starts_at_one_when_nothing_is_parked() {
        let none: [&str; 0] = [];
        assert_eq!(next_index(&none, "ab"), 1);
    }

    // frob:tests crates/frob-worktree/src/claim_park.rs::next_index
    #[test]
    fn next_index_follows_the_highest_taken() {
        let names = [
            "refs/heads/parked/ab-1",
            "refs/heads/parked/ab-3",
            "refs/heads/parked/other-9",
            "refs/heads/parked/ab-x",
        ];
        assert_eq!(next_index(&names, "ab"), 4);
    }
}
