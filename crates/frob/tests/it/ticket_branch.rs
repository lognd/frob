//! `frob ticket branch init`: orphan branch bootstrap that never touches the code checkout.
// frob:ticket 01M3ZX8141MTBF6G2E6BAD33TS

use std::path::Path;
use std::process::Output;

use serde_json::Value;

use crate::common;

fn frob(cwd: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).expect("stdout is JSON")
}

fn git(cwd: &Path, args: &[&str]) -> String {
    let out = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .output()
        .expect("git");
    String::from_utf8_lossy(&out.stdout).trim().to_owned()
}

/// A repository with one commit on `main`, so "code checkout unchanged" is observable.
fn repo_with_commit() -> tempfile::TempDir {
    let dir = common::git_repo();
    std::fs::write(dir.path().join("code.txt"), "code\n").expect("write");
    std::fs::write(dir.path().join("frob.toml"), "[tickets]\n").expect("config");
    git(dir.path(), &["add", "code.txt", "frob.toml"]);
    git(dir.path(), &["commit", "-m", "code"]);
    dir
}

// frob:tests crates/frob/src/ticket/branch_cmd.rs::BranchInit
#[test]
fn init_creates_an_orphan_branch_and_leaves_the_checkout_alone() {
    let dir = repo_with_commit();
    let p = dir.path();
    let (head, status) = (
        git(p, &["rev-parse", "HEAD"]),
        git(p, &["status", "--porcelain"]),
    );
    let index = std::fs::read(p.join(".git/index")).expect("index");

    let out = frob(p, &["ticket", "branch", "init"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    let v = json(&out);
    assert_eq!(v["already"], false);
    assert_eq!(v["data"]["branch"], "frob-tickets");

    assert_eq!(
        git(p, &["show", "frob-tickets:README.md"]).lines().next(),
        Some("# Tickets")
    );
    assert_eq!(
        git(p, &["rev-list", "--parents", "-n1", "frob-tickets"]),
        git(p, &["rev-parse", "frob-tickets"]),
        "root commit has no parent"
    );
    assert_eq!(git(p, &["rev-parse", "HEAD"]), head);
    assert_eq!(git(p, &["symbolic-ref", "HEAD"]), "refs/heads/main");
    assert_eq!(git(p, &["status", "--porcelain"]), status);
    assert_eq!(std::fs::read(p.join(".git/index")).expect("index"), index);
    assert!(!p.join("README.md").exists());
}

// frob:tests crates/frob/src/ticket/branch_cmd.rs::BranchInit
#[test]
fn init_twice_reports_already_and_changes_nothing() {
    let dir = repo_with_commit();
    let p = dir.path();
    assert_eq!(
        frob(p, &["ticket", "branch", "init"]).status.code(),
        Some(0)
    );
    let tip = git(p, &["rev-parse", "frob-tickets"]);
    let second = frob(p, &["ticket", "branch", "init"]);
    assert_eq!(second.status.code(), Some(0));
    let v = json(&second);
    assert_eq!(v["already"], true);
    assert_eq!(v["data"]["tip"], tip);
    assert_eq!(git(p, &["rev-parse", "frob-tickets"]), tip);
}

// frob:tests crates/frob/src/ticket/branch_cmd.rs::BranchInit
#[test]
fn branch_knob_names_the_branch_and_bad_names_are_refused() {
    let dir = repo_with_commit();
    let p = dir.path();
    std::fs::write(p.join("frob.toml"), "[tickets]\nbranch = \"ledger\"\n").expect("cfg");
    let out = frob(p, &["ticket", "branch", "init"]);
    assert_eq!(json(&out)["data"]["branch"], "ledger");
    assert!(!git(p, &["rev-parse", "ledger"]).is_empty());

    std::fs::write(p.join("frob.toml"), "[tickets]\nbranch = \"bad..name\"\n").expect("cfg");
    let bad = frob(p, &["ticket", "branch", "init"]);
    assert_ne!(bad.status.code(), Some(0));
    assert!(String::from_utf8_lossy(&bad.stdout).contains("E-TICKET-BRANCH-NAME"));
}

/// A shallow single-branch clone of a repository whose ledger lives on `frob-tickets`; returns the clone and the ledger tip.
fn shallow_ci_clone() -> (tempfile::TempDir, tempfile::TempDir, String) {
    let origin = common::git_repo();
    let o = origin.path();
    std::fs::write(o.join("code.txt"), "code\n").expect("write");
    std::fs::write(o.join("frob.toml"), "[tickets]\nref_mode = \"orphan\"\n").expect("config");
    git(o, &["add", "code.txt", "frob.toml"]);
    git(o, &["commit", "-m", "code"]);
    assert_eq!(
        frob(o, &["ticket", "branch", "init"]).status.code(),
        Some(0)
    );
    let tip = git(o, &["rev-parse", "frob-tickets"]);
    let branch = git(o, &["branch", "--show-current"]);
    let clone = tempfile::tempdir().expect("tempdir");
    let url = format!("file://{}", gob_path::Shown::with_home(o, None).as_str());
    git(
        clone.path(),
        &["clone", "--depth=1", "--branch", &branch, &url, "c"],
    );
    let c = clone.path().join("c");
    git(&c, &["config", "user.name", "Test User"]);
    git(&c, &["config", "user.email", "test@example.com"]);
    (origin, clone, tip)
}

// frob:tests crates/frob/src/init.rs::Init
#[test]
fn init_in_a_shallow_ci_clone_creates_the_ticket_branch_from_origin() {
    let (_origin, clone, tip) = shallow_ci_clone();
    let c = clone.path().join("c");
    assert_eq!(
        git(&c, &["rev-parse", "--verify", "--quiet", "frob-tickets"]),
        ""
    );
    let out = frob(&c, &["init"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    assert_eq!(
        json(&out)["data"]["ticket_branch"]["target"],
        "refs/heads/frob-tickets"
    );
    assert_eq!(git(&c, &["rev-parse", "frob-tickets"]), tip);
    let again = frob(&c, &["init"]);
    assert_eq!(json(&again)["data"]["ticket_branch"], Value::Null);
}

// frob:tests crates/frob/src/ticket/doctor_cmd.rs::TicketDoctor
#[test]
fn doctor_fix_creates_the_missing_ticket_branch_from_origin() {
    let (_origin, clone, tip) = shallow_ci_clone();
    let c = clone.path().join("c");
    let refused = frob(&c, &["ticket", "doctor"]);
    assert_eq!(refused.status.code(), Some(3), "refusal exit");
    assert!(
        String::from_utf8_lossy(&refused.stdout).contains("E-DOCTOR-TICKET-BRANCH-MISSING"),
        "{}",
        String::from_utf8_lossy(&refused.stdout)
    );
    let fixed = frob(&c, &["ticket", "doctor", "--fix"]);
    assert_eq!(
        json(&fixed)["data"]["ticket_branch_created"],
        "frob-tickets",
        "{}",
        String::from_utf8_lossy(&fixed.stdout)
    );
    assert_eq!(git(&c, &["rev-parse", "frob-tickets"]), tip);
}
