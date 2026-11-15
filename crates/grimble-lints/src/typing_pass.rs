//! The TYPING pass: run [`cast::scan`] over the walked files and return every verdict as a
//! [`PathFinding`].
//!
//! TYPING findings share the PATH finding and report shapes. `TYPING004` is advisory: it names a
//! cast of unvalidated network or file data and never gates. Subjects are the TypeScript and TSX
//! files the scan reads.

// frob:ticket 01M4D95Q9WWPDZH86CMBMAZEDQ

use rayon::prelude::*;

use crate::cast::{self, Origin, Site};
use crate::pass::{PathFile, PathFinding, PathReport};
use crate::res::ScanError;

/// Rule id of the unvalidated boundary cast rule.
pub const TYPING004: &str = "TYPING004";

/// What the TYPING pass found and examined.
pub type TypingReport = PathReport;

/// The message of an unvalidated cast.
fn describe(site: &Site) -> String {
    let what = match site.origin {
        Origin::Json => "a response body",
        Origin::JsonParse => "parsed JSON",
        Origin::Binding => "a value read from a response or JSON, never validated,",
    };
    format!(
        "{what} is cast to `{}` without validation; parse it with a schema (zod, valibot) instead of `as`",
        site.target
    )
}

/// The verdict for one site of file `f`; `lines` are the file's lines.
fn finding(f: &PathFile<'_>, lines: &[&str], site: &Site) -> PathFinding {
    let range = (
        u32::from(site.range.start()) as usize,
        u32::from(site.range.end()) as usize,
    );
    let line = f.text[..range.0].bytes().filter(|b| *b == b'\n').count();
    let line_text = lines.get(line).copied().unwrap_or("");
    PathFinding {
        rule: TYPING004,
        severity: gob_rules::Severity::Error,
        file: f.path.to_owned(),
        range,
        message: describe(site),
        reason: None,
        anchor: format!("{}:{}", f.path, line_text.trim()),
    }
}

/// Run `TYPING004` over `files`.
pub fn analyze(files: &[PathFile<'_>]) -> TypingReport {
    let mut report = TypingReport::default();
    let mut examined = 0usize;
    // Parsing is the whole cost and is independent per file, so it runs on the rayon pool; the
    // fold stays sequential so the report is deterministic.
    let scans: Vec<Result<Vec<Site>, ScanError>> = files
        .par_iter()
        .map(|f| cast::scan(f.language, f.text))
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let sites = match scanned {
            Ok(sites) => sites,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "typing scan skipped an unparsable file");
                continue;
            }
        };
        if cast::judged(f.language) {
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
        report
            .not_applicable
            .insert(TYPING004, "no TypeScript files in the walk".to_owned());
    } else {
        report.subjects.insert(TYPING004, examined);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.range, &a.anchor).cmp(&(&b.file, b.range, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "typing pass done"
    );
    report
}
