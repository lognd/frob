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
