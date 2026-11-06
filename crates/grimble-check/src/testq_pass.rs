//! The TESTQ pass: scan the test files of the walk and return every verdict as a [`PathFinding`].
//!
//! TESTQ findings share the PATH finding and report shapes, so the product converts them like the
//! TIME findings. A site whose certainty is [`Certainty::Unknown`] (a helper out of sight) and a
//! language without test roles are reported Unresolved, never as a hit and never as clean.
//! `TESTQ003` is off by default: it runs only when [`TestqOptions::control_flow`] is set, which
//! the product does when `[rules.TESTQ003] severity` is present in `grimble.toml`.

// frob:ticket 01M5HJNE91SN4N0MR8GHM30Z1Y

use std::collections::BTreeSet;
use std::path::Path;

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use grimble_lints::pass::{PathFile, PathFinding, PathReport};
use grimble_lints::res::Certainty;
use grimble_lints::testq::{self, Kind};
use rayon::prelude::*;

/// Rule id of the test without an assertion.
pub const TESTQ001: &str = "TESTQ001";
/// Rule id of the sleep, wall-clock read or unseeded random source in a test.
pub const TESTQ002: &str = "TESTQ002";
/// Rule id of the control flow in a test body (off by default).
pub const TESTQ003: &str = "TESTQ003";

/// Why `TESTQ003` is not applicable on a run that did not opt in.
pub const CONTROL_FLOW_OFF: &str =
    "off by default; enable it with `[rules.TESTQ003] severity = \"error\"` in grimble.toml";

/// What the TESTQ pass may be asked to do beyond the default rules.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct TestqOptions {
    /// Run `TESTQ003` (control flow in a test body); a taste call, so off unless a project opts in.
    pub control_flow: bool,
}

/// The message of a decided site of `kind` named `detail`.
fn describe(kind: Kind, detail: &str) -> String {
    match kind {
        Kind::NoAssertion => format!("test `{detail}` asserts nothing; add an assertion or an expected-failure check"),
        Kind::Nondeterminism => format!("`{detail}` makes the test depend on time or chance; fake the clock or seed the source"),
        Kind::ControlFlow => format!("`{detail}` branches inside a test body; split the cases into separate tests or parametrize"),
    }
}

/// True when `file` holds tests worth scanning: Rust anywhere (in-file `#[test]`), others by name.
fn scannable(file: &PathFile<'_>) -> bool {
    file.language == Language::Rust || testq::is_test_file(Path::new(file.path))
}

/// True when a language without test roles is a code language whose silence would hide a gap.
fn unresolvable(language: Language) -> bool {
    matches!(
        language,
        Language::Go | Language::Java | Language::C | Language::Cpp
    )
}

/// Whether `kind` runs under `opts`.
fn enabled(kind: Kind, opts: &TestqOptions) -> bool {
    kind.default_enabled() || opts.control_flow
}

/// Run `TESTQ001` to `TESTQ003` over `files`.
pub fn analyze(files: &[PathFile<'_>], opts: &TestqOptions) -> PathReport {
    let mut report = PathReport::default();
    let mut examined = 0usize;
    let mut undecided: BTreeSet<(Kind, &'static str)> = BTreeSet::new();
    let targets: Vec<&PathFile<'_>> = files.iter().filter(|f| scannable(f)).collect();
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Result<testq::Report, testq::ScanError>> = targets
        .par_iter()
        .map(|f| testq::scan(f.language, f.text))
        .collect();
    for (f, scanned) in targets.iter().zip(scans) {
        let scanned = match scanned {
            Ok(r) => r,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "testq scan skipped an unparsable file");
                continue;
            }
        };
        if testq::has_test_roles(f.language) {
            examined += 1;
        }
        let lines: Vec<&str> = if scanned.sites.is_empty() {
            Vec::new()
        } else {
            f.text.lines().collect()
        };
        for site in scanned.sites.iter().filter(|s| enabled(s.kind, opts)) {
            let range = (
                u32::from(site.range.start()) as usize,
                u32::from(site.range.end()) as usize,
            );
            let line_text = lines
                .get(site.line.saturating_sub(1))
                .copied()
                .unwrap_or("");
            let (severity, message, reason) = match site.certainty {
                Certainty::Certain => (Severity::Error, describe(site.kind, &site.detail), None),
                Certainty::Unknown => (
                    Severity::Unresolved,
                    format!(
                        "test `{}` calls a helper whose body is out of sight, so {} cannot be decided",
                        site.detail,
                        site.kind.rule_id()
                    ),
                    Some(UnresolvedReason::Fidelity),
                ),
            };
            tracing::debug!(rule = site.kind.rule_id(), file = f.path, line = site.line, ?severity, "testq site");
            report.findings.push(PathFinding {
                rule: site.kind.rule_id(),
                severity,
                file: f.path.to_owned(),
                range,
                message,
                reason,
                anchor: format!("{}:{}", f.path, line_text.trim()),
            });
        }
        if testq::has_test_roles(f.language) || !unresolvable(f.language) {
            continue;
        }
        for kind in scanned.unresolved.iter().filter(|k| enabled(**k, opts)) {
            // One Unresolved verdict per rule and language, at the first file, not one per file.
            if !undecided.insert((*kind, f.language.name())) {
                continue;
            }
            report.findings.push(PathFinding {
                rule: kind.rule_id(),
                severity: Severity::Unresolved,
                file: f.path.to_owned(),
                range: (0, 0),
                message: format!(
                    "{} has no test roles, so {} cannot be decided",
                    f.path,
                    kind.rule_id()
                ),
                reason: Some(UnresolvedReason::Fidelity),
                anchor: format!("{}:unresolved:{}", f.path, kind.rule_id()),
            });
        }
    }
    for id in [TESTQ001, TESTQ002] {
        if examined == 0 {
            report
                .not_applicable
                .insert(id, "no test files in the walk".to_owned());
        } else {
            report.subjects.insert(id, examined);
        }
    }
    if !opts.control_flow {
        report.not_applicable.insert(TESTQ003, CONTROL_FLOW_OFF.to_owned());
    } else if examined == 0 {
        report
            .not_applicable
            .insert(TESTQ003, "no test files in the walk".to_owned());
    } else {
        report.subjects.insert(TESTQ003, examined);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "testq pass done"
    );
    report
}
