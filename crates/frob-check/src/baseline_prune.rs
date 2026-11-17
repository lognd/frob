//! Prune evidence and text pruning of `frob-baseline.toml`, shared by `frob baseline prune`, `frob land` and the baseline rules.
//!
//! A baseline key whose finding no longer occurs is dead weight, and a key the base tip no longer
//! lists must not survive a merge (docs/design/shared/rules.md section 6.1).

// frob:ticket 01M7KME88Y8N7JD506Y0WRG2MX

use std::collections::BTreeSet;

use gob_rules::{Baseline, BaselineError, PruneInput, PruneReport};

use crate::CheckReport;

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

    // frob:tests crates/frob-check/src/baseline_prune.rs::pruned_text
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

    // frob:tests crates/frob-check/src/baseline_prune.rs::pruned_text
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

    // frob:tests crates/frob-check/src/baseline_prune.rs::pruned_text
    #[test]
    fn keys_the_base_tip_dropped_do_not_survive_the_merge() {
        let head = file("DOC001", &[DEAD, LIVE]);
        let base = file("DOC001", &[LIVE]);
        let live = input(&[DEAD, LIVE], &["DOC001"], true);
        let (out, _) = pruned_text(&head, Some(&base), &live).unwrap().unwrap();
        assert!(out.contains(LIVE) && !out.contains(DEAD));
    }

    // frob:tests crates/frob-check/src/baseline_prune.rs::pruned_text
    #[test]
    fn conflict_markers_are_an_error_not_an_empty_baseline() {
        let text = "<<<<<<< HEAD\nversion = 1\n=======\n>>>>>>> base\n";
        assert!(pruned_text(text, None, &input(&[], &[], true)).is_err());
    }
}
