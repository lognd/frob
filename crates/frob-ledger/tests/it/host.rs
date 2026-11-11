//! The ledger host seam: `LedgerView::open`, the evaluation-failed finding and rule binding against a stub host.
// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use std::path::Path;

use frob_ledger::host::{LedgerHost, LedgerView, evaluation_failed};
use gob_rules::{Finding, Severity};

/// A host with no ledger whose doctor always fails with a fixed message.
struct Stub;

impl LedgerHost for Stub {
    fn ledger_view(&self) -> LedgerView<'_> {
        LedgerView {
            root: Path::new("."),
            ledger: None,
            error: Some("boom"),
            missing: None,
            milestones: 0,
            tickets: 0,
            configured: true,
        }
    }

    fn doctor_findings(&self) -> Result<Vec<Finding>, String> {
        Err("doctor unavailable".to_owned())
    }
}

// frob:tests crates/frob-ledger/src/host.rs::LedgerHost.ledger_view
// frob:tests crates/frob-ledger/src/host.rs::LedgerView.open
// frob:tests crates/frob-ledger/src/host.rs::evaluation_failed
#[test]
fn an_unreadable_ledger_opens_as_the_required_unresolved_finding() {
    let view = Stub.ledger_view();
    let finding = view.open("TICK001").expect_err("unreadable ledger");
    assert_eq!(finding.severity, Severity::Unresolved);
    assert!(finding.message.contains("ledger unreadable: boom"));
    let clean = LedgerView {
        error: None,
        ..view
    };
    assert!(clean.open("TICK001").expect("no error").is_none());
    let direct = evaluation_failed("TICK002", "why");
    assert!(direct.message.starts_with("evaluation-failed: TICK002"));
}

// frob:tests crates/frob-ledger/src/host.rs::LedgerHost.doctor_findings
#[test]
fn the_stub_doctor_reports_its_failure_text() {
    assert_eq!(
        Stub.doctor_findings().expect_err("fails"),
        "doctor unavailable"
    );
}

// frob:tests crates/frob-ledger/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_tick_rule_for_a_ledger_host() {
    assert_eq!(frob_ledger::rules::bind::<Stub>().len(), 5);
}
