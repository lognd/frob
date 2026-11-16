//! Usability and design QA artifacts: `design/qa/heuristics/*.toml` (findings against the ten NN/g
//! heuristics) and `design/qa/walkthroughs/*.toml` (four cognitive-walkthrough questions per step).
//! Parsing is pure; [`load_qa`] reads a project and reports each bad file as a located problem.

// frob:ticket 01M5XCZ14WCPMG9R6E269QRPVH

use std::collections::BTreeSet;
use std::path::Path;

use serde::Deserialize;

use crate::research::{ResearchError, ResearchProblem, parse_toml};

/// Directory holding heuristic evaluations, relative to the project root.
pub const HEURISTICS_DIR: &str = "design/qa/heuristics";
/// Directory holding walkthroughs, relative to the project root.
pub const WALKTHROUGHS_DIR: &str = "design/qa/walkthroughs";
/// The highest severity a finding may carry (0 is no problem).
pub const MAX_SEVERITY: u8 = 4;
/// The lowest severity that counts as major and so needs an owner.
pub const MAJOR_SEVERITY: u8 = 3;

/// One of Nielsen's ten usability heuristics.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Heuristic {
    /// Keep users informed about what is going on.
    VisibilityOfSystemStatus,
    /// Speak the user's language.
    MatchSystemRealWorld,
    /// Offer a clearly marked emergency exit.
    UserControlAndFreedom,
    /// Follow platform and internal conventions.
    ConsistencyAndStandards,
    /// Prevent problems before they occur.
    ErrorPrevention,
    /// Minimise memory load.
    RecognitionRatherThanRecall,
    /// Accelerators for experts.
    FlexibilityAndEfficiency,
    /// Show only what is relevant.
    AestheticAndMinimalistDesign,
    /// Plain-language errors with a way forward.
    HelpUsersRecoverFromErrors,
    /// Documentation that is searchable and task-focused.
    HelpAndDocumentation,
}

impl Heuristic {
    /// Every heuristic, in Nielsen's order.
    pub const ALL: [Self; 10] = [
        Self::VisibilityOfSystemStatus,
        Self::MatchSystemRealWorld,
        Self::UserControlAndFreedom,
        Self::ConsistencyAndStandards,
        Self::ErrorPrevention,
        Self::RecognitionRatherThanRecall,
        Self::FlexibilityAndEfficiency,
        Self::AestheticAndMinimalistDesign,
        Self::HelpUsersRecoverFromErrors,
        Self::HelpAndDocumentation,
    ];
}

/// One heuristic finding on a screen.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HeuristicFinding {
    /// The heuristic violated.
    pub heuristic: Heuristic,
    /// Severity 0 (none) to 4 (catastrophe).
    pub severity: u8,
    /// Who owns the fix (a ticket or person reference).
    #[serde(default)]
    pub owner: Option<String>,
    /// What shows the problem (a screenshot, recording or note reference).
    #[serde(default)]
    pub evidence: Option<String>,
    /// Free-text description.
    #[serde(default)]
    pub note: Option<String>,
}

/// A heuristic evaluation of one screen (`design/qa/heuristics/<screen>.toml`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HeuristicFile {
    /// The screen evaluated.
    pub screen: String,
    /// Heuristics reviewed without a finding.
    #[serde(default)]
    pub reviewed: Vec<Heuristic>,
    /// Findings raised.
    #[serde(default)]
    pub findings: Vec<HeuristicFinding>,
}

impl HeuristicFile {
    /// True when the evaluation reviewed at least one heuristic or raised a finding.
    #[must_use]
    pub fn covers(&self) -> bool {
        !self.reviewed.is_empty() || !self.findings.is_empty()
    }
}

/// One walkthrough step with the four cognitive-walkthrough answers.
#[allow(
    clippy::struct_excessive_bools,
    reason = "the walkthrough has exactly four yes/no questions"
)]
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WalkthroughStep {
    /// The step's name.
    pub name: String,
    /// Will the user try to achieve the right effect?
    pub tries: bool,
    /// Will the user notice the correct action is available?
    pub notices: bool,
    /// Will the user associate the action with the effect they want?
    pub associates: bool,
    /// Will the user see progress after acting?
    pub progress: bool,
}

impl WalkthroughStep {
    /// The questions answered no, as short phrases.
    #[must_use]
    pub fn failed_questions(&self) -> Vec<&'static str> {
        [
            (self.tries, "will the user try to achieve the effect"),
            (self.notices, "will the user notice the correct action"),
            (
                self.associates,
                "will the user associate the action with the effect",
            ),
            (self.progress, "will the user see progress"),
        ]
        .into_iter()
        .filter_map(|(yes, q)| (!yes).then_some(q))
        .collect()
    }
}

/// A walkthrough of one screen (`design/qa/walkthroughs/<screen>.toml`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WalkthroughFile {
    /// The screen walked.
    pub screen: String,
    /// The steps, in order.
    #[serde(default)]
    pub steps: Vec<WalkthroughStep>,
}

/// Parse a heuristic evaluation; an unknown heuristic lists the ten, severity above 4 is refused.
///
/// # Errors
/// [`ResearchError`] for invalid TOML, an unknown heuristic or an out-of-range severity.
pub fn parse_heuristics(text: &str) -> Result<HeuristicFile, ResearchError> {
    let file: HeuristicFile = parse_toml(text)?;
    match file.findings.iter().find(|f| f.severity > MAX_SEVERITY) {
        Some(bad) => Err(ResearchError {
            line: None,
            message: format!(
                "severity {} is outside 0-{MAX_SEVERITY} for screen `{}`",
                bad.severity, file.screen
            ),
        }),
        None => Ok(file),
    }
}

/// Parse a walkthrough file.
///
/// # Errors
/// [`ResearchError`] for invalid TOML or the wrong schema.
pub fn parse_walkthrough(text: &str) -> Result<WalkthroughFile, ResearchError> {
    parse_toml(text)
}

/// Everything loaded from a project's QA artifacts; each list is sorted by path.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct QaSet {
    /// Heuristic evaluations with their paths.
    pub heuristics: Vec<(String, HeuristicFile)>,
    /// Walkthroughs with their paths.
    pub walkthroughs: Vec<(String, WalkthroughFile)>,
    /// Files that were unreadable, invalid or repeated a screen.
    pub problems: Vec<ResearchProblem>,
}

impl QaSet {
    /// True when no heuristic or walkthrough file exists (problems aside).
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.heuristics.is_empty() && self.walkthroughs.is_empty()
    }
}

/// Load every `.toml` in `<root>/<dir>`, keeping valid files and refusing a repeated screen.
fn load_dir<T>(
    root: &Path,
    dir: &str,
    parse: fn(&str) -> Result<T, ResearchError>,
    screen_of: fn(&T) -> &str,
    problems: &mut Vec<ResearchProblem>,
) -> Vec<(String, T)> {
    let Ok(entries) = std::fs::read_dir(root.join(dir)) else {
        tracing::debug!(dir, "no qa directory");
        return Vec::new();
    };
    let mut names: Vec<String> = entries
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|n| Path::new(n).extension().is_some_and(|x| x == "toml"))
        .collect();
    names.sort();
    let mut seen = BTreeSet::new();
    let mut out = Vec::new();
    for name in names {
        let path = format!("{dir}/{name}");
        let mut problem = |message: String, line| {
            tracing::warn!(%path, %message, "qa file rejected");
            problems.push(ResearchProblem {
                path: path.clone(),
                line,
                message,
            });
        };
        let text = match std::fs::read_to_string(root.join(&path)) {
            Ok(t) => t,
            Err(err) => {
                problem(format!("unreadable: {err}"), None);
                continue;
            }
        };
        match parse(&text) {
            Ok(item) if seen.insert(screen_of(&item).to_owned()) => out.push((path.clone(), item)),
            Ok(item) => problem(format!("duplicate screen `{}`", screen_of(&item)), None),
            Err(e) => problem(e.message, e.line),
        }
    }
    out
}

/// Read every heuristic evaluation and walkthrough under `root`. A missing directory contributes
/// nothing; a bad file becomes a [`ResearchProblem`] and a repeated screen is refused.
#[must_use]
pub fn load_qa(root: &Path) -> QaSet {
    let mut problems = Vec::new();
    let heuristics = load_dir(
        root,
        HEURISTICS_DIR,
        parse_heuristics,
        |h| &h.screen,
        &mut problems,
    );
    let walkthroughs = load_dir(
        root,
        WALKTHROUGHS_DIR,
        parse_walkthrough,
        |w| &w.screen,
        &mut problems,
    );
    tracing::debug!(
        heuristics = heuristics.len(),
        walkthroughs = walkthroughs.len(),
        problems = problems.len(),
        "loaded qa"
    );
    QaSet {
        heuristics,
        walkthroughs,
        problems,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/qa.rs::parse_heuristics
    #[test]
    fn heuristics_parse() {
        let f = parse_heuristics(
            "screen = \"home\"\n[[findings]]\nheuristic = \"error-prevention\"\nseverity = 2\n",
        )
        .expect("ok");
        assert!(f.covers());
    }

    // frob:tests crates/crunk-spec/src/qa.rs::parse_heuristics
    #[test]
    fn unknown_heuristic_lists_the_ten() {
        let e = parse_heuristics("screen = \"h\"\nreviewed = [\"nope\"]\n").expect_err("bad");
        assert!(e.message.contains("help-and-documentation"));
    }

    // frob:tests crates/crunk-spec/src/qa.rs::parse_heuristics
    #[test]
    fn severity_above_four_is_rejected() {
        let text = "screen = \"h\"\n[[findings]]\nheuristic = \"error-prevention\"\nseverity = 5\n";
        assert!(parse_heuristics(text).is_err());
    }

    // frob:tests crates/crunk-spec/src/qa.rs::parse_walkthrough
    #[test]
    fn walkthrough_names_failed_questions() {
        let text = "screen = \"h\"\n[[steps]]\nname = \"s\"\ntries = true\nnotices = false\nassociates = true\nprogress = true\n";
        let w = parse_walkthrough(text).expect("ok");
        assert_eq!(w.steps[0].failed_questions().len(), 1);
    }

    // frob:tests crates/crunk-spec/src/qa.rs::load_qa
    #[test]
    fn load_tolerates_empty_and_refuses_duplicate_screens() {
        let dir = tempfile::tempdir().expect("tmp");
        assert!(load_qa(dir.path()).is_empty());
        let p = dir.path().join(HEURISTICS_DIR);
        std::fs::create_dir_all(&p).expect("mk");
        std::fs::write(p.join("a.toml"), "screen = \"x\"\n").expect("w");
        std::fs::write(p.join("b.toml"), "screen = \"x\"\n").expect("w");
        let set = load_qa(dir.path());
        assert_eq!(set.heuristics.len(), 1);
        assert_eq!(set.problems.len(), 1);
    }
}
