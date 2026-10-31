//! The TIME pass: scan the walked files and return every verdict as a [`PathFinding`].
//!
//! TIME findings share the PATH finding and report shapes: the product converts both the same way.

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

use std::collections::BTreeSet;

use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::pass::{PathFile, PathFinding, PathReport};
use crate::time::{self, Kind};

/// Rule id of the local clock read rule.
pub const TIME001: &str = "TIME001";
/// Rule id of the naive and aware mix rule.
pub const TIME002: &str = "TIME002";

/// One TIME verdict before the product interns its span.
pub type TimeFinding = PathFinding;
/// What the TIME pass found and examined.
pub type TimeReport = PathReport;

/// The message of a kind.
fn describe(kind: Kind) -> &'static str {
    match kind {
        Kind::LocalClockRead => {
            "local-zone or zone-less clock read that is stored or sent; read the clock in UTC (tz-aware) instead"
        }
        Kind::NaiveAwareMix => {
            "naive and timezone-aware datetimes compared or subtracted; make both aware before mixing"
        }
    }
}

/// The severity both TIME rules report at.
const SEVERITY: Severity = Severity::Error;

/// Run `TIME001` and `TIME002` over `files`.
pub fn analyze(files: &[PathFile<'_>]) -> TimeReport {
    let mut report = TimeReport::default();
    let mut examined = 0usize;
    let mut undecided: BTreeSet<(Kind, &'static str)> = BTreeSet::new();
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Result<time::Report, time::ScanError>> = files
        .par_iter()
        .map(|f| time::scan(f.language, f.text))
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let scanned = match scanned {
            Ok(r) => r,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "time scan skipped an unparsable file");
                continue;
            }
        };
        if time::has_clock_roles(f.language) {
            examined += 1;
        }
        let lines: Vec<&str> = if scanned.sites.is_empty() {
            Vec::new()
        } else {
            f.text.lines().collect()
        };
        for site in &scanned.sites {
            let range = (
                u32::from(site.range.start()) as usize,
                u32::from(site.range.end()) as usize,
            );
            let line_text = lines
                .get(site.line.saturating_sub(1))
                .copied()
                .unwrap_or("");
            report.findings.push(TimeFinding {
                rule: site.kind.rule_id(),
                severity: SEVERITY,
                file: f.path.to_owned(),
                range,
                message: describe(site.kind).to_owned(),
                reason: None,
                anchor: format!("{}:{}", f.path, line_text.trim()),
            });
        }
        if !scanned.unresolved.is_empty() && !unresolvable(f.language) {
            continue;
        }
        for kind in &scanned.unresolved {
            // One Unresolved verdict per rule and language, at the first file, not one per file.
            if !undecided.insert((*kind, f.language.name())) {
                continue;
            }
            report.findings.push(TimeFinding {
                rule: kind.rule_id(),
                severity: Severity::Unresolved,
                file: f.path.to_owned(),
                range: (0, 0),
                message: format!(
                    "{} has no clock roles, so {} cannot be decided",
                    f.path,
                    kind.rule_id()
                ),
                reason: Some(UnresolvedReason::Fidelity),
                anchor: format!("{}:unresolved:{}", f.path, kind.rule_id()),
            });
        }
    }
    for id in [TIME001, TIME002] {
        if examined == 0 {
            report
                .not_applicable
                .insert(id, "no Rust or Python files in the walk".to_owned());
        } else {
            report.subjects.insert(id, examined);
        }
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "time pass done"
    );
    report
}

/// True when a language without clock roles still reads time, so silence would hide a gap.
fn unresolvable(language: gob_languages::Language) -> bool {
    use gob_languages::Language;
    matches!(language, Language::TypeScript | Language::CSharp)
}
