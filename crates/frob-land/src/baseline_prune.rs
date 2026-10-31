//! Prune `frob-baseline.toml` against a full check run, shared by `frob baseline prune` and `frob land`.
//!
//! A baseline key whose finding no longer occurs is dead weight, and a key the base tip no longer
//! lists must not survive a merge (rules.md section 6.1.2a). Land prunes on the merge tree, after
//! the base is merged and the full head check has run, and commits the result so the landed tree
//! carries the shrunken baseline.

// frob:ticket 01M66G70CZQMQ6Y55Y5QJPFKV3

use std::collections::BTreeSet;
use std::path::Path;

use frob_check::CheckReport;
use gob_git::Repo;
use gob_rules::{BASELINE_FILE, Baseline, BaselineError, PruneInput, PruneReport};

use crate::error::{LandError, needs_action};
use crate::git::git;

/// Rule id of a baseline file that cannot be read.
const CODE_BASELINE: &str = "E-LAND-BASELINE";

/// The prune evidence of one full, unscoped check run: every live fingerprint and every evaluated rule.
pub fn prune_input(report: &CheckReport) -> PruneInput {
    let live: BTreeSet<String> = report
        .findings
        .iter()
        .chain(report.suppressed.iter().map(|(f, _)| f))
        .map(|f| f.fingerprint.to_hex())
        .collect();
    let evaluated = report
        .subjects_examined
        .iter()
        .filter(|(_, n)| **n > 0)
        .map(|(rule, _)| rule.clone())
        .collect();
    PruneInput {
        live,
        evaluated,
        full_run: report.scope.is_none(),
    }
}

/// Prune `head_text` against the optional base-tip copy and `input`; `None` when nothing changed.
///
/// Keys the base tip no longer lists go first (a merge must not resurrect them), then keys
/// whose finding is gone. Returns the new file text and what the live-run prune removed.
///
/// # Errors
/// [`BaselineError`] when either text is not a readable baseline (conflict markers included).
pub fn pruned_text(
    head_text: &str,
    base_text: Option<&str>,
    input: &PruneInput,
) -> Result<Option<(String, PruneReport)>, BaselineError> {
    let mut baseline = Baseline::parse(head_text)?;
    if let Some(base) = base_text {
        baseline.intersect_base(&Baseline::parse(base)?);
    }
    let report = baseline.prune(input);
    let text = baseline.render();
    if text == Baseline::parse(head_text)?.render() {
        return Ok(None);
    }
    Ok(Some((text, report)))
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
    let shown = git(
        wt,
        wt_path,
        &["show", &format!("{base_oid}:{BASELINE_FILE}")],
    )?;
    let base_text = shown.ok().then_some(shown.text);
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
    let add = git(wt, wt_path, &["add", "--", BASELINE_FILE])?;
    if !add.ok() {
        return Err(LandError::Config(format!(
            "git add {BASELINE_FILE} failed: {}",
            add.text
        )));
    }
    let message = format!(
        "chore(baseline): prune {} dead keys on land",
        report.removed.len()
    );
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
    tracing::info!(
        removed = report.removed.len(),
        tables_deleted = report.tables_deleted.len(),
        "baseline pruned on the merge tree"
    );
    Ok(Some(report))
}

#[cfg(test)]
mod tests {
    use super::*;

    const DEAD: &str = "0000000000000000000000000000000000000000000000000000000000000000";
    const LIVE: &str = "1111111111111111111111111111111111111111111111111111111111111111";

    fn file(rule: &str, keys: &[&str]) -> String {
        let list: Vec<String> = keys.iter().map(|k| format!("\"{k}\"")).collect();
        format!(
            "version = 1\n\n[rules.{rule}]\nreason = \"r\"\nticket = \"~T1\"\nfindings = [{}]\n",
            list.join(", ")
        )
    }

    fn input(live: &[&str], evaluated: &[&str], full_run: bool) -> PruneInput {
        PruneInput {
            live: live.iter().map(|s| (*s).to_owned()).collect(),
            evaluated: evaluated.iter().map(|s| (*s).to_owned()).collect(),
            full_run,
        }
    }

    // frob:tests crates/frob-land/src/baseline_prune.rs::pruned_text
    #[test]
    fn a_dead_key_is_removed_and_an_emptied_table_deleted() {
        let text = file("DOC001", &[DEAD, LIVE]);
        let (out, report) = pruned_text(&text, None, &input(&[LIVE], &["DOC001"], true))
            .unwrap()
            .unwrap();
        assert_eq!(report.removed.len(), 1);
        assert!(out.contains(LIVE) && !out.contains(DEAD));
        let (out, report) = pruned_text(&text, None, &input(&[], &["DOC001"], true))
            .unwrap()
            .unwrap();
        assert_eq!(report.tables_deleted, vec!["DOC001".to_owned()]);
        assert!(!out.contains("DOC001"));
    }

    // frob:tests crates/frob-land/src/baseline_prune.rs::pruned_text
    #[test]
    fn a_partial_run_or_an_unevaluated_rule_prunes_nothing() {
        let text = file("DOC001", &[DEAD]);
        assert!(
            pruned_text(&text, None, &input(&[], &["DOC001"], false))
                .unwrap()
                .is_none()
        );
        assert!(
            pruned_text(&text, None, &input(&[], &["OTHER01"], true))
                .unwrap()
                .is_none()
        );
    }

    // frob:tests crates/frob-land/src/baseline_prune.rs::pruned_text
    #[test]
    fn keys_the_base_tip_dropped_do_not_survive_the_merge() {
        let head = file("DOC001", &[DEAD, LIVE]);
        let base = file("DOC001", &[LIVE]);
        let live = input(&[DEAD, LIVE], &["DOC001"], true);
        let (out, _) = pruned_text(&head, Some(&base), &live).unwrap().unwrap();
        assert!(out.contains(LIVE) && !out.contains(DEAD));
    }

    // frob:tests crates/frob-land/src/baseline_prune.rs::pruned_text
    #[test]
    fn conflict_markers_are_an_error_not_an_empty_baseline() {
        let text = "<<<<<<< HEAD\nversion = 1\n=======\n>>>>>>> base\n";
        assert!(pruned_text(text, None, &input(&[], &[], true)).is_err());
    }
}
