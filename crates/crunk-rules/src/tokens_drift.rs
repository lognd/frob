//! TOKENS001's input: the generated token files on disk against what the spec renders now, one
//! message per file that is missing or drifted (port of the Python shell's `_tokens_drift_message`).
//!
//! The comparison reads the managed files (a side input outside the repository walk), so this is a
//! plain module the rule calls rather than a fact the host carries.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::DesignSpec;
use crunk_tokens::export::{self as drift, DriftReport, ExportError, Status};

use crate::sheets::site_path;

/// One file TOKENS001 reports: its project-relative path and the finding message.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DriftFinding {
    /// The managed file, relative to the project root with forward slashes.
    pub path: String,
    /// What is wrong and how to fix it.
    pub message: String,
}

/// The message for one non-clean file: a banner-only difference is named as such so nobody re-diffs
/// unchanged content.
pub fn drift_message(status: Status, banner_only: bool) -> String {
    if banner_only {
        "tokens file drifted; only the generated banner line differs and content is unchanged -- run `crunk tokens` to regenerate".to_owned()
    } else {
        format!(
            "tokens file {}; run `crunk tokens` to regenerate",
            status.word()
        )
    }
}

/// The findings of a [`DriftReport`], one per file that is not clean.
pub fn findings(spec: &DesignSpec, report: &DriftReport) -> Vec<DriftFinding> {
    report
        .dirty()
        .map(|file| DriftFinding {
            path: site_path(spec, &file.path),
            message: drift_message(file.status, file.banner_only),
        })
        .collect()
}

/// Compare the managed token files of `spec` with their renders.
///
/// # Errors
///
/// [`ExportError`] when the spec produces a colliding token name or a file cannot be read, in which
/// case drift is undecided.
pub fn check(spec: &DesignSpec) -> Result<Vec<DriftFinding>, ExportError> {
    let report = drift::check(spec)?;
    let found = findings(spec, &report);
    tracing::debug!(
        files = report.files.len(),
        drifted = found.len(),
        "tokens drift checked"
    );
    Ok(found)
}
