//! The UNITY pass: run [`unity_hot::scan`] over the walked C# files and return every verdict as a
//! [`PathFinding`].
//!
//! UNITY findings share the PATH finding and report shapes, so the product converts all of them the
//! same way. `UNITY201` and `UNITY202` are Advisory (zero allocation as a global target is contested);
//! `UNITY301` and `UNITY302` are Warn (a runtime exception, a frame-rate dependent force); a site the
//! syntax cannot decide is Unresolved, never a guessed verdict.
//!
//! [`analyze_project`] adds `UNITY301` (legacy `Input` under the Input System handler, read from the
//! nearest `ProjectSettings/ProjectSettings.asset` above each file) and `UNITY302` (a per-frame
//! Rigidbody force); [`analyze_all`] is the union the product runs.

// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY
// frob:ticket 01M5HGRWG7RDR3DTS7PT08HTWJ

use std::path::{Path, PathBuf};

use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use rayon::prelude::*;

use crate::pass::{PathFile, PathFinding, PathReport};
use crate::res::{Certainty, ScanError};
use crate::unity_common::Finding;
use crate::unity_hot::{self, RULE_ALLOC, RULE_LOOKUP};
use crate::unity_input::{self, InputHandler};
use crate::unity_physics;

/// One UNITY verdict before the product interns its span.
pub type UnityFinding = PathFinding;
/// What the UNITY pass found and examined.
pub type UnityReport = PathReport;

/// The rules this pass evaluates, in id order.
const RULES: [&str; 2] = [RULE_LOOKUP, RULE_ALLOC];

/// True when a C# file is Unity code: it names the engine namespace or a `MonoBehaviour`.
///
/// A plain .NET class with an `Update` method is not on a frame loop, so it is not examined.
pub(crate) fn is_unity_source(text: &str) -> bool {
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
        Certainty::Certain if RULES.contains(&found.rule) => (Severity::Advisory, None),
        Certainty::Certain => (Severity::Warn, None),
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

/// Append the verdicts of `found` (the scan of `f`) to `report`.
fn push_findings(report: &mut UnityReport, f: &PathFile<'_>, found: &[Finding]) {
    if found.is_empty() {
        return;
    }
    let lines: Vec<&str> = f.text.lines().collect();
    report
        .findings
        .extend(found.iter().map(|x| verdict(f, &lines, x)));
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
        push_findings(&mut report, f, &found);
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

/// The rules [`analyze_project`] evaluates, in id order.
const PROJECT_RULES: [&str; 2] = [unity_input::RULE, unity_physics::RULE];

/// A Unity `ProjectSettings/ProjectSettings.asset` the walk found.
#[derive(Debug, Clone, Copy)]
pub struct SettingsFile<'a> {
    /// Repo-relative path of the asset.
    pub path: &'a str,
    /// The asset text.
    pub text: &'a str,
}

/// True when `path` is a Unity `ProjectSettings/ProjectSettings.asset`.
pub fn is_project_settings(path: &str) -> bool {
    let p = Path::new(path);
    p.file_name().is_some_and(|n| n == "ProjectSettings.asset")
        && p.parent()
            .and_then(Path::file_name)
            .is_some_and(|n| n == "ProjectSettings")
}

/// The input handler each settings asset declares, keyed by the project root it sits in.
///
/// An asset that is not a `PlayerSettings` document, or whose handler value is unreadable, is
/// skipped and logged: its project is then not applicable, never guessed to be legacy.
fn project_handlers(settings: &[SettingsFile<'_>]) -> Vec<(PathBuf, InputHandler)> {
    settings
        .iter()
        .filter_map(|s| {
            if !s.text.contains("PlayerSettings:") {
                tracing::warn!(
                    file = s.path,
                    "ProjectSettings.asset is not a PlayerSettings document"
                );
                return None;
            }
            let Some(handler) = unity_input::active_input_handler(s.text) else {
                tracing::warn!(file = s.path, "activeInputHandler is not 0, 1 or 2");
                return None;
            };
            let root = Path::new(s.path).parent()?.parent()?.to_path_buf();
            Some((root, handler))
        })
        .collect()
}

/// The handler of the innermost project that contains `file`, if any.
fn handler_of(file: &str, projects: &[(PathBuf, InputHandler)]) -> Option<InputHandler> {
    projects
        .iter()
        .filter(|(root, _)| Path::new(file).starts_with(root))
        .max_by_key(|(root, _)| root.components().count())
        .map(|(_, handler)| *handler)
}

/// One file's scan outcome.
type Scan = Result<Vec<Finding>, ScanError>;

/// Run `UNITY301` and `UNITY302` over the Unity C# files of `files`.
///
/// `UNITY301` needs the project's input handler, so it examines only files under a readable
/// `settings` asset and is not applicable when there is none. `UNITY302` needs no settings.
pub fn analyze_project(files: &[PathFile<'_>], settings: &[SettingsFile<'_>]) -> UnityReport {
    let projects = project_handlers(settings);
    let mut report = UnityReport::default();
    let (mut input_examined, mut physics_examined) = (0usize, 0usize);
    let scans: Vec<Option<(Option<Scan>, Scan)>> = files
        .par_iter()
        .map(|f| {
            (f.language == Language::CSharp && is_unity_source(f.text)).then(|| {
                let input =
                    handler_of(f.path, &projects).map(|h| unity_input::scan(f.language, f.text, h));
                (input, unity_physics::scan(f.language, f.text))
            })
        })
        .collect();
    for (f, scanned) in files.iter().zip(scans) {
        let Some((input, physics)) = scanned else {
            continue;
        };
        if let Some(input) = input {
            match input {
                Ok(found) => {
                    input_examined += 1;
                    push_findings(&mut report, f, &found);
                }
                Err(err) => {
                    tracing::debug!(file = f.path, %err, "input scan skipped an unparsable file");
                }
            }
        }
        match physics {
            Ok(found) => {
                physics_examined += 1;
                push_findings(&mut report, f, &found);
            }
            Err(err) => {
                tracing::debug!(file = f.path, %err, "physics scan skipped an unparsable file");
            }
        }
    }
    let reasons = [
        "no Unity C# file under a readable ProjectSettings.asset in the walk",
        "no Unity C# files in the walk",
    ];
    for ((rule, examined), why) in PROJECT_RULES
        .into_iter()
        .zip([input_examined, physics_examined])
        .zip(reasons)
    {
        if examined == 0 {
            report.not_applicable.insert(rule, why.to_owned());
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
        projects = projects.len(),
        "unity project pass done"
    );
    report
}

/// Run every UNITY rule (201, 202, 301, 302) over `files`, with `settings` for `UNITY301`.
pub fn analyze_all(files: &[PathFile<'_>], settings: &[SettingsFile<'_>]) -> UnityReport {
    let mut report = analyze(files);
    let project = analyze_project(files, settings);
    report.findings.extend(project.findings);
    report.subjects.extend(project.subjects);
    report.not_applicable.extend(project.not_applicable);
    report
        .findings
        .sort_by(|a, b| (&a.file, a.range, &a.anchor).cmp(&(&b.file, b.range, &b.anchor)));
    report
}
