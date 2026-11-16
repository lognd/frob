//! The game-artifact checks: the acceptance cases and edge cases.

// frob:ticket 01M5XCZ1FM4GWNE4T7SQ905APV

use crunk_rules::gx_files::{GxFileContext, GxFileFinding, GxFileIssue, check_gx_files};
use crunk_spec::game_files::{
    FeedbackFile, FtueFile, GameSet, GxFile, HudElement, InputFile, parse_feedback, parse_ftue,
    parse_gx, parse_input,
};
use crunk_spec::research::ResearchProblem;

fn names(items: &[&str]) -> std::collections::BTreeSet<String> {
    items.iter().map(|s| (*s).to_owned()).collect()
}

fn ctx() -> GxFileContext {
    GxFileContext {
        devices: names(&["pad", "kbd"]),
        profiles: names(&["tv"]),
        mechanics: names(&["dash"]),
        toggles: names(&["no-shake"]),
    }
}

fn issues(found: Vec<GxFileFinding>) -> Vec<GxFileIssue> {
    found.into_iter().map(|f| f.issue).collect()
}

fn ftue(text: &str) -> GameSet {
    let file: FtueFile = parse_ftue(text).expect("ftue");
    GameSet {
        ftue: Some(file),
        ..GameSet::default()
    }
}

fn feedback(text: &str) -> GameSet {
    let file: FeedbackFile = parse_feedback(text).expect("feedback");
    GameSet {
        feedback: Some(file),
        ..GameSet::default()
    }
}

fn gx(text: &str) -> GameSet {
    let file: GxFile = parse_gx(text).expect("gx");
    GameSet {
        gx: Some(file),
        ..GameSet::default()
    }
}

fn input(text: &str) -> GameSet {
    let file: InputFile = parse_input(text).expect("input");
    GameSet {
        input: Some(file),
        ..GameSet::default()
    }
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn mechanic_without_ftue_entry_fires() {
    let found = check_gx_files(&ftue("[[entries]]\nmechanic = \"jump\"\n"), &ctx());
    assert_eq!(issues(found), [GxFileIssue::NoFtue]);
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn explicit_none_satisfies_ftue() {
    let set = ftue("[[entries]]\nmechanic = \"dash\"\nnone = true\n");
    assert!(check_gx_files(&set, &ctx()).is_empty());
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn feedback_event_without_toggle_fires() {
    let found = check_gx_files(&feedback("[[events]]\nevent = \"hit\"\n"), &ctx());
    assert_eq!(issues(found), [GxFileIssue::NoToggle]);
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn feedback_toggle_not_declared_is_unresolved() {
    let set = feedback("[[events]]\nevent = \"hit\"\ntoggle = \"ghost\"\n");
    assert_eq!(
        issues(check_gx_files(&set, &ctx())),
        [GxFileIssue::Unresolved]
    );
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn met_guideline_without_evidence_fires() {
    let found = check_gx_files(&gx("[[items]]\nid = \"subtitles\"\nmet = true\n"), &ctx());
    assert_eq!(issues(found), [GxFileIssue::NoEvidence]);
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn met_guideline_with_evidence_is_clean() {
    let set = gx("[[items]]\nid = \"subtitles\"\nmet = true\nevidence = \"video\"\n");
    assert!(check_gx_files(&set, &ctx()).is_empty());
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn missing_glyph_is_reported_once_per_device() {
    let set =
        input("[[actions]]\naction = \"a\"\nglyphs = [\"pad\"]\n[[actions]]\naction = \"b\"\n");
    let found = check_gx_files(&set, &ctx());
    assert_eq!(issues(found), [GxFileIssue::NoGlyph, GxFileIssue::NoGlyph]);
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn hud_element_outside_profiles_is_unresolved() {
    let set = GameSet {
        hud: vec![(
            "design/game/hud/h.toml".to_owned(),
            HudElement {
                element: "health".to_owned(),
                profile: "phone".to_owned(),
            },
        )],
        ..GameSet::default()
    };
    assert_eq!(
        issues(check_gx_files(&set, &ctx())),
        [GxFileIssue::Unresolved]
    );
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn absent_files_are_silent() {
    assert!(check_gx_files(&GameSet::default(), &ctx()).is_empty());
}

// frob:tests crates/crunk-rules/src/gx_files.rs::check_gx_files
#[test]
fn load_problems_are_located_schema_findings() {
    let bad = GameSet {
        problems: vec![ResearchProblem {
            path: "design/game/gx-a11y.toml".to_owned(),
            line: Some(3),
            message: "unknown guideline id".to_owned(),
        }],
        ..GameSet::default()
    };
    let found = check_gx_files(&bad, &ctx());
    assert_eq!(found[0].issue, GxFileIssue::Schema);
    assert_eq!(found[0].line, Some(3));
}
