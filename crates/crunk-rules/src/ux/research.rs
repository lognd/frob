//! The research-evidence checks: every persona and journey cites existing research, every screen
//! cites a persona or job, research is not older than the staleness window, and a load problem
//! (bad front matter, malformed file, duplicate persona id) is a located schema finding. A project
//! with no research artifacts at all is silent.

// frob:ticket 01M5XCYCSXSPQP9A4DZKNX5RGS

use std::collections::BTreeSet;

use crunk_spec::research::{Date, ResearchSet};

/// What a research finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ResearchIssue {
    /// A research, persona or journey file is malformed or duplicates an id.
    Schema,
    /// A persona or journey cites no research.
    NoEvidence,
    /// A citation names a research, persona or job that does not exist.
    Dangling,
    /// A screen cites no persona or job.
    ScreenUncited,
    /// A research note is older than the staleness window.
    Stale,
}

/// One research finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResearchFinding {
    /// What kind of finding.
    pub issue: ResearchIssue,
    /// The file it is about, relative to the project root (a screen id for screen findings).
    pub path: String,
    /// The 1-based line, when the issue has one.
    pub line: Option<usize>,
    /// The human message.
    pub message: String,
}

/// A screen as the research checks see it: its id and the persona or job ids it cites.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ScreenCitations {
    /// The screen id.
    pub id: String,
    /// Persona or job ids the screen cites.
    pub cites: Vec<String>,
}

/// A finding without a line.
fn finding(issue: ResearchIssue, path: &str, message: String) -> ResearchFinding {
    ResearchFinding {
        issue,
        path: path.to_owned(),
        line: None,
        message,
    }
}

/// Evidence findings for one persona or journey `kind` `id` citing `evidence`.
fn check_evidence(
    out: &mut Vec<ResearchFinding>,
    path: &str,
    kind: &str,
    id: &str,
    evidence: &[String],
    research: &BTreeSet<&str>,
) {
    if evidence.is_empty() {
        tracing::debug!(%path, %id, "no cited evidence");
        out.push(finding(
            ResearchIssue::NoEvidence,
            path,
            format!("{kind} `{id}` cites no research evidence"),
        ));
    }
    for cited in evidence {
        if !research.contains(cited.as_str()) {
            out.push(finding(
                ResearchIssue::Dangling,
                path,
                format!("{kind} `{id}` cites missing research `{cited}`"),
            ));
        }
    }
}

/// Run every research check. `today` is the current date and `stale_days` the staleness window;
/// research older than the window is stale. `jobs` are the job ids a screen may cite besides
/// personas. Findings come in load problems, personas, journeys, research, screens order.
#[must_use]
pub fn check_research_rules(
    set: &ResearchSet,
    screens: &[ScreenCitations],
    jobs: &BTreeSet<String>,
    today: Date,
    stale_days: u32,
) -> Vec<ResearchFinding> {
    let mut out: Vec<ResearchFinding> = set
        .problems
        .iter()
        .map(|p| ResearchFinding {
            issue: ResearchIssue::Schema,
            path: p.path.clone(),
            line: p.line,
            message: p.message.clone(),
        })
        .collect();
    if set.is_empty() {
        tracing::debug!(problems = out.len(), "no research artifacts; checks silent");
        return out;
    }
    let research: BTreeSet<&str> = set.research.iter().map(|(_, d)| d.id.as_str()).collect();
    let personas: BTreeSet<&str> = set.personas.iter().map(|(_, p)| p.id.as_str()).collect();
    for (path, p) in &set.personas {
        check_evidence(&mut out, path, "persona", &p.id, &p.evidence, &research);
    }
    for (path, j) in &set.journeys {
        check_evidence(&mut out, path, "journey", &j.id, &j.evidence, &research);
        if let Some(who) = j.persona.as_deref().filter(|w| !personas.contains(w)) {
            out.push(finding(
                ResearchIssue::Dangling,
                path,
                format!("journey `{}` names missing persona `{who}`", j.id),
            ));
        }
    }
    for (path, d) in &set.research {
        let age = today.days() - d.date.days();
        if age > i64::from(stale_days) {
            tracing::debug!(%path, age, "stale research");
            out.push(finding(
                ResearchIssue::Stale,
                path,
                format!(
                    "research `{}` is {age} days old (window {stale_days})",
                    d.id
                ),
            ));
        }
    }
    for screen in screens {
        if screen.cites.is_empty() {
            out.push(finding(
                ResearchIssue::ScreenUncited,
                &screen.id,
                format!("screen `{}` cites no persona or job", screen.id),
            ));
        }
        for cited in &screen.cites {
            if !personas.contains(cited.as_str()) && !jobs.contains(cited) {
                out.push(finding(
                    ResearchIssue::Dangling,
                    &screen.id,
                    format!(
                        "screen `{}` cites unknown persona or job `{cited}`",
                        screen.id
                    ),
                ));
            }
        }
    }
    tracing::debug!(findings = out.len(), "research checks done");
    out
}
