//! Running examples end to end: lower, build the model from source, execute, judge.

// frob:ticket 01M4M99GMQDG93W4X05A4HFP5X

use gob_plan::examples::run_example;
use gob_plan::grl::parse;
use gob_text::FileInterner;

const RULE: &str = r#"rule DNG001 "danger-call" {
  lang rust
  severity error
  find c: call where c.callee == "danger"
  report c "danger on line {c.line}"
  example fire rust """
    fn a() {}
    fn b() {
        danger(); //~ error
    }
  """
  example clean rust """
    fn a() {}
    fn b() {
        danger(); //~ error
    }
  """
  explain """
    Danger bites.
  """
}
"#;

fn results(src: &str) -> Vec<gob_plan::examples::ExampleResult> {
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), src);
    assert!(parsed.is_ok(), "{:?}", parsed.errors);
    let rule = &parsed.file.rules[0];
    rule.examples
        .iter()
        .map(|e| run_example(rule, e).expect("example runs"))
        .collect()
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn a_fire_example_with_one_violation_on_line_three_passes() {
    let r = results(RULE);
    assert!(r[0].passed, "{}", r[0].diff);
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn a_clean_variant_of_a_violating_source_fails_with_grl016_and_a_diff() {
    let r = results(RULE);
    assert!(!r[1].passed);
    assert_eq!(r[1].code, Some("GRL016"));
    assert!(
        r[1].diff.contains("+ actual   line 3: error"),
        "{}",
        r[1].diff
    );
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn a_fire_example_whose_source_has_no_violation_fails() {
    let src = RULE.replace("danger(); //~ error", "safe(); //~ error");
    let r = results(&src);
    assert!(!r[0].passed);
    assert_eq!(r[0].code, Some("GRL016"));
}
