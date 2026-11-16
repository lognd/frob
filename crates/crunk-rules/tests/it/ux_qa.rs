//! The QA checks: the acceptance cases and edge cases.

// frob:ticket 01M5XCZ14WCPMG9R6E269QRPVH

use crunk_rules::ux::qa::{QaFinding, QaIssue, check_qa_rules};
use crunk_spec::qa::{
    Heuristic, HeuristicFile, HeuristicFinding, QaSet, WalkthroughFile, WalkthroughStep,
};
use crunk_spec::research::ResearchProblem;

fn heur(screen: &str, severity: u8, owner: Option<&str>, evidence: Option<&str>) -> QaSet {
    let finding = HeuristicFinding {
        heuristic: Heuristic::ErrorPrevention,
        severity,
        owner: owner.map(str::to_owned),
        evidence: evidence.map(str::to_owned),
        note: None,
    };
    QaSet {
        heuristics: vec![(
            format!("design/qa/heuristics/{screen}.toml"),
            HeuristicFile {
                screen: screen.to_owned(),
                reviewed: Vec::new(),
                findings: vec![finding],
            },
        )],
        ..QaSet::default()
    }
}

fn walk(answers: [bool; 4]) -> QaSet {
    let [tries, notices, associates, progress] = answers;
    QaSet {
        walkthroughs: vec![(
            "design/qa/walkthroughs/home.toml".to_owned(),
            WalkthroughFile {
                screen: "home".to_owned(),
                steps: vec![WalkthroughStep {
                    name: "open".to_owned(),
                    tries,
                    notices,
                    associates,
                    progress,
                }],
            },
        )],
        ..QaSet::default()
    }
}

fn issues(found: Vec<QaFinding>) -> Vec<QaIssue> {
    found.into_iter().map(|f| f.issue).collect()
}

fn home() -> Vec<String> {
    vec!["home".to_owned()]
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn a_no_answer_fails_the_step_and_names_the_question() {
    let found = check_qa_rules(&walk([true, false, true, true]), &[]);
    assert_eq!(issues(found.clone()), [QaIssue::WalkthroughFailed]);
    assert!(found[0].message.contains("notice"));
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn all_yes_walkthrough_is_clean() {
    assert!(check_qa_rules(&walk([true; 4]), &[]).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn major_finding_without_owner_fires() {
    let found = check_qa_rules(&heur("home", 3, None, Some("shot")), &home());
    assert_eq!(issues(found), [QaIssue::NoOwner]);
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn minor_finding_without_owner_is_clean() {
    assert!(check_qa_rules(&heur("home", 2, None, Some("shot")), &home()).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn finding_without_evidence_fires() {
    let found = check_qa_rules(&heur("home", 1, None, None), &home());
    assert_eq!(issues(found), [QaIssue::NoEvidence]);
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn screen_without_heuristic_coverage_fires() {
    let found = check_qa_rules(&heur("home", 1, None, Some("s")), &["other".to_owned()]);
    assert_eq!(issues(found), [QaIssue::NoCoverage]);
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn empty_qa_set_is_silent() {
    assert!(check_qa_rules(&QaSet::default(), &home()).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/qa.rs::check_qa_rules
#[test]
fn load_problems_are_located_schema_findings() {
    let bad = QaSet {
        problems: vec![ResearchProblem {
            path: "design/qa/heuristics/a.toml".to_owned(),
            line: Some(2),
            message: "unknown variant".to_owned(),
        }],
        ..QaSet::default()
    };
    let found = check_qa_rules(&bad, &[]);
    assert_eq!(found[0].issue, QaIssue::Schema);
    assert_eq!(found[0].line, Some(2));
}
