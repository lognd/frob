//! COV005: `[[testing.threshold]]` unit case minimums against the test functions of a scope.

// frob:ticket 01M5HT58NK23KQMMVXD1FZ0R2D

use crate::common;

use frob_obligations::InvariantsConfig;
use gob_rules::{Finding, Severity};

/// A source file holding two test functions.
const TWO_TESTS: &str = "pub fn a() {}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn one() {}\n\n    #[test]\n    fn two() {}\n}\n";

/// Evaluate a tree holding `frob.toml` (`toml`) and `src/a.rs`; return the COV005 findings.
fn cov005(toml: &str) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("frob.toml", toml), ("src/a.rs", TWO_TESTS)]);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let eval = common::evaluate_tree(dir.path(), None, &config, None);
    eval.findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "COV005")
        .collect()
}

/// A one-entry minimum table for `scope` requiring `min` cases.
fn table(scope: &str, min: u64) -> String {
    format!("[[testing.threshold]]\nscope = \"{scope}\"\nmin_unit_cases = {min}\n")
}

// frob:tests crates/frob-obligations/src/unit_cases.rs::cov005
#[test]
fn below_minimum_names_scope_and_shortfall() {
    let found = cov005(&table("src", 5));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Error);
    assert!(found[0].message.contains("`src`"), "{}", found[0].message);
    assert!(
        found[0].message.contains("short by 3"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/frob-obligations/src/unit_cases.rs::cov005
#[test]
fn at_the_minimum_passes() {
    assert!(cov005(&table("src", 2)).is_empty());
}

// frob:tests crates/frob-obligations/src/unit_cases.rs::cov005
#[test]
fn above_the_minimum_passes() {
    assert!(cov005(&table("src/a.rs", 1)).is_empty());
}

// frob:tests crates/frob-obligations/src/unit_cases.rs::cov005
#[test]
fn an_empty_scope_falls_short_of_any_minimum() {
    let found = cov005(&table("elsewhere", 1));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("0 unit cases"),
        "{}",
        found[0].message
    );
}

// frob:tests crates/frob-obligations/src/unit_cases.rs::cov005
#[test]
fn an_invalid_glob_is_unresolved() {
    let found = cov005(&table("src/[", 1));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Unresolved);
}
