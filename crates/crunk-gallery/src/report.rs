//! The `gallery check` report: every rule's findings plus counts (`crunk-gallery-check-v1.json`).

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

use crunk_spec::{DesignSpec, Severity};
use gob_time::Day;
use serde::Serialize;

use crate::cells::{Cell, enumerate};
use crate::manifest::Manifest;
use crate::rules::{Finding, check_cells, check_routes};

/// The result of checking a gallery.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CheckReport {
    /// Report schema version (always 1).
    pub version: u32,
    /// Cells the spec enumerates.
    pub cells: usize,
    /// Findings at `error`.
    pub errors: usize,
    /// Findings at `warn`.
    pub warnings: usize,
    /// All findings, cell rules first, then routes.
    pub findings: Vec<Finding>,
}

impl CheckReport {
    /// True when no finding is an error.
    #[must_use]
    pub fn passed(&self) -> bool {
        self.errors == 0
    }
}

/// Count `findings` over `cells` into a report.
fn tally(cells: &[Cell], findings: Vec<Finding>) -> CheckReport {
    let count = |s: Severity| findings.iter().filter(|f| f.severity == s).count();
    CheckReport {
        version: 1,
        cells: cells.len(),
        errors: count(Severity::Error),
        warnings: count(Severity::Warn),
        findings,
    }
}

/// Run GALLERY001 to GALLERY005 for `spec` against `manifest`, as of `today`, with the router's `routes`.
pub fn check_report(
    spec: &DesignSpec,
    manifest: &Manifest,
    routes: &[String],
    today: Day,
) -> CheckReport {
    let cells = enumerate(spec);
    let mut findings = check_cells(spec, &cells, manifest, today);
    findings.extend(check_routes(spec, routes));
    let report = tally(&cells, findings);
    tracing::info!(
        cells = report.cells,
        errors = report.errors,
        warnings = report.warnings,
        "gallery checked"
    );
    report
}
