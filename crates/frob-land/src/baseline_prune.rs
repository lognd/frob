//! Prune `frob-baseline.toml` against a full check run, shared by `frob baseline prune` and `frob land`.
//!
//! A baseline key whose finding no longer occurs is dead weight, and a key the base tip no longer
//! lists must not survive a merge (docs/design/shared/rules.md section 6.1). Land prunes on the merge tree, after
//! the base is merged and the full head check has run, and commits the result so the landed tree
//! carries the shrunken baseline.

// frob:ticket 01M66G70CZQMQ6Y55Y5QJPFKV3

use std::path::Path;

use frob_check::baseline_prune::{prune_input, pruned_text};
use frob_check::CheckOptions;
use frob_ledger::LedgerConfig;
use gob_git::Repo;
use gob_rules::{BASELINE_FILE, BaselineError, PruneInput, PruneReport};

use crate::candidate::Candidate;
use crate::error::{LandError, needs_action};
use crate::git::git;

/// Rule id of a baseline file that cannot be read.
const CODE_BASELINE: &str = "E-LAND-BASELINE";

/// Stage and commit the pruned baseline file on the merge tree.
fn commit_pruned(wt: &Repo, wt_path: &Path, removed: usize) -> Result<(), LandError> {
    stage_baseline(wt, wt_path)?;
    commit_staged(wt, wt_path, removed)
}

/// `git add` the baseline file on the merge tree.
fn stage_baseline(wt: &Repo, wt_path: &Path) -> Result<(), LandError> {
    let add = git(wt, wt_path, &["add", "--", BASELINE_FILE])?;
    if !add.ok() {
        return Err(LandError::Config(format!(
            "git add {BASELINE_FILE} failed: {}",
            add.text
        )));
    }
    Ok(())
}

/// Commit the staged baseline file, naming how many dead keys were pruned.
fn commit_staged(wt: &Repo, wt_path: &Path, removed: usize) -> Result<(), LandError> {
    let message = format!("chore(baseline): prune {removed} dead keys on land");
    let commit = git(
        wt,
        wt_path,
        &[
            "-c",
            "user.name=frob-land",
            "-c",
            "user.email=frob-land@localhost",
            "commit",
            "-m",
            &message,
        ],
    )?;
    if !commit.ok() {
        return Err(LandError::Config(format!(
            "committing the pruned {BASELINE_FILE} failed: {}",
            commit.text
        )));
    }
    Ok(())
}

/// The text of the baseline file at `base_oid`, or `None` when the base has none.
fn base_baseline_text(
    wt: &Repo,
    wt_path: &Path,
    base_oid: &str,
) -> Result<Option<String>, LandError> {
    let shown = git(
        wt,
        wt_path,
        &["show", &format!("{base_oid}:{BASELINE_FILE}")],
    )?;
    Ok(shown.ok().then_some(shown.text))
}

/// Prune the baseline of a land-train candidate: one full unscoped check of the candidate tree, then the merge-tree prune.
///
/// Skipped (no check run) when the candidate carries no baseline file. frob:ticket 01M66JP3Y9AHPNPNK5S9ZHTAS8
///
/// # Errors
///
/// The check cannot run, or the baseline cannot be pruned or committed.
pub fn prune_candidate(
    repo: &Repo,
    candidate: &mut Candidate,
    base_oid: &str,
    ledger: &LedgerConfig,
) -> Result<Option<PruneReport>, LandError> {
    let dir = candidate.checkout().to_path_buf();
    if !dir.join(BASELINE_FILE).is_file() {
        tracing::debug!("no baseline file on the train candidate; nothing to prune");
        return Ok(None);
    }
    crate::ratchet::isolate_build_dir(&dir);
    let head = frob_check::run(
        &dir,
        &CheckOptions {
            ledger: Some(ledger.clone()),
            skip_telemetry: true,
            skip_tools: true,
            ..CheckOptions::default()
        },
    )
    .map_err(|e| LandError::Config(e.to_string()))?;
    let pruned = candidate.prune_baseline(repo, base_oid, &prune_input(&head))?;
    tracing::info!(
        removed = pruned.as_ref().map_or(0, |r| r.removed.len()),
        "train candidate baseline prune done"
    );
    Ok(pruned)
}

/// Prune the baseline in the worktree against the merge-tree check `input` and commit the result; the report when it changed.
pub(crate) fn prune_on_merge_tree(
    wt: &Repo,
    wt_path: &Path,
    base_oid: &str,
    input: &PruneInput,
) -> Result<Option<PruneReport>, LandError> {
    let file = wt_path.join(BASELINE_FILE);
    let Ok(head_text) = std::fs::read_to_string(&file) else {
        tracing::debug!("no baseline file on the merge tree; nothing to prune");
        return Ok(None);
    };
    let base_text = base_baseline_text(wt, wt_path, base_oid)?;
    let refuse = |e: BaselineError| {
        needs_action(
            CODE_BASELINE,
            format!("{BASELINE_FILE} cannot be pruned on the merge tree: {e}"),
            format!("fix {BASELINE_FILE} (resolve merge markers), commit, then frob land again"),
        )
    };
    let Some((text, report)) =
        pruned_text(&head_text, base_text.as_deref(), input).map_err(refuse)?
    else {
        tracing::debug!("baseline already minimal on the merge tree");
        return Ok(None);
    };
    gob_fs::write_atomic(&file, text.as_bytes())
        .map_err(|e| LandError::io(format!("writing {BASELINE_FILE}"), e))?;
    commit_pruned(wt, wt_path, report.removed.len())?;
    tracing::info!(
        removed = report.removed.len(),
        tables_deleted = report.tables_deleted.len(),
        "baseline pruned on the merge tree"
    );
    Ok(Some(report))
}
