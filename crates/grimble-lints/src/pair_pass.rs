//! The PAIR pass: run [`effect::scan`] over the walked files and return every verdict as a
//! [`PathFinding`].
//!
//! PAIR findings share the PATH finding and report shapes: the product converts all of them the
//! same way. Two vocabularies of `PAIR001` are wired here: React ([`effect::scan`], TS/JS files) and
//! Unity ([`unity::scan`], C# files that name `UnityEngine` or `MonoBehaviour`; a plain .NET class
//! with an `OnEnable` method is not a lifecycle). A certain site is a Warn, a site whose cleanup the
//! scan cannot read is Unresolved (never a guessed Warn).

// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01
// frob:ticket 01M5K3RAZWM6Z4GWWQ716JGSGC

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::effect::{self, Reason};
use crate::pass::{PathFile, PathFinding, PathReport};
use crate::res::{Certainty, ScanError};
use crate::unity::{self, Reason as UnityReason};
use crate::unity_pass::is_unity_source;

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

/// The message of an unpaired Unity acquire.
fn describe_unity(pair: &str, reason: UnityReason) -> String {
    let why = match reason {
        UnityReason::NoTeardown => "the class has no OnDisable or OnDestroy",
        UnityReason::TeardownMissesAcquire => "OnDisable and OnDestroy release something else",
        UnityReason::ConditionalTeardown => "the release runs only on some paths",
        UnityReason::AnonymousHandler => "an anonymous handler cannot be removed",
        UnityReason::UnboundHandle => "the returned handle is not kept, so nothing can release it",
    };
    format!("Unity acquire `{pair}` is never released: {why}; undo it in OnDisable or OnDestroy")
}

/// True for the languages that can hold a React effect.
fn has_effect_roles(language: Language) -> bool {
    matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    )
}

/// One acquire site of either vocabulary, before it becomes a verdict.
struct Hit {
    pair: &'static str,
    range: gob_text::TextRange,
    certainty: Certainty,
    message: String,
}

/// Every unpaired acquire of `f`: React effects in TS/JS, Unity lifecycles in Unity C#.
fn scan_file(f: &PathFile<'_>) -> Result<Vec<Hit>, ScanError> {
    let mut hits: Vec<Hit> = effect::scan(f.language, f.text)?
        .into_iter()
        .map(|s| Hit {
            pair: s.pair,
            range: s.range,
            certainty: s.certainty,
            message: describe(s.pair, s.reason),
        })
        .collect();
    if is_unity_file(f) {
        hits.extend(unity::scan(f.language, f.text)?.into_iter().map(|s| Hit {
            pair: s.pair,
            range: s.range,
            certainty: s.certainty,
            message: describe_unity(s.pair, s.reason),
        }));
    }
    Ok(hits)
}

/// True for a C# file that holds Unity code.
fn is_unity_file(f: &PathFile<'_>) -> bool {
    f.language == Language::CSharp && is_unity_source(f.text)
}

/// Run `PAIR001` (React and Unity vocabularies) over `files`.
pub fn analyze(files: &[PathFile<'_>]) -> PairReport {
    let mut report = PairReport::default();
    let mut examined = 0usize;
    // Parsing and scanning is the whole cost and is independent per file, so it runs on the rayon
    // pool; the fold stays sequential so the report is deterministic.
    let scans: Vec<Result<Vec<Hit>, ScanError>> = files.par_iter().map(scan_file).collect();
    for (f, scanned) in files.iter().zip(scans) {
        let sites = match scanned {
            Ok(sites) => sites,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "pair scan skipped an unparsable file");
                continue;
            }
        };
        if has_effect_roles(f.language) || is_unity_file(f) {
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
                Certainty::Certain => (Severity::Error, None),
                Certainty::Unknown => (Severity::Unresolved, Some(UnresolvedReason::Fidelity)),
            };
            report.findings.push(PairFinding {
                rule: PAIR001,
                severity,
                file: f.path.to_owned(),
                range,
                message: site.message.clone(),
                reason,
                anchor: format!("{}:{}:{}", f.path, site.pair, line_text.trim()),
            });
        }
    }
    if examined == 0 {
        report.not_applicable.insert(
            PAIR001,
            "no TypeScript, JavaScript or Unity C# files in the walk".to_owned(),
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
