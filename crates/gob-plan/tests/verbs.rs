//! The library behind `rule test`, `rule check`, `rule catalog` and `rule fmt`.

// frob:ticket 01M3ZX7FCFBJSWMTZGCQMW7215

use gob_plan::verbs::catalog::lookup;
use gob_plan::verbs::check::check_source;
use gob_plan::verbs::fmt::{Formatted, format_text};
use gob_plan::verbs::test::{ExampleLine, test_file};

const RULE: &str = r#"rule NOPE001 "danger-call" {
  lang rust
  severity error
  find c: call where c.callee == "danger"
  report c "danger on line {c.line}"
  example fire rust """
    fn b() {
        danger(); //~ error
    }
  """
  example clean rust """
    fn b() {
        safe();
    }
  """
  explain """
    Danger bites.

    ## Remedy
    Call something safe.
  """
}
"#;

// frob:tests crates/gob-plan/src/verbs/test.rs::test_file
#[test]
fn test_prints_one_line_per_example_and_passes() {
    let r = test_file("rules/NOPE001.grl", RULE);
    assert!(r.passed(), "{r:?}");
    let lines: Vec<String> = r.examples.iter().map(ExampleLine::text).collect();
    assert_eq!(
        lines,
        vec![
            "NOPE001  fire   ok (1 finding on line 2)",
            "NOPE001  clean  ok"
        ]
    );
}

// frob:tests crates/gob-plan/src/verbs/test.rs::test_file
#[test]
fn test_fails_with_the_diff_when_an_example_is_wrong() {
    let bad = RULE.replace("safe();", "danger();");
    let r = test_file("rules/NOPE001.grl", &bad);
    assert!(!r.passed());
    let clean = &r.examples[1];
    assert_eq!(clean.status, "fail");
    assert!(
        clean.text().starts_with("NOPE001  clean  FAIL"),
        "{}",
        clean.text()
    );
    assert!(clean.diff.contains("+ actual"), "{}", clean.diff);
}

// frob:tests crates/gob-plan/src/verbs/test.rs::test_file
#[test]
fn test_runs_nothing_when_the_file_does_not_compile() {
    let r = test_file("rules/B.grl", &RULE.replace("call", "cal"));
    assert!(r.examples.is_empty());
    assert!(!r.passed());
    assert_eq!(r.diagnostics[0].code, "GRL001");
    assert!(r.diagnostics[0].line > 0);
}

// frob:tests crates/gob-plan/src/verbs/check.rs::check_source
#[test]
fn check_reports_cost_class_and_prefilter_or_coded_errors() {
    let ok = check_source("rules/NOPE001.grl", RULE);
    assert!(ok.ok(), "{ok:?}");
    assert_eq!(ok.rules[0].rule, "NOPE001");
    assert_eq!(ok.rules[0].cost, "per-file");
    assert!(
        ok.rules[0].text().starts_with("NOPE001  per-file"),
        "{}",
        ok.rules[0].text()
    );
    let bad = check_source("rules/B.grl", &RULE.replace("call", "cal"));
    assert!(!bad.ok());
    assert!(bad.rules.is_empty());
    assert_eq!(bad.diagnostics[0].code, "GRL001");
}

// frob:tests crates/gob-plan/src/verbs/catalog.rs::lookup
#[test]
fn catalog_returns_the_entry_or_a_did_you_mean() {
    let hit = lookup(Some("test"));
    assert_eq!(hit.entries[0].class, "kind");
    assert!(hit.did_you_mean.is_none());
    let miss = lookup(Some("tset"));
    assert!(miss.entries.is_empty());
    assert_eq!(miss.did_you_mean.as_deref(), Some("test"));
    assert!(lookup(Some("zzzzzzzz")).did_you_mean.is_none());
    assert!(lookup(None).entries.len() > 10);
}

// frob:tests crates/gob-plan/src/verbs/fmt.rs::format_text
#[test]
fn fmt_rewrites_to_the_canonical_layout_and_is_idempotent() {
    let messy = RULE.replace(
        "  lang rust\n  severity error\n",
        "lang rust severity error\n",
    );
    let Formatted::Changed(text) = format_text("rules/F.grl", &messy) else {
        panic!("expected a rewrite");
    };
    assert_eq!(format_text("rules/F.grl", &text), Formatted::Unchanged);
    assert!(matches!(
        format_text("rules/F.grl", "rule {"),
        Formatted::Skipped(_)
    ));
}
