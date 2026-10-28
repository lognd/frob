//! The PATH pass: scan the walked files and return every verdict as a [`PathFinding`].

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1

use std::collections::{BTreeMap, BTreeSet};

use gob_languages::Language;
use gob_rules::{Finding, RuleId, Severity, UnresolvedReason};
use gob_text::{FileInterner, Span, TextRange, TextSize};
use rayon::prelude::*;

use crate::path::{self, Kind, Options};

/// Rule id of the absolute host path rule.
pub const PATH001: &str = "PATH001";
/// Rule id of the string path separator rule.
pub const PATH002: &str = "PATH002";
/// Rule id of the path in command line rule.
pub const PATH003: &str = "PATH003";

/// One PATH verdict before the product interns its span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PathFinding {
    /// The rule id (`PATH001`).
    pub rule: &'static str,
    /// The severity; `Unresolved` when `reason` is set.
    pub severity: Severity,
    /// Repo-relative file the finding points into.
    pub file: String,
    /// Byte range in that file.
    pub range: (usize, usize),
    /// The message.
    pub message: String,
    /// Why an Unresolved finding could not decide; `None` for a resolved finding.
    pub reason: Option<UnresolvedReason>,
    /// The anchor the fingerprint is computed from.
    pub anchor: String,
}

impl PathFinding {
    /// Intern the span and build the pipeline [`Finding`]; `None` when the rule id is invalid.
    pub fn into_finding(self, files: &mut FileInterner) -> Option<Finding> {
        let id: RuleId = match self.rule.parse() {
            Ok(id) => id,
            Err(err) => {
                tracing::error!(rule = self.rule, %err, "path finding names an invalid rule id");
                return None;
            }
        };
        let size = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        let (start, end) = self.range;
        let span = Span::new(
            files.intern(&self.file),
            TextRange::new(size(start), size(end.max(start))),
        );
        let finding = Finding::new(id, self.severity, Some(span), self.message, &self.anchor);
        Some(match self.reason {
            Some(r) => finding.with_reason(r),
            None => finding,
        })
    }
}

/// One file the PATH pass reads.
pub struct PathFile<'a> {
    /// Repo-relative path.
    pub path: &'a str,
    /// The language the walk detected for it.
    pub language: Language,
    /// The file text.
    pub text: &'a str,
}

/// What the PATH pass found and examined.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct PathReport {
    /// Findings of the three rules, sorted by file, rule and anchor.
    pub findings: Vec<PathFinding>,
    /// Files examined per rule (those whose language the rule can judge); absent when none.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Rules whose whole scope is absent here (rule id to the reason), so zero subjects is not a gap.
    pub not_applicable: BTreeMap<&'static str, String>,
}

/// The message of a kind.
fn describe(kind: Kind) -> &'static str {
    match kind {
        Kind::AbsoluteHostPath => "absolute host path literal; build the path from a root instead",
        Kind::StringPathSeparator => {
            "path turned into a string and handled with a literal separator; use Path operations"
        }
        Kind::PathInCommandLine => {
            "path interpolated into one command-line string; pass it as its own argument"
        }
    }
}

/// The severity of a scanner [`path::Severity`] in the pipeline.
fn map_severity(_scanner: path::Severity) -> Severity {
    Severity::Error
}

/// Run `PATH001` to `PATH003` over `files` with `options`.
pub fn analyze(files: &[PathFile<'_>], options: &Options) -> PathReport {
    let mut report = PathReport::default();
    let mut examined = [0usize; 3];
    let mut undecided: BTreeSet<(Kind, &'static str)> = BTreeSet::new();
    // The parse-and-scan of each file is independent and is the whole cost of the pass, so it
    // runs on the rayon pool; the fold below stays sequential so the report is deterministic.
    let scans: Vec<Result<path::Report, path::ScanError>> = files
        .par_iter()
        .map(|f| path::scan(f.language, f.text, options))
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let scanned = match scanned {
            Ok(r) => r,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "path scan skipped an unparsable file");
                continue;
            }
        };
        let lines: Vec<&str> = if scanned.sites.is_empty() {
            Vec::new()
        } else {
            f.text.lines().collect()
        };
        if scanned_any(f.language) {
            examined[0] += 1;
            if path::has_conversion_roles(f.language) {
                examined[1] += 1;
                examined[2] += 1;
            }
        }
        let test_file = path::is_test_path(f.path);
        for site in &scanned.sites {
            let severity =
                map_severity(path::default_severity(site.kind, test_file || site.in_test));
            let (start, end) = (
                u32::from(site.range.start()) as usize,
                u32::from(site.range.end()) as usize,
            );
            let line_text = lines
                .get(site.line.saturating_sub(1))
                .copied()
                .unwrap_or("");
            report.findings.push(PathFinding {
                rule: site.kind.rule_id(),
                severity,
                file: f.path.to_owned(),
                range: (start, end),
                message: describe(site.kind).to_owned(),
                reason: None,
                anchor: format!("{}:{}", f.path, line_text.trim()),
            });
        }
        for kind in &scanned.unresolved {
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
                    "{} has no path-conversion roles, so {} cannot be decided",
                    f.path,
                    kind.rule_id()
                ),
                reason: Some(UnresolvedReason::Fidelity),
                anchor: format!("{}:unresolved:{}", f.path, kind.rule_id()),
            });
        }
    }
    for (id, n) in [PATH001, PATH002, PATH003].into_iter().zip(examined) {
        if n == 0 {
            report.not_applicable.insert(
                id,
                "no Rust, Python, TypeScript or C# files in the walk".to_owned(),
            );
        } else {
            report.subjects.insert(id, n);
        }
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "path pass done"
    );
    report
}

/// True when `language` has string literals the scanner reads.
fn scanned_any(language: Language) -> bool {
    matches!(
        language,
        Language::Rust | Language::Python | Language::TypeScript | Language::CSharp
    )
}
