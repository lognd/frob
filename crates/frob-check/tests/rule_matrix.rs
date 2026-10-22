//! Every Universal frob rule fills the language matrix, with expectations derived from its needs.

// frob:ticket 01M48Q4DMNMQEYQNWPK42DZ0RZ

// The rule crates are linked only for their inventory registrations.
use frob_check as _;

use frob_check::{CheckOptions, run};
use gob_check::SubjectStatus;
use gob_check::applicability::{Applies, derive_cell, temporary_applies};

use gob_mdtest::garbage::check_garbage;
use gob_mdtest::matrix::Derived;
use gob_mdtest::{Case, Runner};
use gob_rules::{Registry, RuleReport};

/// The `frob` rules whose declared applicability is Universal.
fn universal_rules() -> Vec<String> {
    Registry::global()
        .iter()
        .filter(|m| m.product == "frob")
        .filter(|m| matches!(temporary_applies(m), Applies::Universal { .. }))
        .map(|m| m.id.to_owned())
        .collect()
}

/// The derived class of `rule` in `cell`, from its declared `applies` and the capability matrix.
fn derive(rule: &str, cell: &str) -> Option<Derived> {
    let meta = Registry::global().iter().find(|m| m.id == rule)?;
    Some(match derive_cell(&temporary_applies(meta), cell)? {
        SubjectStatus::Examine => Derived::Examine,
        SubjectStatus::Unresolved(_) => Derived::Unresolved,
        SubjectStatus::NotApplicable(_) => Derived::NotApplicable,
    })
}

// frob:tests crates/gob-mdtest/src/matrix.rs::assert_matrix
#[test]
fn every_universal_frob_rule_fills_the_matrix() {
    let rules = universal_rules();
    assert!(!rules.is_empty(), "no Universal frob rules registered");
    gob_mdtest::matrix::assert_matrix(env!("CARGO_MANIFEST_DIR"), "frob", &rules, &derive);
}

/// Run the real check over the case's garbage file and report `case.rule`'s share of it.
///
/// A cell the matrix derives as `NotApplicable` is reported so only when the rule truly stayed
/// silent; any other cell reports the rule's findings, which the contract wants to be Unresolved.
fn garbage_runner(case: &Case) -> RuleReport {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join(&case.file_name), &case.text).expect("write garbage");
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    let findings: Vec<_> = run(dir.path(), &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect();
    let cell = if case.language == "html" {
        "island"
    } else {
        case.language.as_str()
    };
    let not_applicable = (findings.is_empty()
        && matches!(
            derive(case.rule.as_str(), cell),
            Some(Derived::NotApplicable)
        ))
    .then(|| format!("{} does not apply to {cell} by construction", case.rule));
    tracing::debug!(rule = %case.rule, cell, findings = findings.len(), "garbage probe");
    RuleReport::new(case.rule.clone(), 0, 0, not_applicable, findings)
}

/// Rules that read parse state of source files: garbage must surface as their Unresolved finding.
const PARSE_DEPENDENT: [&str; 3] = ["AFFECT001", "COV001", "DOC001"];

/// Garbage probes of every Universal frob rule through the real check.
///
/// Parse-dependent rules must answer Unresolved (or `NotApplicable`) on every cell but `text`,
/// which has no grammar to fail so a silent pass is the correct answer. Every other rule is
/// ledger, graph or text based, so a silent pass is legitimate there and only a panic fails.
// frob:tests crates/gob-mdtest/src/garbage.rs::check_garbage
#[test]
fn garbage_input_never_panics_and_stays_unresolved() {
    let runner = Runner::new(garbage_runner);
    let strict: Vec<&str> = gob_mdtest::matrix::CELLS
        .iter()
        .copied()
        .filter(|c| *c != "text")
        .collect();
    let mut failures = Vec::new();
    for id in universal_rules() {
        let rule = Registry::global()
            .iter()
            .find(|m| m.id == id)
            .and_then(|m| m.rule_id().ok())
            .expect("registered rule id");
        let strict_rule = PARSE_DEPENDENT.contains(&id.as_str());
        let cells: &[&str] = if strict_rule {
            &strict
        } else {
            &gob_mdtest::matrix::CELLS
        };
        for f in check_garbage(&runner, &rule, cells) {
            if strict_rule || f.why.starts_with("the runner panicked") {
                failures.push(format!("{rule}: {f}"));
            }
        }
    }
    assert!(
        failures.is_empty(),
        "garbage probes failed:\n{}",
        failures.join("\n")
    );
}
