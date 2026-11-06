//! The `PmHost` seam: `relay_pm` against a stub host, the stub's lease answers, the `PM` rule binding and
//! the legacy `frob.toml` readers.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::collections::BTreeSet;
use std::path::Path;

use frob_ledger::TicketId;
use frob_ledger::guards::LeaseCheck;
use frob_ledger::host::{LedgerHost, LedgerView};
use frob_ledger::index::Summary;
use frob_pm::{PmHost, config::PmConfig, relay_pm};
use gob_rules::{Finding, Severity};

/// A host whose ledger is unreadable and which holds no leases.
struct Stub;

struct Free;

impl LeaseCheck for Free {
    fn is_free(&self, _ticket: &Summary, _scope: &[String]) -> bool {
        true
    }
}

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
        Ok(Vec::new())
    }
}

impl PmHost for Stub {
    fn pm_config(&self) -> Result<PmConfig, String> {
        Ok(PmConfig::default())
    }

    fn live_leases(&self) -> Option<BTreeSet<TicketId>> {
        Some(BTreeSet::new())
    }

    fn lease_check(&self) -> Box<dyn LeaseCheck + '_> {
        Box::new(Free)
    }
}

// frob:tests crates/frob-pm/src/host.rs::relay_pm
// frob:tests crates/frob-pm/src/host.rs::PmHost.pm_config
#[test]
fn an_unreadable_ledger_relays_the_required_unresolved_finding() {
    let found = relay_pm(&Stub, "PM001", |_| Ok(Vec::new()));
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].severity, Severity::Unresolved);
    assert!(found[0].message.contains("ledger unreadable: boom"));
}

// frob:tests crates/frob-pm/src/host.rs::PmHost.live_leases
// frob:tests crates/frob-pm/src/host.rs::PmHost.lease_check
// frob:tests crates/frob-pm/src/host.rs::PmHost.design_graph
#[test]
fn the_stub_host_answers_lease_questions() {
    assert_eq!(Stub.live_leases(), Some(BTreeSet::new()));
    let _free: Box<dyn LeaseCheck + '_> = Stub.lease_check();
    assert!(Stub.design_graph().is_none());
}

// frob:tests crates/frob-pm/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_relay_per_pm_rule() {
    assert_eq!(frob_pm::rules::bind::<Stub>().len(), 8);
}

// frob:tests crates/frob-pm/src/legacy/good_first.rs::max_points
// frob:tests crates/frob-pm/src/legacy/pm032.rs::min_ready
#[test]
fn legacy_thresholds_read_frob_toml_and_fall_back_to_defaults() {
    let dir = tempfile::tempdir().expect("tempdir");
    assert_eq!(frob_pm::legacy::good_first::max_points(dir.path()), 2);
    assert_eq!(frob_pm::legacy::pm032::min_ready(dir.path()), 3);
    std::fs::write(
        dir.path().join("frob.toml"),
        "[tickets]\ngood_first_max_points = 5\ngood_first_min = 7\n",
    )
    .expect("write");
    assert_eq!(frob_pm::legacy::good_first::max_points(dir.path()), 5);
    assert_eq!(frob_pm::legacy::pm032::min_ready(dir.path()), 7);
}
