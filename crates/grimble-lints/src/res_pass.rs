//! The RES pass: run [`res::scan`] over the walked files and return every verdict as a
//! [`PathFinding`].
//!
//! RES findings share the PATH finding and report shapes. A certain site is a Warn; a site whose
//! handle escapes the scope (returned, stored, passed on) or is discarded is Unresolved, because
//! the release may live out of sight (never a guessed Warn). Subjects are the files in a language
//! the scan reads: TypeScript, TSX, JavaScript and JSX.

// frob:ticket 01M4MGE2XKGBNJEV1AECPBVHQF

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::pass::{PathFile, PathFinding, PathReport};
use crate::res::{self, Certainty, PAIRS, ScanError, Site};

/// Rule id of the unpaired-resource-acquisition rule.
pub const RES001: &str = "RES001";

/// What the RES pass found and examined.
pub type ResReport = PathReport;

/// True for the languages the RES scan reads.
fn judged(language: Language) -> bool {
    matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    )
}

/// The message of an unpaired acquire of pair `id`.
fn describe(id: &str) -> String {
    let release = PAIRS
        .iter()
        .find(|p| p.id == id)
        .and_then(|p| p.release.first())
        .copied()
        .unwrap_or("its release");
    format!("resource acquire `{id}` has no paired release in scope; call `{release}` or hand the resource to an owner that does")
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
        Certainty::Certain => (Severity::Warn, None),
        Certainty::Unknown => (Severity::Unresolved, Some(UnresolvedReason::Fidelity)),
    };
    PathFinding {
        rule: RES001,
        severity,
        file: f.path.to_owned(),
        range,
        message: describe(site.pair),
        reason,
        anchor: format!("{}:{}:{}", f.path, site.pair, line_text.trim()),
    }
}

/// Run `RES001` over `files`.
pub fn analyze(files: &[PathFile<'_>]) -> ResReport {
    let mut report = ResReport::default();
    let mut examined = 0usize;
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Result<Vec<Site>, ScanError>> = files
        .par_iter()
        .map(|f| res::scan(f.language, f.text))
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let sites = match scanned {
            Ok(sites) => sites,
            Err(error) => {
                tracing::debug!(file = f.path, %error, "res scan skipped an unparsable file");
                continue;
            }
        };
        if judged(f.language) {
            examined += 1;
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
    if examined == 0 {
        report.not_applicable.insert(
            RES001,
            "no TypeScript or JavaScript files in the walk".to_owned(),
        );
    } else {
        report.subjects.insert(RES001, examined);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.range, &a.anchor).cmp(&(&b.file, b.range, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "res pass done"
    );
    report
}
