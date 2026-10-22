//! COV004: `[[coverage.threshold]]` minimums against an lcov report.

// frob:ticket 01M4FD1NX760N78Z1T60MQ76H2

mod common;

use frob_obligations::InvariantsConfig;
use gob_rules::{Finding, Severity};

/// An lcov report: `src/a.rs` has 3 of 4 lines and 1 of 2 branches hit; `src/b.rs` 2 of 2 lines.
const REPORT: &str = "TN:\nSF:src/a.rs\nDA:1,1\nDA:2,1\nDA:3,0\nDA:4,5\nBRDA:2,0,0,1\nBRDA:2,0,1,-\nend_of_record\nSF:src/b.rs\nDA:1,2\nDA:2,1\nend_of_record\n";

/// Evaluate a tree holding `frob.toml` (`toml`) and, when given, `lcov.info` (`report`); return the COV004 findings.
fn cov004(toml: &str, report: Option<&str>) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[("frob.toml", toml), ("src/a.rs", "fn a() {}\n")],
    );
    if let Some(r) = report {
        common::write_tree(dir.path(), &[("lcov.info", r)]);
    }
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let eval = common::evaluate_tree(dir.path(), None, &config, None);
    eval.findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "COV004")
        .collect()
}

/// A one-entry threshold table for `scope` with `extra` keys.
fn table(scope: &str, extra: &str) -> String {
    format!("[[coverage.threshold]]\nscope = \"{scope}\"\n{extra}\n")
}

// frob:tests cov004
// frob:tests CoverageConfig.load
#[test]
fn report_under_threshold_names_scope_measured_and_required() {
    let found = cov004(&table("src/a.rs", "line = 80"), Some(REPORT));
    assert_eq!(found.len(), 1, "{found:?}");
    let f = &found[0];
    assert_eq!(f.severity, Severity::Error);
    assert!(f.message.contains("`src/a.rs`"), "{}", f.message);
    assert!(f.message.contains("line"), "{}", f.message);
    assert!(f.message.contains("75.00%"), "{}", f.message);
    assert!(f.message.contains("80.00%"), "{}", f.message);
}

// frob:tests cov004
#[test]
fn missing_report_is_unresolved() {
    let found = cov004(&table("src", "line = 80"), None);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Unresolved);
    assert!(found[0].message.contains("`src`"), "{}", found[0].message);
    assert!(
        found[0].message.contains("unreadable"),
        "{}",
        found[0].message
    );
}

// frob:tests cov004
#[test]
fn meeting_the_threshold_is_clean_and_directory_scopes_aggregate() {
    // src: 5 of 6 lines hit = 83.33%.
    assert!(cov004(&table("src", "line = 83"), Some(REPORT)).is_empty());
    assert_eq!(
        cov004(&table("src/**", "line = 83.34"), Some(REPORT)).len(),
        1
    );
    assert!(cov004(&table("src/a.rs", "line = 75"), Some(REPORT)).is_empty());
}

// frob:tests cov004
#[test]
fn branch_minimum_uses_branch_records() {
    let found = cov004(&table("src/a.rs", "branch = 60"), Some(REPORT));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("branch coverage 50.00%"),
        "{}",
        found[0].message
    );
    assert!(cov004(&table("src/a.rs", "branch = 50"), Some(REPORT)).is_empty());
}

// frob:tests cov004
#[test]
fn unmeasurable_entries_are_unresolved() {
    for (extra, scope) in [
        ("line = 50", "nothing/here"),
        ("branch = 50", "src/b.rs"),
        ("line = 101", "src"),
        ("", "src"),
        ("line = 50", "src/["),
    ] {
        let found = cov004(&table(scope, extra), Some(REPORT));
        assert_eq!(found.len(), 1, "{scope} {extra}: {found:?}");
        assert_eq!(found[0].severity, Severity::Unresolved, "{scope} {extra}");
    }
}

// frob:tests cov004
#[test]
fn repeated_records_merge_and_absolute_paths_are_rebased() {
    let dir = tempfile::tempdir().expect("tempdir");
    let abs = dir.path().join("src").join("a.rs");
    let report = format!(
        "SF:{p}\nDA:1,0\nDA:2,0\nend_of_record\nSF:./src/a.rs\nDA:1,3\nDA:2,0\nend_of_record\n",
        p = gob_path::Shown::of(&abs)
    );
    common::write_tree(
        dir.path(),
        &[
            ("frob.toml", &table("src/a.rs", "line = 60")),
            ("lcov.info", &report),
            ("src/a.rs", "fn a() {}\n"),
        ],
    );
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let eval = common::evaluate_tree(dir.path(), None, &config, None);
    let found: Vec<_> = eval
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV004")
        .collect();
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].message.contains("50.00%"), "{}", found[0].message);
}

// frob:tests cov004
#[test]
fn no_thresholds_means_no_findings_even_without_a_report() {
    assert!(cov004("", None).is_empty());
}

// frob:tests cov004
#[test]
fn acceptance_1_below_threshold_names_values_and_no_report_is_unresolved() {
    let table = table("src/a.rs", "line = 80\nbranch = 40");
    let under = cov004(&table, Some(REPORT));
    assert_eq!(under.len(), 1, "{under:?}");
    assert_eq!(under[0].severity, Severity::Error);
    for needle in ["src/a.rs", "line", "75.00%", "80.00%"] {
        assert!(under[0].message.contains(needle), "{}", under[0].message);
    }
    let none = cov004(&table, None);
    assert_eq!(none.len(), 1, "{none:?}");
    assert_eq!(none[0].severity, Severity::Unresolved);
}
