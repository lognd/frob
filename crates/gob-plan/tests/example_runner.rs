//! The example judge: markers per language, fire/clean/unresolved/notapplicable/known-gap, fixed.

// frob:ticket 01M3ZX7F8WQQ8JKW7GVVB2EYG6

use gob_plan::examples::{Expected, Level, Mark, expect_line, judge, judge_fixed, parse_markers};
use gob_plan::grl::ast::ExpectKind;

fn warn(line: u32) -> Expected {
    Expected {
        line,
        mark: Mark::Finding(Level::Error),
    }
}

const RUST: &str = "fn a() {}\nfn b() {\n    x.unwrap(); //~ error\n}\n";

// frob:tests crates/gob-plan/src/examples/judge.rs::judge
#[test]
fn a_marker_on_line_three_passes_iff_exactly_one_warn_is_reported_on_line_three() {
    let expected = parse_markers("rust", RUST);
    assert_eq!(expected, vec![warn(3)]);
    assert!(judge(ExpectKind::Fire, &expected, &[warn(3)], false).passed);
    assert!(!judge(ExpectKind::Fire, &expected, &[warn(2)], false).passed);
    assert!(!judge(ExpectKind::Fire, &expected, &[warn(3), warn(3)], false).passed);
    assert!(!judge(ExpectKind::Fire, &expected, &[], false).passed);
}

// frob:tests crates/gob-plan/src/examples/markers.rs::parse_markers
#[test]
fn each_language_family_uses_its_own_introducer_and_json_uses_expect_lines() {
    assert_eq!(parse_markers("python", "a\n#~ error\n")[0].line, 2);
    assert_eq!(parse_markers("lua", "x --~ error\n"), vec![warn(1)]);
    assert_eq!(parse_markers("html", "<p>\n<!--~ error -->\n")[0].line, 2);
    assert_eq!(
        parse_markers("rust", "x //~ unresolved\n")[0].mark,
        Mark::Unresolved
    );
    assert!(parse_markers("json", "//~ error\n").is_empty());
    assert_eq!(expect_line("line 3: error"), Some(warn(3)));
    assert_eq!(expect_line("nonsense"), None);
}

// frob:tests crates/gob-plan/src/examples/judge.rs::judge
#[test]
fn a_known_gap_that_starts_firing_fails_with_grl016_and_a_diff() {
    let ok = judge(ExpectKind::KnownGap, &[], &[], false);
    assert!(ok.passed);
    let bad = judge(ExpectKind::KnownGap, &[], &[warn(3)], false);
    assert!(!bad.passed);
    assert_eq!(bad.code, Some("GRL016"));
    assert!(
        bad.diff.contains("+ actual   line 3: error"),
        "{}",
        bad.diff
    );
}

// frob:tests crates/gob-plan/src/examples/judge.rs::judge
#[test]
fn a_mismatching_fire_prints_expected_and_actual_findings() {
    let r = judge(ExpectKind::Fire, &[warn(3)], &[warn(4)], false);
    assert_eq!(r.code, Some("GRL016"));
    assert_eq!(
        r.diff,
        "- expected line 3: error\n+ actual   line 4: error\n"
    );
}

// frob:tests crates/gob-plan/src/examples/judge.rs::judge
#[test]
fn clean_unresolved_and_notapplicable_follow_their_meaning() {
    assert!(judge(ExpectKind::Clean, &[], &[], false).passed);
    assert!(!judge(ExpectKind::Clean, &[], &[warn(1)], false).passed);
    let un = Expected {
        line: 2,
        mark: Mark::Unresolved,
    };
    assert!(judge(ExpectKind::Unresolved, &[un], &[un], false).passed);
    assert!(!judge(ExpectKind::Unresolved, &[un], &[warn(2)], false).passed);
    assert!(judge(ExpectKind::NotApplicable, &[], &[], true).passed);
    assert!(!judge(ExpectKind::NotApplicable, &[], &[], false).passed);
    assert!(!judge(ExpectKind::Fire, &[warn(1)], &[warn(1)], true).passed);
}

// frob:tests crates/gob-plan/src/examples/judge.rs::judge_fixed
#[test]
fn fixed_output_must_match_byte_for_byte() {
    assert!(judge_fixed("a\n", "a\n").passed);
    let r = judge_fixed("a\n", "b\n");
    assert_eq!(r.code, Some("GRL016"));
    assert!(r.diff.contains("- a") && r.diff.contains("+ b"));
}
