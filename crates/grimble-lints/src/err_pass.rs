//! The ERR pass: run [`err::scan`] over the walked files and return every verdict as a
//! [`PathFinding`].
//!
//! ERR findings share the PATH finding and report shapes. A certain site is a Warn; a site whose
//! callee fallibility the scan cannot read is Unresolved (never a guessed Warn). Subjects are the
//! files in a language the rule judges.

// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::err::{self, Certainty, Kind, ScanError, Site};
use crate::pass::{PathFile, PathFinding, PathReport};

/// Rule id of the empty-error-handler rule.
pub const ERR001: &str = "ERR001";
/// Rule id of the discarded-result rule.
pub const ERR002: &str = "ERR002";
/// Rule id of the silent-catch-all rule.
pub const ERR003: &str = "ERR003";

/// What the ERR pass found and examined.
pub type ErrReport = PathReport;

/// True when `rule` judges files in `language`.
fn judges(rule: &str, language: Language) -> bool {
    let handler_langs = matches!(
        language,
        Language::Python | Language::TypeScript | Language::CSharp
    );
    match rule {
        ERR001 => handler_langs || language == Language::Rust,
        ERR002 => language == Language::Rust,
        _ => handler_langs,
    }
}

/// The message of one swallowed-error site.
fn describe(kind: Kind) -> &'static str {
    match kind {
        Kind::EmptyHandler => "empty error handler swallows the error; handle, log or rethrow it",
        Kind::DiscardedResult => {
            "the result of a fallible call is discarded; handle the error or say why it is safe to drop"
        }
        Kind::SilentCatchAll => {
            "catch-all handler neither rethrows nor logs the error; log it or rethrow"
        }
    }
}

/// The verdict for one site of file `f`; `lines` are the file's lines.
fn finding(f: &PathFile<'_>, lines: &[&str], site: &Site) -> PathFinding {
    let range = (
        u32::from(site.range.start()) as usize,
        u32::from(site.range.end()) as usize,
    );
    let line = f.text[..range.0].bytes().filter(|b| *b == b'\n').count();
    let line_text = lines.get(line).copied().unwrap_or("");
    let (severity, reason) = match site.certainty {
        Certainty::Certain => (Severity::Error, None),
        Certainty::Unknown => (Severity::Unresolved, Some(UnresolvedReason::Fidelity)),
    };
    PathFinding {
        rule: site.kind.rule_id(),
        severity,
        file: f.path.to_owned(),
        range,
        message: describe(site.kind).to_owned(),
        reason,
        anchor: format!("{}:{}:{}", f.path, site.kind.rule_id(), line_text.trim()),
    }
}

/// Run `ERR001`, `ERR002` and `ERR003` over `files`.
pub fn analyze(files: &[PathFile<'_>]) -> ErrReport {
    let mut report = ErrReport::default();
    let mut examined = [0usize; 3];
    let rules = [ERR001, ERR002, ERR003];
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Result<Vec<Site>, ScanError>> = files
        .par_iter()
        .map(|f| err::scan(f.language, f.text))
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let sites = match scanned {
            Ok(sites) => sites,
            Err(error) => {
                tracing::debug!(file = f.path, %error, "err scan skipped an unparsable file");
                continue;
            }
        };
        for (slot, rule) in examined.iter_mut().zip(rules) {
            if judges(rule, f.language) {
                *slot += 1;
            }
        }
        let lines: Vec<&str> = if sites.is_empty() {
            Vec::new()
        } else {
            f.text.lines().collect()
        };
        report
            .findings
            .extend(sites.iter().map(|s| finding(f, &lines, s)));
    }
    for (rule, count) in rules.into_iter().zip(examined) {
        if count == 0 {
            report.not_applicable.insert(
                rule,
                "no Rust, Python, TypeScript or C# files in the walk".to_owned(),
            );
        } else {
            report.subjects.insert(rule, count);
        }
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.range, &a.anchor).cmp(&(&b.file, b.range, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "err pass done"
    );
    report
}
