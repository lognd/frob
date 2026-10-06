//! `frob ticket branch init`: orphan branch bootstrap that never touches the code checkout.
// frob:ticket 01M3ZX8141MTBF6G2E6BAD33TS

use std::path::Path;
use std::process::Output;

use serde_json::Value;

mod common;

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
