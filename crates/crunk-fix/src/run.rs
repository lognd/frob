//! Running a fix pass: check, collect, plan, apply.

use std::path::Path;

use gob_fix::{ApplyReport, Mode, Plan, Snapshot, Tier};
use gob_rules::Finding;
use gob_text::FileInterner;

use crate::collect::collect;

/// Why a fix pass failed.
#[derive(Debug, thiserror::Error)]
pub enum FixError {
    /// The check that finds the fixable sites failed.
    #[error("{0}")]
    Check(#[from] crunk_check::CheckError),
    /// A file could not be read, or written atomically.
    #[error("{0}")]
    Apply(#[from] gob_fix::FixError),
}

/// What one fix pass planned and did.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FixReport {
    /// The accepted and dropped fixes.
    pub plan: Plan,
    /// Per-file outcomes, diffs and the journal.
    pub applied: ApplyReport,
    /// Fixes refused because an edit was outside a stylesheet.
    pub skipped_non_stylesheet: usize,
    /// Whether nothing was written because this was a dry run.
    pub dry_run: bool,
}

/// Plan and apply the Tier A fixes of `findings` under `root`.
///
/// Files are snapshotted from disk now, so a file edited since the check that produced
/// `findings` is refused rather than corrupted.
///
/// # Errors
/// [`FixError::Apply`] on an unreadable or unwritable file.
pub fn apply_findings(
    root: &Path,
    findings: &[Finding],
    files: &FileInterner,
    dry_run: bool,
) -> Result<FixReport, FixError> {
    let collected = collect(findings, files);
    let mut snapshot = Snapshot::new();
    for fix in &collected.fixes {
        for edit in &fix.edits {
            if let Ok(bytes) = std::fs::read(root.join(&edit.path)) {
                snapshot.record(&edit.path, &bytes);
            }
        }
    }
    let plan = gob_fix::plan(collected.fixes, Tier::A);
    let mode = if dry_run { Mode::DryRun } else { Mode::Write };
    let applied = gob_fix::apply(&plan, root, &snapshot, mode)?;
    tracing::info!(
        accepted = plan.accepted.len(),
        dropped = plan.dropped.len(),
        files = applied.diffs.len(),
        dry_run,
        "crunk fix pass finished"
    );
    Ok(FixReport {
        plan,
        applied,
        skipped_non_stylesheet: collected.skipped_non_stylesheet,
        dry_run,
    })
}

/// Run `crunk check` for `root`, then apply (or with `dry_run` only diff) its Tier A fixes.
///
/// # Errors
/// [`FixError`] when the check or the apply fails.
pub fn run(root: &Path, dry_run: bool) -> Result<FixReport, FixError> {
    let run = crunk_check::run(root, &crunk_check::CheckOptions::default())?;
    apply_findings(root, &run.report.findings, &run.report.files, dry_run)
}
