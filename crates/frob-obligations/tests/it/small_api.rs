//! The obligation host seam, exception application over raw findings, ledger-file TICK006 and rule binding.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use crate::common;

use std::path::PathBuf;

use common::{shared_tickets, write_tree};
use frob_obligations::{
    Collected, InvariantsConfig, ObligationHost, ObligationInputs, apply_exceptions, collect,
    evaluate_repo, tick006_ledger_file,
};

const ULID: &str = "01M3ZX86MA30ABW915Z943BQYB";

/// A host over one collected tree.
struct Stub {
    root: PathBuf,
    collected: Collected,
    config: InvariantsConfig,
}

impl ObligationHost for Stub {
    fn obligations(&self) -> ObligationInputs<'_> {
        self.collected.inputs(&self.root, None, &self.config)
    }
}

fn stub(files: &[(&str, &str)]) -> (tempfile::TempDir, Stub) {
    let dir = tempfile::tempdir().expect("tempdir");
    write_tree(dir.path(), files);
    let collected = collect(dir.path()).expect("collect");
    let host = Stub {
        root: dir.path().to_path_buf(),
        collected,
        config: InvariantsConfig::default(),
    };
    (dir, host)
}

// frob:tests crates/frob-obligations/src/host.rs::ObligationHost.has_test_capable_files
// frob:tests crates/frob-obligations/src/host.rs::ObligationHost.ledger_facts
#[test]
fn the_host_defaults_assume_test_capable_files_and_keep_no_ledger() {
    let (_dir, host) = stub(&[("docs/a.md", "# A\n")]);
    assert!(ObligationHost::has_test_capable_files(&host));
    assert!(ObligationHost::ledger_facts(&host).is_none());
}

// frob:tests crates/frob-obligations/src/host.rs::ObligationHost.obligations
#[test]
fn the_host_lends_the_inputs_of_the_tree_it_collected() {
    let (dir, host) = stub(&[("docs/a.md", "# A\n")]);
    let inputs = ObligationHost::obligations(&host);
    assert_eq!(inputs.root, dir.path());
    assert!(inputs.ledger.is_none());
    assert!(!inputs.skip_tools);
}

// frob:tests crates/frob-obligations/src/lib.rs::apply_exceptions
#[test]
fn findings_without_a_covering_exception_stand_and_nothing_is_suppressed() {
    let text = format!("see tickets/{ULID}/ticket.md\n");
    let (_dir, host) = stub(&[("docs/a.md", text.as_str())]);
    let inputs = ObligationHost::obligations(&host);
    let mut files = inputs.files.clone();
    let raw = evaluate_repo(&inputs, &mut files);
    assert!(!raw.is_empty(), "the old ticket path form fires");
    let resolved = apply_exceptions(&inputs, &files, raw.clone());
    assert!(resolved.suppressed.is_empty());
    assert_eq!(resolved.findings.len(), raw.len());
}

// frob:tests crates/frob-obligations/src/tick_paths.rs::tick006_ledger_file
#[test]
fn a_ledger_file_link_is_reported_without_a_span_or_a_fix() {
    let tickets = shared_tickets();
    let text = format!("see tickets/{ULID}/ticket.md\n");
    let found = tick006_ledger_file("tickets/x/ticket.md", &text, &tickets.ledger);
    assert!(!found.is_empty());
    assert!(found.iter().all(|f| f.span.is_none() && f.fix.is_none()));
}

// frob:tests crates/frob-obligations/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = frob_obligations::rules::bind::<Stub>();
    assert_eq!(rules.len(), frob_obligations::rules::METAS.len());
}
