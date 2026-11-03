//! `RuleReport::unresolved` yields only the Unresolved findings of a report.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use gob_ir::vocab::finding::Finding;
use gob_ir::vocab::severity::Severity;
use gob_ir::vocab::unresolved::RuleReport;

// frob:tests crates/gob-ir/src/vocab/unresolved.rs::RuleReport.unresolved
#[test]
fn unresolved_skips_error_findings() {
    let rule = "COV001".parse().expect("rule id");
    let err = Finding::new(rule, Severity::Error, None, "bad", "a.rs::f");
    let unk = Finding::new(
        "COV001".parse().expect("rule id"),
        Severity::Unresolved,
        None,
        "unsure",
        "a.rs::g",
    );
    let report = RuleReport::new(
        "COV001".parse().expect("rule id"),
        2,
        2,
        None,
        vec![err, unk],
    );
    let found: Vec<_> = RuleReport::unresolved(&report).collect();
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].message, "unsure");
}
