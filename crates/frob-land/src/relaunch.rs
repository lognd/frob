//! `frob land --relaunch`: carry a locally landed ticket's kept branch onto the remote base (distributed-tickets.md row 52).
//!
//! After weeks offline the local base holds lands that origin never saw and
//! origin's base moved on. frob never rebases and never rewrites the local base:
//! the kept ticket branch gets `<remote>/<base>` merged in (in a throwaway
//! worktree) so its tip descends from origin's base and can be checked and
//! pushed or proposed. The recorded `land` event is left as it is.

use std::path::Path;
use std::sync::Arc;

use frob_check::CheckOptions;
use frob_ledger::config::SyncTable;
use frob_ledger::event::EventBody;
use frob_ledger::model::Category;
use gob_git::Repo;
use gob_time::Clock;

use crate::error::{LandError, needs_action};
use crate::git::git;
use crate::land::{begin, blank_outcome, merge_base_in};
use crate::plan::{LandOptions, LandOutcome};

/// The remote whose base the relaunch targets: `[sync] remote` of `frob.toml`, `origin` when unset or unreadable.
fn sync_remote(root: &Path) -> String {
    match gob_config::load::<SyncTable>(root, "frob") {
        Ok(l) => l.value.remote,
        Err(e) => {
            tracing::warn!(error = %e, "[sync] unreadable; relaunching against origin");
            SyncTable::default().remote
        }
    }
}

/// The remote-tracking ref of `base` on `remote`.
fn remote_base_ref(remote: &str, base: &str) -> String {
    format!("refs/remotes/{remote}/{base}")
}

/// Short branch name of a recorded `branch` (a `land` event may carry the full ref).
fn short_branch(recorded: &str) -> &str {
    recorded.strip_prefix("refs/heads/").unwrap_or(recorded)
}

/// Where the merge starts and the expected old tip of `branch`; a branch land cleanup collected is recreated at the land commit (compare-and-swap against "absent").
fn kept_branch_start(
    repo: &Repo,
    branch: &str,
    land_commit: &str,
    out: &mut LandOutcome,
) -> (String, String) {
    if let Ok(tip) = repo.rev_parse(&format!("refs/heads/{branch}")) {
        return (branch.to_owned(), tip.to_string());
    }
    tracing::info!(ticket = %out.id, branch, "kept branch is gone; recreating it at the land commit");
    out.warnings.push(format!(
        "{branch} was gone; recreated at the land commit {land_commit}"
    ));
    (land_commit.to_owned(), "0".repeat(40))
}

// frob:ticket 01M5CW05WX0TMSBKDFTPEHB5R3
/// Merge the remote base into the kept branch (recreated at the land commit if collected) of an already-landed ticket; nothing is published.
///
/// # Errors
///
/// `E-RELAUNCH-NOT-LANDED`, `E-RELAUNCH-NO-REMOTE`,
/// `E-LAND-CONFLICT` (merge aborted), plus ledger and git failures.
pub fn relaunch(
    root: &Path,
    opts: &LandOptions,
    clock: &Arc<dyn Clock>,
) -> Result<LandOutcome, LandError> {
    let b = begin(root, opts, clock)?;
    let (repo, handle, base) = (&b.repo, &b.handle, &b.base);
    tracing::info!(ticket = %b.id, base = %base, dry_run = opts.dry_run, "relaunch started");
    let mut out = blank_outcome(b.id, handle, base, opts);

    let landed = b
        .here
        .ledger
        .events(b.id)?
        .into_iter()
        .rev()
        .find_map(|e| match e.body {
            EventBody::Land(d) => Some(d),
            _ => None,
        });
    let Some(landed) = landed.filter(|_| b.view.summary.category == Category::Done) else {
        return Err(needs_action(
            "E-RELAUNCH-NOT-LANDED",
            format!("{handle} has no local land to relaunch"),
            format!("frob land {handle}"),
        ));
    };
    let remote_name = sync_remote(&b.cwd_root);
    let remote = remote_base_ref(&remote_name, base);
    let remote_oid = repo.rev_parse(&remote).map_err(|_| {
        needs_action(
            "E-RELAUNCH-NO-REMOTE",
            format!("no remote-tracking ref {remote}"),
            "frob refresh",
        )
    })?;
    let commit = repo.rev_parse(&landed.commit)?;
    if repo.merge_base(&landed.commit, &remote)? == Some(commit) {
        tracing::info!(ticket = %b.id, "land commit already on the remote base");
        out.already = true;
        out.commit = Some(landed.commit);
        return Ok(out);
    }
    let branch = short_branch(&landed.branch).to_owned();
    let (start, old) = kept_branch_start(repo, &branch, &landed.commit, &mut out);
    out.branch = Some(branch.clone());
    out.plan = vec![
        format!("merge {remote} into {branch}"),
        if opts.push {
            format!("then: frob check, git push {remote_name} {branch}:{base} when it is clean")
        } else {
            format!(
                "then: frob check, git push {remote_name} {branch}:{base} (or rerun with --push)"
            )
        },
    ];
    if opts.dry_run {
        return Ok(out);
    }

    let tmp = repo
        .common_dir()
        .join("frob")
        .join("relaunch")
        .join(handle.trim_start_matches('~'));
    let tmp_s = gob_path::Shown::with_home(&tmp, None).to_string();
    let primary = &b.cwd_root;
    let _ = git(repo, primary, &["worktree", "remove", "--force", &tmp_s]);
    let added = git(
        repo,
        primary,
        &["worktree", "add", "--detach", &tmp_s, &start],
    )?;
    if !added.ok() {
        return Err(LandError::Config(format!(
            "worktree add failed: {}",
            added.text
        )));
    }
    let merged = relaunch_in(repo, &tmp, &tmp_s, &remote, &branch, &old, handle);
    // The check runs on the merged tree, before the throwaway worktree goes away.
    let gate = match (&merged, opts.push) {
        (Ok(_), true) => Some(check_merged(&tmp, &b.here)),
        _ => None,
    };
    let removed = git(repo, primary, &["worktree", "remove", "--force", &tmp_s]);
    if !removed.as_ref().is_ok_and(crate::git::GitRun::ok) {
        out.warnings
            .push(format!("temporary worktree {tmp_s} was not removed"));
    }
    let (how, tip) = merged?;
    tracing::info!(ticket = %b.id, how = %how, tip = %tip, "relaunch merged the remote base");
    out.base_merge = Some(how);
    out.commit = Some(tip);
    match gate {
        None => out.warnings.push(format!(
            "{branch} now contains {remote_oid}; check it, then push {branch}:{base} to {remote_name} (or rerun with --push)"
        )),
        Some(Err(e)) => return Err(e),
        Some(Ok(false)) => out.warnings.push(format!(
            "{branch} now contains {remote_oid} but the check is red; fix it, then push {branch}:{base} to {remote_name}"
        )),
        Some(Ok(true)) => push_branch(repo, &remote_name, &branch, base, &mut out),
    }
    Ok(out)
}

/// Run the whole-tree check on the merged worktree `tmp`; true when nothing reaches the fail threshold.
fn check_merged(tmp: &Path, here: &frob_evidence::Workspace) -> Result<bool, LandError> {
    let report = frob_check::run(
        tmp,
        &CheckOptions {
            ledger: Some(here.ledger.config().clone()),
            clock: Some(here.ledger.clock().clone()),
            skip_telemetry: true,
            ..CheckOptions::default()
        },
    )?;
    let clean = report.exit_code() == gob_diagnostics::ExitCode::Ok;
    tracing::info!(clean, findings = report.findings.len(), "relaunch check");
    Ok(clean)
}

/// Push `branch` to `<remote>/<base>` (plain, never forced); a refusal is a warning, the merge stands.
fn push_branch(repo: &Repo, remote: &str, branch: &str, base: &str, out: &mut LandOutcome) {
    match repo.push(remote, &format!("refs/heads/{branch}:refs/heads/{base}")) {
        Ok(()) => {
            tracing::info!(remote, branch, base, "relaunched branch pushed");
            out.pushed = true;
        }
        Err(e) => {
            tracing::warn!(error = %e, "relaunch push failed");
            out.warnings.push(format!(
                "the check is clean but the push failed: {e}; run `git push {remote} {branch}:{base}`"
            ));
        }
    }
}

/// Merge `remote` in the throwaway worktree `tmp`, then move `branch` from `old` to the result (compare-and-swap).
fn relaunch_in(
    repo: &Repo,
    tmp: &Path,
    tmp_s: &str,
    remote: &str,
    branch: &str,
    old: &str,
    handle: &str,
) -> Result<(String, String), LandError> {
    let wt = Repo::discover(tmp).map_err(|e| LandError::Config(e.to_string()))?;
    let how = merge_base_in(&wt, tmp, remote, handle)?;
    let tip = wt.rev_parse("HEAD")?.to_string();
    let r = git(
        repo,
        tmp,
        &["update-ref", &format!("refs/heads/{branch}"), &tip, old],
    )?;
    if !r.ok() {
        return Err(LandError::Config(format!(
            "could not move {branch} (it changed during the relaunch; {tmp_s}): {}",
            r.text
        )));
    }
    Ok((how, tip))
}
