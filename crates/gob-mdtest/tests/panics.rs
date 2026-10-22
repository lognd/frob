//! Panic containment and `expect-panic`: a panicking runner fails one case, not the run.

// frob:ticket 01M48PC1C64V7SN640NSASXGW5

use gob_mdtest::garbage::{PROBES, check_garbage};
use gob_mdtest::matrix::CELLS;
use gob_mdtest::{Case, FileReport, ParseError, Runner, parse_suite, run_file};
use gob_rules::{Finding, RuleId, RuleReport, Severity, UnresolvedReason};

/// Panics on `@panic MSG` (str payload), `@panic-fmt MSG` (String), `@panic-any`; `@error` yields a finding.
fn panicky(case: &Case) -> Vec<Finding> {
    let mut out = Vec::new();
    for line in case.text.lines() {
        if let Some(m) = line.strip_prefix("@panic-fmt ") {
            panic!("{m} {}", 1);
        } else if line.starts_with("@panic-any") {
            std::panic::panic_any(7_u8);
        } else if line.starts_with("@panic") {
            panic!("rule exploded");
        } else if line.starts_with("@error") {
            out.push(Finding::new(
                case.rule.clone(),
                Severity::Error,
                None,
                "bad",
                &case.file_name,
            ));
        }
    }
    out
}

const HEADER: &str = "<!-- mdtest: rule=MDT001 -->\n";
const CONTROLS: &str = "```txt expect=fire\n@error\n```\n```txt expect=clean\nok\n```\n";

fn run(md: &str) -> FileReport {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("s.md");
    std::fs::write(&path, md).unwrap();
    run_file(&path, &Runner::new(panicky))
}

fn failure_of(r: &FileReport, i: usize) -> String {
    r.cases[i].outcome.clone().unwrap_err()
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn panic_fails_that_case_with_its_line_and_the_rest_still_run() {
    let r = run(&format!(
        "{HEADER}{CONTROLS}```txt expect=fire\n@panic\n```\n```txt expect=fire\n@panic-fmt boom\n```\n```txt expect=fire\n@error\n```\n"
    ));
    assert!(!r.passed());
    assert_eq!(r.cases.len(), 5);
    assert!(r.cases[0].outcome.is_ok() && r.cases[1].outcome.is_ok());
    let a = failure_of(&r, 2);
    assert!(a.contains("panicked at markdown line 8"), "{a}");
    assert!(a.contains("rule exploded"), "{a}");
    assert!(failure_of(&r, 3).contains("boom 1"));
    assert!(r.cases[4].outcome.is_ok(), "a case after two panics runs");
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn non_string_payload_is_reported_with_a_placeholder() {
    let r = run(&format!(
        "{HEADER}{CONTROLS}```txt expect=fire\n@panic-any\n```\n"
    ));
    assert!(failure_of(&r, 2).contains("<non-string panic payload>"));
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn expect_panic_passes_on_a_matching_panic() {
    let r = run(&format!(
        "{HEADER}{CONTROLS}<!-- expect-panic: exploded -->\n```txt expect=fire\n@panic\n```\n"
    ));
    assert!(r.passed(), "{}", r.render_failures());
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn expect_panic_fails_when_nothing_panics() {
    let r = run(&format!(
        "{HEADER}{CONTROLS}<!-- expect-panic: exploded -->\n```txt expect=fire\n@error\n```\n"
    ));
    let e = failure_of(&r, 2);
    assert!(e.contains("expected the runner to panic"), "{e}");
    assert!(e.contains("`exploded`"), "{e}");
    assert!(!e.contains("also failed"), "{e}");
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn expect_panic_fails_on_a_different_message() {
    let r = run(&format!(
        "{HEADER}{CONTROLS}<!-- expect-panic: other words -->\n```txt expect=fire\n@panic\n```\n"
    ));
    let e = failure_of(&r, 2);
    assert!(
        e.contains("expected a panic containing `other words`"),
        "{e}"
    );
    assert!(e.contains("rule exploded"), "{e}");
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn empty_expect_panic_accepts_any_panic_but_still_needs_one() {
    let any = run(&format!(
        "{HEADER}{CONTROLS}<!-- expect-panic: -->\n```txt expect=fire\n@panic-any\n```\n<!-- expect-panic -->\n```txt expect=fire\n@panic\n```\n"
    ));
    assert!(any.passed(), "{}", any.render_failures());
    let none = run(&format!(
        "{HEADER}{CONTROLS}<!-- expect-panic: -->\n```txt expect=clean\nok\n```\n"
    ));
    let e = failure_of(&none, 2);
    assert!(
        e.contains("expected the runner to panic, but it returned"),
        "{e}"
    );
}

// frob:tests crates/gob-mdtest/src/run.rs::run_case
#[test]
fn no_panic_and_another_failure_reports_both() {
    let r = run(&format!(
        "{HEADER}{CONTROLS}<!-- expect-panic: x -->\n```txt expect=fire\nnothing\n```\n"
    ));
    let e = failure_of(&r, 2);
    assert!(e.contains("expected the runner to panic"), "{e}");
    assert!(e.contains("also failed its expectations"), "{e}");
}

// frob:tests crates/gob-mdtest/src/parse.rs::expect_panic_of
#[test]
fn directive_binds_to_the_next_case_only_and_survives_crlf() {
    let md = format!("{HEADER}{CONTROLS}<!-- expect-panic: exploded -->\n```txt expect=fire\n@panic\n```\n```txt expect=fire\n@error\n```\n")
        .replace('\n', "\r\n");
    let blocks = parse_suite(&md).unwrap();
    assert_eq!(blocks[2].expect_panic.as_deref(), Some("exploded"));
    assert!(blocks[3].expect_panic.is_none());
    // CRLF does not shift the attributed line: the third case fence is line 9.
    assert_eq!(blocks[2].fence_line, 9);
    let r = run(&md);
    assert!(r.passed(), "{}", r.render_failures());
}

// frob:tests crates/gob-mdtest/src/parse.rs::parse_outside
#[test]
fn dangling_or_doubled_directive_is_a_parse_error() {
    let dangling: ParseError =
        parse_suite(&format!("{HEADER}{CONTROLS}<!-- expect-panic: a -->\n")).unwrap_err();
    assert!(dangling.message.contains("not followed"), "{dangling}");
    let doubled = parse_suite(&format!(
        "{HEADER}<!-- expect-panic: a -->\n<!-- expect-panic: b -->\n```txt expect=fire\n@panic\n```\n"
    ))
    .unwrap_err();
    assert!(doubled.message.contains("second expect-panic"), "{doubled}");
}

// frob:tests crates/gob-mdtest/src/contain.rs::contained
#[test]
fn parallel_panics_do_not_leak_between_threads() {
    let handles: Vec<_> = (0..4)
        .map(|i| std::thread::spawn(move || run(&format!(
            "{HEADER}{CONTROLS}<!-- expect-panic: exploded -->\n```txt expect=fire\n@panic\n```\n```txt expect=fire\n@panic-fmt t{i}\n```\n"
        ))))
        .collect();
    for (i, h) in handles.into_iter().enumerate() {
        let r = h.join().unwrap();
        assert!(r.cases[2].outcome.is_ok());
        assert!(failure_of(&r, 3).contains(&format!("t{i} 1")));
    }
}

fn rule() -> RuleId {
    "MDT001".parse().unwrap()
}

/// Reports Unresolved on everything, as a well-behaved rule does for unparseable input.
fn unresolved_all(case: &Case) -> Vec<Finding> {
    vec![
        Finding::new(
            case.rule.clone(),
            Severity::Unresolved,
            None,
            "cannot parse",
            &case.file_name,
        )
        .with_reason(UnresolvedReason::from_code("hole")),
    ]
}

// frob:tests crates/gob-mdtest/src/garbage.rs::check_garbage
#[test]
fn probes_cover_every_matrix_cell_in_order() {
    let cells: Vec<_> = PROBES.iter().map(|p| p.cell).collect();
    assert_eq!(cells, CELLS);
}

// frob:tests crates/gob-mdtest/src/garbage.rs::check_garbage
#[test]
fn unresolved_or_not_applicable_on_garbage_satisfies_the_contract() {
    assert!(check_garbage(&Runner::new(unresolved_all), &rule(), &CELLS).is_empty());
    let na =
        |case: &Case| RuleReport::new(case.rule.clone(), 0, 0, Some("binary".into()), Vec::new());
    assert!(check_garbage(&Runner::new(na), &rule(), &CELLS).is_empty());
}

// frob:tests crates/gob-mdtest/src/garbage.rs::check_garbage
#[test]
fn garbage_that_panics_errors_or_is_silent_is_reported_per_cell() {
    let boom = |_: &Case| -> Vec<Finding> { panic!("parser bug") };
    let f = check_garbage(&Runner::new(boom), &rule(), &CELLS);
    assert_eq!(f.len(), CELLS.len());
    assert!(f[0].why.contains("panicked: parser bug"), "{}", f[0]);

    let error = |c: &Case| -> Vec<Finding> {
        vec![Finding::new(
            c.rule.clone(),
            Severity::Error,
            None,
            "x",
            &c.file_name,
        )]
    };
    let f = check_garbage(&Runner::new(error), &rule(), &["rust"]);
    assert!(f[0].why.contains("only Unresolved"), "{}", f[0]);

    let silent = |_: &Case| -> Vec<Finding> { Vec::new() };
    let f = check_garbage(&Runner::new(silent), &rule(), &["python"]);
    assert!(f[0].why.contains("neither Unresolved nor NotApplicable"));

    let f = check_garbage(&Runner::new(unresolved_all), &rule(), &["cobol"]);
    assert_eq!(f[0].cell, "cobol");
}
