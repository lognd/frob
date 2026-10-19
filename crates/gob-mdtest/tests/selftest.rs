//! Self-tests: a toy rule MDT001 (and MDT002 as a warn) over the corpora.

use gob_mdtest::{Case, Missing, Runner, run_dir, run_file};
use gob_rules::{Finding, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};

/// Fires on every line containing `forbidden`; MDT002 reports it as a warning.
fn toy(case: &Case) -> Vec<Finding> {
    let file = FileInterner::new().intern(&case.file_name);
    let mut out = Vec::new();
    let mut off = 0usize;
    for line in case.text.split_inclusive('\n') {
        if line.contains("forbidden") {
            let start = TextSize::try_from(off).unwrap();
            let len = TextSize::try_from(line.len()).unwrap();
            let span = Span::new(file, TextRange::at(start, len));
            let sev = if case.rule.as_str() == "MDT002" {
                Severity::Warn
            } else {
                Severity::Error
            };
            out.push(Finding::new(
                case.rule.clone(),
                sev,
                Some(span),
                "forbidden word",
                &case.file_name,
            ));
        }
        off += line.len();
    }
    out
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = toy);

fn fail_path(name: &str) -> std::path::PathBuf {
    gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR"))
        .join("tests/mdtest_fail")
        .join(name)
}

#[test]
fn wrong_line_fails_showing_both_lines() {
    let r = run_file(&fail_path("wrong_line.md"), &Runner::new(toy));
    assert!(!r.passed());
    let text = r.render_failures();
    assert!(text.contains("   2 | Error MDT001 | -"), "{text}");
    assert!(text.contains("   3 | - | Error MDT001"), "{text}");
}

#[test]
fn missing_control_fails_naming_rule() {
    let r = run_file(&fail_path("missing_control.md"), &Runner::new(toy));
    assert!(!r.passed());
    assert_eq!(r.missing.len(), 1);
    assert_eq!(r.missing[0].rule.as_str(), "MDT001");
    assert_eq!(r.missing[0].missing, Missing::Clean);
    assert!(r.render_failures().contains("MDT001"));
}

#[test]
fn fail_dir_reports_every_file() {
    let rep = run_dir(&fail_path(""), &Runner::new(toy));
    assert_eq!(rep.files.len(), 2);
    assert!(!rep.passed());
    assert!(rep.render().contains("FAIL"));
}

gob_mdtest::mdtest!(
    name = mdtest_snapshots,
    dir = "tests/mdtest_snap",
    runner = toy
);

#[test]
fn changed_rendering_fails_with_snapshot_mismatch() {
    let dir = std::env::temp_dir().join(format!("gob-mdtest-snap-{}", std::process::id()));
    let snaps = dir.join("snapshots");
    std::fs::create_dir_all(&snaps).unwrap();
    let src = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR")).join("tests/mdtest_snap");
    std::fs::copy(src.join("snap.md"), dir.join("snap.md")).unwrap();
    for e in std::fs::read_dir(src.join("snapshots")).unwrap() {
        let e = e.unwrap();
        let body = std::fs::read_to_string(e.path())
            .unwrap()
            .replace("forbidden word", "changed word");
        std::fs::write(snaps.join(e.file_name()), body).unwrap();
    }
    let r = run_file(&dir.join("snap.md"), &Runner::new(toy));
    assert!(!r.passed());
    assert!(
        r.render_failures().contains("does not match"),
        "{}",
        r.render_failures()
    );
    let _ = std::fs::remove_dir_all(&dir);
}

/// The same toy, returning the full per-rule report instead of bare findings.
fn toy_report(case: &Case) -> gob_rules::RuleReport {
    let findings = toy(case);
    let n = case.text.lines().count();
    gob_rules::RuleReport::new(case.rule.clone(), n, n, None, findings)
}

// frob:tests crates/gob-mdtest/src/run.rs::Runner
#[test]
fn a_runner_may_return_a_rule_report() {
    let bare = run_dir(&fail_path(""), &Runner::new(toy));
    let full = run_dir(&fail_path(""), &Runner::new(toy_report));
    assert_eq!(bare.render(), full.render());
    let ok = run_dir(
        &gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR")).join("tests/mdtest"),
        &Runner::new(toy_report),
    );
    assert!(ok.passed(), "{}", ok.render());
}

/// Extended toy: columns at the word, plus advisory, unresolved (hole, optionally required) and two-hit lines.
fn toy_ext(case: &Case) -> Vec<Finding> {
    let file = FileInterner::new().intern(&case.file_name);
    let mut out = Vec::new();
    let mut off = 0usize;
    for line in case.text.split_inclusive('\n') {
        for (word, sev, msg) in [
            ("forbidden", Severity::Error, "forbidden word"),
            ("advisory_word", Severity::Advisory, "advisory advice"),
            ("unsure_req", Severity::Unresolved, "undecided required"),
            ("unsure;", Severity::Unresolved, "undecided"),
            ("twice", Severity::Error, "first hit"),
            ("twice", Severity::Error, "second hit"),
        ] {
            let Some(at) = line.find(word) else { continue };
            let start = TextSize::try_from(off + at).unwrap();
            let len = TextSize::try_from(word.len()).unwrap();
            let span = Span::new(file, TextRange::at(start, len));
            let mut f = Finding::new(case.rule.clone(), sev, Some(span), msg, &case.file_name);
            if sev == Severity::Unresolved {
                f.reason = Some(gob_rules::UnresolvedReason::Hole);
                if word == "unsure_req" {
                    f.required = Some(gob_rules::RequiredReason::ZeroSubjects {
                        rule: case.rule.to_string(),
                    });
                }
            }
            out.push(f);
        }
        off += line.len();
    }
    out
}

gob_mdtest::mdtest!(
    name = mdtest_ext_forms,
    dir = "tests/mdtest_ext",
    runner = toy_ext
);

fn ext_fail(name: &str) -> String {
    let path = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR"))
        .join("tests/mdtest_fail_ext")
        .join(name);
    let r = run_file(&path, &Runner::new(toy_ext));
    assert!(!r.passed(), "{name} should fail");
    r.render_failures()
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn wrong_rule_in_a_marker_fails() {
    let t = ext_fail("wrong_rule.md");
    assert!(t.contains("Error MDT002 | Error MDT001"), "{t}");
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn wrong_column_fails_showing_both_columns() {
    let t = ext_fail("wrong_column.md");
    assert!(
        t.contains("Error MDT001 [col 1] | Error MDT001 [col 9]"),
        "{t}"
    );
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn wrong_message_fails_showing_both_messages() {
    let t = ext_fail("wrong_message.md");
    assert!(t.contains("\"no such text\""), "{t}");
    assert!(t.contains("\"forbidden word\""), "{t}");
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn expected_unresolved_but_got_error_fails() {
    let t = ext_fail("unresolved_got_error.md");
    assert!(t.contains("Unresolved[hole] MDT001 | Error MDT001"), "{t}");
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn differing_unresolved_reason_fails() {
    let t = ext_fail("wrong_reason.md");
    assert!(
        t.contains("Unresolved[partial] MDT001 | Unresolved[hole] MDT001"),
        "{t}"
    );
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn own_line_marker_applies_to_the_next_line_even_if_blank() {
    let t = ext_fail("own_line_wrong_target.md");
    assert!(t.contains("!    1") || t.contains("!    2"), "{t}");
    assert!(t.contains("!    3"), "{t}");
}

/// The toy plus a stray MDT009 Error and an MDT001 Advisory on every case.
fn noisy(case: &Case) -> Vec<Finding> {
    let file = FileInterner::new().intern(&case.file_name);
    let span = Span::new(file, TextRange::at(TextSize::from(0), TextSize::from(1)));
    let mut out = toy(case);
    out.push(Finding::new(
        "MDT009".parse().unwrap(),
        Severity::Error,
        Some(span),
        "second rule",
        &case.file_name,
    ));
    out.push(Finding::new(
        case.rule.clone(),
        Severity::Advisory,
        Some(span),
        "side note",
        &case.file_name,
    ));
    out
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn an_unexpected_second_rule_or_advisory_fails_the_case() {
    let dir = std::env::temp_dir().join(format!("gob-mdtest-strict-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("s.md");
    std::fs::write(
        &path,
        "<!-- mdtest: rule=MDT001 -->\n```txt expect=fire rules=MDT009\nforbidden\n```\n```txt expect=clean\nok\n```\n",
    )
    .unwrap();
    let r = run_file(&path, &Runner::new(noisy));
    std::fs::remove_dir_all(&dir).ok();
    assert!(!r.passed());
    let text = r.render_failures();
    assert!(text.contains("unexpected findings"), "{text}");
    // the unselected-rule case (second block, no rules=) ignores MDT009
    assert!(
        r.cases[1].outcome.is_err(),
        "clean block sees its own advisory"
    );
    assert!(
        text.contains("class=fire severity=Error reason=- rule=MDT009"),
        "{text}"
    );
    assert!(
        text.contains("class=advisory severity=Advisory reason=- rule=MDT001"),
        "{text}"
    );
}

/// Returns one spanless Unresolved finding of the rule under test.
fn rolled_up(case: &Case) -> Vec<Finding> {
    vec![
        Finding::new(
            case.rule.clone(),
            Severity::Unresolved,
            None,
            "rolled up",
            &case.file_name,
        )
        .with_reason(gob_rules::UnresolvedReason::from_code("hole")),
    ]
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn a_spanless_unresolved_is_matched_by_the_header_assertion_only() {
    let dir = std::env::temp_dir().join(format!("gob-mdtest-rollup-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("s.md");
    std::fs::write(
        &path,
        "<!-- mdtest: rule=MDT001 -->\n```txt expect=unresolved reason=hole\nx\n```\n```txt expect=fire\nx\n```\n",
    )
    .unwrap();
    let r = run_file(&path, &Runner::new(rolled_up));
    std::fs::remove_dir_all(&dir).ok();
    assert!(r.cases[0].outcome.is_ok(), "{}", r.render_failures());
    let e = r.cases[1].outcome.clone().unwrap_err();
    assert!(
        e.contains("not Unresolved") || e.contains("unexpected"),
        "{e}"
    );
}
