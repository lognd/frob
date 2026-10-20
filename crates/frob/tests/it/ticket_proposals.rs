//! `ticket proposals list|decline` and the pending count in `frob check`, against fixture ledgers.
// frob:ticket 01M3ZXGAWKZPVY6HF9NJ8GAFQV

use std::path::Path;
use std::process::Output;

use frob_ledger::event::{EventBody, ProposalData};
use serde_json::Value;

use crate::common;

fn frob(p: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(p)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn ok(p: &Path, args: &[&str]) -> Value {
    let out = frob(p, args);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{args:?}: {}",
        String::from_utf8_lossy(&out.stdout)
    );
    json(&out)
}

/// A repo with one ticket holding a pending proposal whose excerpt carries an escape byte.
fn fixture() -> (tempfile::TempDir, String) {
    let dir = common::git_repo();
    let p = dir.path();
    ok(p, &["init"]);
    let id = ok(p, &["ticket", "new", "--title", "Held"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let repo = gob_git::Repo::discover(p).expect("discover");
    let cfg = frob_cli::config::FrobConfig::load(p).expect("config");
    let ledger = frob_ledger::Ledger::open(
        repo,
        cfg.ledger(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let data = ProposalData {
        tracker_event: "T_1".into(),
        item: "I_9".into(),
        field: "title".into(),
        actor_id: "42".into(),
        time: "2026-11-01T00:00:00Z".parse().expect("stamp"),
        digest: "abc".into(),
        excerpt: "new \\u{1b}[31mtitle".into(),
        origin: "tracker".into(),
        supersedes: None,
    };
    ledger
        .append(id.parse().expect("ulid"), EventBody::Proposal(data))
        .expect("append proposal");
    (dir, id)
}

#[test]
fn a_pending_proposal_is_listed_then_declined_with_a_reason_and_leaves_the_list() {
    // frob:tests crates/frob/src/ticket/proposals_cmd.rs::Decline
    // frob:tests crates/frob/src/ticket/proposals_cmd.rs::List
    let (dir, id) = fixture();
    let p = dir.path();
    let listed = ok(p, &["ticket", "proposals", "list"]);
    assert_eq!(listed["data"]["count"], 1);
    let row = &listed["data"]["proposals"][0];
    assert_eq!(row["tracker_event"], "T_1");
    assert_eq!(row["origin"], "tracker");
    assert_eq!(row["actor_id"], "42");

    let done = ok(
        p,
        &[
            "ticket",
            "proposals",
            "decline",
            &id,
            "T_1",
            "--reason",
            "not wanted",
        ],
    );
    assert_eq!(done["data"]["reason"], "not wanted");
    assert_eq!(ok(p, &["ticket", "proposals", "list"])["data"]["count"], 0);

    let again = ok(
        p,
        &[
            "ticket",
            "proposals",
            "decline",
            &id,
            "T_1",
            "--reason",
            "not wanted",
        ],
    );
    assert_eq!(again["already"], true);

    let missing = frob(
        p,
        &[
            "ticket",
            "proposals",
            "decline",
            &id,
            "T_404",
            "--reason",
            "x",
        ],
    );
    assert_eq!(missing.status.code(), Some(2));
}

#[test]
fn pending_proposals_show_a_count_in_check_without_changing_its_exit_status() {
    // frob:tests crates/frob-check/src/proposals_summary.rs::pending_count_at
    // frob:tests crates/frob-check/src/proposals_summary.rs::pending_count
    // frob:tests crates/frob-check/src/proposals_summary.rs::pending_by_ticket
    let (dir, _) = fixture();
    let p = dir.path();
    let out = frob(p, &["check", "--only", "REF001"]);
    let body = json(&out);
    assert_eq!(body["data"]["pending_proposals"], 1, "{body}");
    assert_eq!(out.status.code(), Some(0), "{body}");
}
