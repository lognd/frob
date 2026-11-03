//! Rule binding of the release crate against a stub ledger host, and the recorded cuts of an empty ledger.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::path::Path;

use frob_ledger::host::{LedgerHost, LedgerView};
use gob_rules::Finding;

/// A host with no ledger.
struct Stub;

impl LedgerHost for Stub {
    fn ledger_view(&self) -> LedgerView<'_> {
        LedgerView {
            root: Path::new("."),
            ledger: None,
            error: None,
            missing: None,
            milestones: 0,
            tickets: 0,
            configured: false,
        }
    }

    fn doctor_findings(&self) -> Result<Vec<Finding>, String> {
        Ok(Vec::new())
    }
}

// frob:tests crates/frob-release/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = frob_release::rules::bind::<Stub>();
    assert_eq!(rules.len(), frob_release::rules::METAS.len());
}

// frob:tests crates/frob-release/src/rel001.rs::recorded_cuts
#[test]
fn a_ledger_with_no_tip_records_no_cuts() {
    let (_d, repo) = crate::rel001_corpus::fixture();
    let ledger = frob_ledger::Ledger::open(
        repo,
        frob_ledger::LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let cuts = frob_release::rel001::recorded_cuts(&ledger).expect("readable");
    assert!(cuts.is_empty());
}
