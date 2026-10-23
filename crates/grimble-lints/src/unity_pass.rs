//! The UNITY pass: run [`unity_hot::scan`] over the walked C# files and return every verdict as a
//! [`PathFinding`].
//!
//! UNITY findings share the PATH finding and report shapes, so the product converts all of them the
//! same way. Both rules are Advisory (zero allocation as a global target is contested); a site the
//! syntax cannot decide is Unresolved, never a guessed verdict.

// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::pass::{PathFile, PathFinding, PathReport};
use crate::res::{Certainty, ScanError};
use crate::unity_common::Finding;
use crate::unity_hot::{self, RULE_ALLOC, RULE_LOOKUP};

/// One UNITY verdict before the product interns its span.
pub type UnityFinding = PathFinding;
/// What the UNITY pass found and examined.
pub type UnityReport = PathReport;

/// The rules this pass evaluates, in id order.
const RULES: [&str; 2] = [RULE_LOOKUP, RULE_ALLOC];

/// True when a C# file is Unity code: it names the engine namespace or a `MonoBehaviour`.
///
/// A plain .NET class with an `Update` method is not on a frame loop, so it is not examined.
fn is_unity_source(text: &str) -> bool {
    text.contains("UnityEngine") || text.contains("MonoBehaviour")
}

/// Convert one scan finding of `f` into a pass verdict.
fn verdict(f: &PathFile<'_>, lines: &[&str], found: &Finding) -> UnityFinding {
    let range = (
        u32::from(found.range.start()) as usize,
        u32::from(found.range.end()) as usize,
    );
    let line = f.text[..range.0].bytes().filter(|b| *b == b'\n').count();
    let line_text = lines.get(line).copied().unwrap_or("");
    let (severity, reason) = match found.certainty {
        Certainty::Certain => (Severity::Advisory, None),
        Certainty::Unknown => (Severity::Unresolved, Some(UnresolvedReason::Fidelity)),
    };
    UnityFinding {
        rule: found.rule,
        severity,
        file: f.path.to_owned(),
        range,
        message: found.message.clone(),
        reason,
        anchor: format!("{}:{}:{}", f.path, found.rule, line_text.trim()),
    }
}

/// Run `UNITY201` and `UNITY202` over the Unity C# files of `files`.
pub fn analyze(files: &[PathFile<'_>]) -> UnityReport {
    let mut report = UnityReport::default();
    let mut examined = 0usize;
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Option<Result<Vec<Finding>, ScanError>>> = files
        .par_iter()
        .map(|f| {
            (f.language == Language::CSharp && is_unity_source(f.text))
                .then(|| unity_hot::scan(f.language, f.text))
        })
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let Some(scanned) = scanned else { continue };
        let found = match scanned {
            Ok(found) => found,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "unity scan skipped an unparsable file");
                continue;
            }
        };
        examined += 1;
        let lines: Vec<&str> = if found.is_empty() {
            Vec::new()
        } else {
            f.text.lines().collect()
        };
        report
            .findings
            .extend(found.iter().map(|x| verdict(f, &lines, x)));
    }
    for rule in RULES {
        if examined == 0 {
            report
                .not_applicable
                .insert(rule, "no Unity C# files in the walk".to_owned());
        } else {
            report.subjects.insert(rule, examined);
        }
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.range, &a.anchor).cmp(&(&b.file, b.range, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        subjects = ?report.subjects,
        "unity pass done"
    );
    report
}
