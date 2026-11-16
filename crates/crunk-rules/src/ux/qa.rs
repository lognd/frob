//! The QA checks: a walkthrough step answering no fails and names the question, a major heuristic
//! finding needs an owner, every finding needs evidence, and every screen needs heuristic
//! coverage. A load problem is a located schema finding; a project with no QA artifacts is silent.

// frob:ticket 01M5XCZ14WCPMG9R6E269QRPVH

use crunk_spec::qa::{MAJOR_SEVERITY, QaSet};

/// What a QA finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum QaIssue {
    /// A QA file is malformed, names an unknown heuristic or has a bad severity.
    Schema,
    /// A walkthrough step answered a question no.
    WalkthroughFailed,
    /// A major finding names no owner.
    NoOwner,
    /// A finding cites no evidence.
    NoEvidence,
    /// A screen has no heuristic coverage.
    NoCoverage,
}

/// One QA finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QaFinding {
    /// What kind of finding.
    pub issue: QaIssue,
    /// The file (or screen id for coverage) it is about.
    pub path: String,
    /// The 1-based line, when known.
    pub line: Option<usize>,
    /// The human message.
    pub message: String,
}

/// A finding without a line.
fn finding(issue: QaIssue, path: &str, message: String) -> QaFinding {
    QaFinding {
        issue,
        path: path.to_owned(),
        line: None,
        message,
    }
}

/// Run every QA check against the known `screens` ids. Findings come in load problems,
/// heuristics, walkthroughs, coverage order.
#[must_use]
pub fn check_qa_rules(set: &QaSet, screens: &[String]) -> Vec<QaFinding> {
    let mut out: Vec<QaFinding> = set
        .problems
        .iter()
        .map(|p| QaFinding {
            issue: QaIssue::Schema,
            path: p.path.clone(),
            line: p.line,
            message: p.message.clone(),
        })
        .collect();
    if set.is_empty() {
        tracing::debug!(problems = out.len(), "no qa artifacts; checks silent");
        return out;
    }
    for (path, file) in &set.heuristics {
        for f in &file.findings {
            let name = format!("{:?}", f.heuristic);
            if f.severity >= MAJOR_SEVERITY && f.owner.is_none() {
                out.push(finding(
                    QaIssue::NoOwner,
                    path,
                    format!(
                        "major finding ({name}, severity {}) has no owner",
                        f.severity
                    ),
                ));
            }
            if f.evidence.is_none() {
                out.push(finding(
                    QaIssue::NoEvidence,
                    path,
                    format!("finding ({name}) cites no evidence"),
                ));
            }
        }
    }
    for (path, file) in &set.walkthroughs {
        for step in &file.steps {
            for q in step.failed_questions() {
                out.push(finding(
                    QaIssue::WalkthroughFailed,
                    path,
                    format!("step `{}` fails: {q}", step.name),
                ));
            }
        }
    }
    for screen in screens {
        let covered = set
            .heuristics
            .iter()
            .any(|(_, h)| h.screen == *screen && h.covers());
        if !covered {
            out.push(finding(
                QaIssue::NoCoverage,
                screen,
                format!("screen `{screen}` has no heuristic coverage"),
            ));
        }
    }
    tracing::debug!(findings = out.len(), "qa checks done");
    out
}
