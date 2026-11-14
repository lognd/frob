//! Small entry points of the design stamp and the CLI registration, driven against throwaway repositories.

use std::path::Path;

use frob_evidence::design::{digests_with, locate_grimble, stamp};
use frob_evidence::provider::{Capture, build_record};
use frob_evidence::record::Provider;
use frob_evidence::scrub::PathScrub;
use frob_evidence::{EvidenceTable, NonPassing, Workspace};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;

/// A workspace over a fresh repository plus the id of one ticket in its ledger.
fn workspace() -> (tempfile::TempDir, Workspace, frob_ledger::TicketId) {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("init");
    let config = dir.path().join(".git").join("config");
    let mut text = std::fs::read_to_string(&config).expect("config");
    text.push_str("[user]\n\tname = Owner\n\temail = owner@example.com\n");
    std::fs::write(&config, text).expect("identity");
    let ws =
        Workspace::open(dir.path(), std::sync::Arc::new(gob_time::SystemClock)).expect("workspace");
    let t = ws
        .ledger
        .new_ticket(NewTicket::new("Design stamp", TicketType::Task))
        .expect("ticket");
    let id = t.ticket.front.id;
    (dir, ws, id)
}

#[test]
fn a_grimble_that_cannot_run_yields_no_digests() {
    // frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
    // frob:tests crates/frob-evidence/src/design.rs::digests_with
    let (_dir, ws, id) = workspace();
    assert!(digests_with(&ws, Path::new("/nonexistent/grimble"), id).is_empty());
}

#[test]
fn a_root_with_no_model_leaves_the_record_without_design_digests() {
    // frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
    // frob:tests crates/frob-evidence/src/design.rs::stamp
    let (dir, ws, id) = workspace();
    let repo = gob_git::Repo::discover(dir.path()).expect("repo");
    let store =
        frob_evidence::store::BlobStore::open(&EvidenceTable::default(), &repo).expect("store");
    let cap = Capture {
        exit_code: Some(0),
        passed: true,
        measured: true,
        tests: Vec::new(),
        failed_tests: Vec::new(),
        non_passing: NonPassing::default(),
        transcript: String::new(),
    };
    let mut rec = build_record(
        &store,
        &PathScrub::default(),
        Provider::Command,
        "true",
        &cap,
        &[1],
        frob_ledger::model::Stamp::from_unix(1_800_000_000),
    )
    .expect("record");
    stamp(&ws, id, &mut rec);
    assert!(rec.design.is_empty());
}

#[test]
fn a_located_grimble_is_named_grimble() {
    // frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
    // frob:tests crates/frob-evidence/src/design.rs::locate_grimble
    if let Some(path) = locate_grimble() {
        assert_eq!(path.file_stem(), Some(std::ffi::OsStr::new("grimble")));
    }
}

#[test]
fn registering_in_place_adds_the_evidence_verbs() {
    // frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
    // frob:tests crates/frob-evidence/src/lib.rs::register_mut
    let mut cli = gob_cli::Cli::new("frob", "0.0.0");
    frob_evidence::register_mut(&mut cli);
    assert!(format!("{cli:?}").contains("evidence"));
}
