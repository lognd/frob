//! The research-evidence checks: the acceptance cases and edge cases.

// frob:ticket 01M5XCYCSXSPQP9A4DZKNX5RGS

use std::collections::BTreeSet;

use crunk_rules::ux::research::{ResearchIssue, ScreenCitations, check_research_rules};
use crunk_spec::research::{
    Date, JourneyFile, PersonaFile, ResearchDoc, ResearchProblem, ResearchSet,
};

fn date(s: &str) -> Date {
    Date::parse(s).expect("date")
}

fn persona(id: &str, evidence: &[&str]) -> (String, PersonaFile) {
    (
        format!("design/personas/{id}.toml"),
        PersonaFile {
            id: id.to_owned(),
            name: None,
            evidence: evidence.iter().map(|e| (*e).to_owned()).collect(),
        },
    )
}

fn note(id: &str, when: &str) -> (String, ResearchDoc) {
    (
        format!("design/research/{id}.md"),
        ResearchDoc {
            id: id.to_owned(),
            date: date(when),
        },
    )
}

fn issues(set: &ResearchSet, screens: &[ScreenCitations]) -> Vec<ResearchIssue> {
    check_research_rules(set, screens, &BTreeSet::new(), date("2026-11-16"), 365)
        .into_iter()
        .map(|f| f.issue)
        .collect()
}

// frob:tests crates/crunk-rules/src/ux/research.rs::check_research_rules
#[test]
fn persona_and_journey_without_evidence_are_named() {
    let set = ResearchSet {
        personas: vec![persona("p", &[])],
        journeys: vec![(
            "design/journeys/j.toml".to_owned(),
            JourneyFile {
                id: "j".to_owned(),
                persona: Some("p".to_owned()),
                evidence: Vec::new(),
            },
        )],
        ..ResearchSet::default()
    };
    let found = check_research_rules(&set, &[], &BTreeSet::new(), date("2026-11-16"), 365);
    assert_eq!(found.len(), 2);
    assert!(found.iter().all(|f| f.issue == ResearchIssue::NoEvidence));
    assert!(found[0].message.contains("persona `p`"));
}

// frob:tests crates/crunk-rules/src/ux/research.rs::check_research_rules
#[test]
fn screen_without_citation_fires_and_cited_persona_is_clean() {
    let set = ResearchSet {
        research: vec![note("r", "2026-11-01")],
        personas: vec![persona("p", &["r"])],
        ..ResearchSet::default()
    };
    let bare = ScreenCitations {
        id: "home".to_owned(),
        cites: Vec::new(),
    };
    assert_eq!(issues(&set, &[bare]), [ResearchIssue::ScreenUncited]);
    let cited = ScreenCitations {
        id: "home".to_owned(),
        cites: vec!["p".to_owned()],
    };
    assert!(issues(&set, &[cited]).is_empty());
}

// frob:tests crates/crunk-rules/src/ux/research.rs::check_research_rules
#[test]
fn old_research_is_stale_and_boundary_is_not() {
    let set = ResearchSet {
        research: vec![note("old", "2025-01-01"), note("edge", "2025-11-16")],
        ..ResearchSet::default()
    };
    assert_eq!(issues(&set, &[]), [ResearchIssue::Stale]);
}

// frob:tests crates/crunk-rules/src/ux/research.rs::check_research_rules
#[test]
fn dangling_citation_is_a_dangling_finding() {
    let set = ResearchSet {
        personas: vec![persona("p", &["gone"])],
        ..ResearchSet::default()
    };
    assert_eq!(issues(&set, &[]), [ResearchIssue::Dangling]);
}

// frob:tests crates/crunk-rules/src/ux/research.rs::check_research_rules
#[test]
fn load_problems_are_located_schema_findings_and_empty_set_is_silent() {
    let empty = ResearchSet::default();
    let bare = ScreenCitations {
        id: "s".to_owned(),
        cites: Vec::new(),
    };
    assert!(issues(&empty, &[bare]).is_empty());
    let bad = ResearchSet {
        problems: vec![ResearchProblem {
            path: "design/research/a.md".to_owned(),
            line: Some(3),
            message: "malformed front matter line".to_owned(),
        }],
        ..ResearchSet::default()
    };
    let found = check_research_rules(&bad, &[], &BTreeSet::new(), date("2026-11-16"), 365);
    assert_eq!(found[0].issue, ResearchIssue::Schema);
    assert_eq!(found[0].line, Some(3));
}
