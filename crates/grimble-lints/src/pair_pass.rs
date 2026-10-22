//! The PAIR pass: run [`effect::scan`] over the walked files and return every verdict as a
//! [`PathFinding`].
//!
//! PAIR findings share the PATH finding and report shapes: the product converts all of them the
//! same way. Only the React vocabulary of `PAIR001` is wired here; a certain site is a Warn, a site
//! whose cleanup the scan cannot read is Unresolved (never a guessed Warn).

// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::effect::{self, Reason};
use crate::pass::{PathFile, PathFinding, PathReport};
use crate::res::{Certainty, ScanError};

/// Rule id of the acquire-without-release rule.
pub const PAIR001: &str = "PAIR001";

/// One PAIR verdict before the product interns its span.
pub type PairFinding = PathFinding;
/// What the PAIR pass found and examined.
pub type PairReport = PathReport;

/// The message of an unpaired effect acquire.
fn describe(pair: &str, reason: Reason) -> String {
    let why = match reason {
        Reason::NoCleanup => "the effect returns no cleanup",
        Reason::AsyncEffect => "an async effect returns a promise, never a cleanup",
        Reason::CleanupMissesAcquire => "the returned cleanup releases something else",
        Reason::ConditionalCleanup => "the cleanup is returned only on some paths",
        Reason::OpaqueCleanup => "the returned cleanup is not readable here",
    };
    format!("effect acquire `{pair}` is never released: {why}; return a cleanup that undoes it")
}

/// True for the languages that can hold a React effect.
fn has_effect_roles(language: Language) -> bool {
    matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    )
}

/// Run `PAIR001` (React vocabulary) over `files`.
pub fn analyze(files: &[PathFile<'_>]) -> PairReport {
    let mut report = PairReport::default();
    let mut examined = 0usize;
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Result<Vec<effect::Site>, ScanError>> = files
        .par_iter()
        .map(|f| effect::scan(f.language, f.text))
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let sites = match scanned {
            Ok(sites) => sites,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "pair scan skipped an unparsable file");
                continue;
            }
        };
        if has_effect_roles(f.language) {
            examined += 1;
        }
        let lines: Vec<&str> = if sites.is_empty() {
            Vec::new()
        } else {
            f.text.lines().collect()
        };
        for site in &sites {
            let range = (
                u32::from(site.range.start()) as usize,
                u32::from(site.range.end()) as usize,
            );
            let line = f.text[..range.0].bytes().filter(|b| *b == b'\n').count();
            let line_text = lines.get(line).copied().unwrap_or("");
            let (severity, reason) = match site.certainty {
                Certainty::Certain => (Severity::Warn, None),
                Certainty::Unknown => (Severity::Unresolved, Some(UnresolvedReason::Fidelity)),
            };
            report.findings.push(PairFinding {
                rule: PAIR001,
                severity,
                file: f.path.to_owned(),
                range,
                message: describe(site.pair, site.reason),
                reason,
                anchor: format!("{}:{}:{}", f.path, site.pair, line_text.trim()),
            });
        }
    }
    if examined == 0 {
        report.not_applicable.insert(
            PAIR001,
            "no TypeScript or JavaScript files in the walk".to_owned(),
        );
    } else {
        report.subjects.insert(PAIR001, examined);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.range, &a.anchor).cmp(&(&b.file, b.range, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "pair pass done"
    );
    report
}
