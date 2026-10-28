//! `needs` names language capabilities: a language whose matrix cell is not applicable makes the
//! rule `NotApplicable` statically, and `reads` names side relations (grl-spec.md section 4).

// frob:ticket 01M4CXV36WX1C2T64J454ECDV7

use gob_plan::examples::run_example;
use gob_plan::grl::parse;
use gob_plan::lower::{LowerError, lower_rule};
use gob_plan::plan::Provenance;
use gob_text::FileInterner;

/// A universal rule needing `test_items`, with a not-applicable example in `css` and a firing one
/// in `rust`.
fn rule_text(needs: &str, na_lang: &str) -> String {
    format!(
        r#"rule CAP900 "needs a capability" {{
  lang *
  polarity P-  severity error  scope file  rollup file
  needs {needs}

  find f: function
  report f "function {{f.name}}"
  example fire rust {{
    file "src/a.rs" """
      fn a() {{}}   //~ error
    """
  }}
  example clean rust {{
    file "src/a.rs" """
      struct S;
    """
  }}
  example notapplicable {na_lang} {{
    file "src/a.{na_lang}" """
      a {{ color: red; }}
    """
  }}
  explain """
    Test rule.
    ## Remedy
    None.
  """
}}
"#
    )
}

fn parsed(src: &str) -> gob_plan::grl::ast::Rule {
    let parsed = parse(FileInterner::new().intern("rules/CAP900.grl"), src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    parsed.file.rules[0].clone()
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn a_rule_needing_a_capability_the_language_lacks_is_not_applicable_statically() {
    let rule = parsed(&rule_text("test_items", "css"));
    let ex = rule.examples.last().expect("example");
    let result = run_example(&rule, ex).expect("runs");
    assert!(result.passed, "{result:?}");
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn a_rule_without_the_need_still_runs_on_that_language() {
    let rule = parsed(&rule_text("vocab(none)", "css").replace("needs vocab(none)", ""));
    let ex = rule.examples.last().expect("example");
    let result = run_example(&rule, ex).expect("runs");
    assert!(!result.passed, "{result:?}");
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn an_unknown_capability_is_a_lowering_error() {
    let rule = parsed(&rule_text("no_such_capability", "css"));
    let err = lower_rule(&rule, Provenance::Std).expect_err("refused");
    assert!(matches!(err, LowerError::UnknownNeed { .. }), "{err:?}");
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_capability_need_is_not_a_side_relation_read() {
    let rule = parsed(&rule_text("test_items", "css"));
    let plan = lower_rule(&rule, Provenance::Std).expect("lowers");
    assert!(plan.reads().iter().next().is_none());
}
