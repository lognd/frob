//! `frob agent brief`: a bounded summary of the leased ticket, scope, worktree and standing rules.
// frob:ticket 01M4P2N1M00A5XSDA8SW5FBRR8

use crate::common;

use std::path::Path;
use std::process::Output;

use frob_lease::{Holder, LeaseConfig, LeaseStore};
use serde_json::Value;

fn git(dir: &Path, args: &[&str]) {
    let s = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(s.success(), "git {args:?}");
}

fn frob(dir: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(dir)
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

/// An initialised repo holding a ticket leased from the repo's own worktree.
fn leased_repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let r = dir.path();
    assert_eq!(frob(r, &["init"]).status.code(), Some(0));
    git(r, &["add", "-A"]);
    git(r, &["commit", "-q", "-m", "base"]);
    let new = json(&frob(
        r,
        &["ticket", "new", "--title", "brief me", "--scope", "src/**"],
    ));
    let id: frob_ledger::TicketId = new["data"]["id"]
        .as_str()
        .expect("id")
        .parse()
        .expect("ulid");
    let repo = gob_git::Repo::discover(r).expect("discover");
    let store = LeaseStore::open(
        &repo,
        LeaseConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .expect("store");
    let holder = Holder {
        actor: "Test User".to_owned(),
        worktree: gob_fs::canonical(r).expect("canon"),
    };
    store
        .acquire(id, &holder, &["src/**".to_owned()])
        .expect("acquire");
    dir
}

// frob:tests crates/frob/src/agent/brief.rs::lines
// frob:tests crates/frob/src/agent_cmd.rs::AgentBrief
#[test]
fn brief_names_ticket_scope_worktree_and_rules() {
    let dir = leased_repo();
    let out = frob(dir.path(), &["agent", "brief"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    let v = json(&out);
    let text = v["data"]["text"].as_str().expect("text");
    assert!(text.contains("brief me"), "{text}");
    assert!(text.contains("Lease scope: src/**"), "{text}");
    assert!(text.contains("Worktree: "), "{text}");
    assert!(text.contains("Standing rules:"), "{text}");
    assert_eq!(v["data"]["truncated"], false);
}

// frob:tests crates/frob/src/agent/brief.rs::cap
#[test]
fn brief_is_capped_at_the_byte_budget() {
    let dir = leased_repo();
    let v = json(&frob(dir.path(), &["agent", "brief", "--max-bytes", "80"]));
    let text = v["data"]["text"].as_str().expect("text");
    assert!(text.len() <= 80, "{} bytes: {text}", text.len());
    assert_eq!(v["data"]["truncated"], true);
    assert_eq!(v["data"]["max_bytes"], 80);
}
