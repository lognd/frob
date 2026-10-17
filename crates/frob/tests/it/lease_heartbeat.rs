//! Verbs that prove activity (`ticket update`, `check --ticket`, `test`) renew the lease of the worktree they run in.

use crate::common;

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use frob_lease::{Holder, LeaseConfig, LeaseStore};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
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

/// A repo with a ticket leased to the repo's own work tree; returns (dir, ticket id, store).
fn leased() -> (tempfile::TempDir, String, frob_ledger::TicketId, LeaseStore) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    assert_eq!(frob(p, &["init"]).status.code(), Some(0));
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let out = frob(p, &["ticket", "new", "--title", "t", "--scope", "a/**"]);
    let v: Value = serde_json::from_slice(&out.stdout).expect("json");
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    let tid: frob_ledger::TicketId = id.parse().expect("ulid");
    let repo = gob_git::Repo::discover(p).expect("discover");
    let store = LeaseStore::open(
        &repo,
        LeaseConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .expect("store");
    let holder = Holder {
        actor: "Test User".to_owned(),
        worktree: repo.work_dir().expect("work dir").to_path_buf(),
    };
    store
        .acquire(tid, &holder, &["a/**".to_owned()])
        .expect("acquire");
    (dir, id, tid, store)
}

/// Run `args` after a pause and assert the lease's `renewed_at` moved forward.
fn assert_renews(args: &[&str], with_id: bool) {
    let (dir, id, tid, store) = leased();
    let before = store
        .live_lease(tid)
        .expect("read")
        .expect("lease")
        .renewed_at;
    std::thread::sleep(Duration::from_millis(2100));
    let mut full: Vec<&str> = args.to_vec();
    if with_id {
        full.push(&id);
    }
    let _ = frob(dir.path(), &full);
    let after = store
        .live_lease(tid)
        .expect("read")
        .expect("lease")
        .renewed_at;
    assert!(
        after > before,
        "{args:?} did not renew the lease: {before:?} -> {after:?}"
    );
}

// frob:ticket 01M48YXQM2E6EFTH71NQ6XGMR7
// frob:tests crates/frob/src/ticket/write.rs::Update
#[test]
fn ticket_update_renews_the_worktree_lease() {
    let (dir, id, tid, store) = leased();
    let before = store
        .live_lease(tid)
        .expect("read")
        .expect("lease")
        .renewed_at;
    std::thread::sleep(Duration::from_millis(2100));
    let _ = frob(dir.path(), &["ticket", "update", &id, "--add-label", "x"]);
    let after = store
        .live_lease(tid)
        .expect("read")
        .expect("lease")
        .renewed_at;
    assert!(
        after > before,
        "update did not renew: {before:?} -> {after:?}"
    );
}

// frob:ticket 01M48YXQM2E6EFTH71NQ6XGMR7
#[test]
fn check_ticket_renews_the_worktree_lease() {
    assert_renews(&["check", "--ticket"], true);
}

// frob:ticket 01M48YXQM2E6EFTH71NQ6XGMR7
#[test]
fn test_verb_renews_the_worktree_lease() {
    assert_renews(&["test", "--all"], false);
}
