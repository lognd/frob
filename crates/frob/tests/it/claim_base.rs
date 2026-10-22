//! `work --here` pins the commit it started from, so a later change shows in the diff even on main (frob:ticket 01M4CTV0F8HWA7DPXYYDBE4TDJ).

use crate::common;

use std::path::Path;

use serde_json::Value;

fn frob(dir: &Path, args: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob");
    serde_json::from_slice(&out.stdout).unwrap_or(Value::Null)
}

fn git(dir: &Path, args: &[&str]) {
    let status = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(status.success(), "git {args:?}");
}

// frob:tests crates/frob-worktree/src/work.rs::Workspace.start_with
// frob:tests crates/frob-tests/src/verb.rs::claim_base
#[test]
fn work_here_base_keeps_a_committed_change_in_the_test_diff() {
    let dir = common::git_repo();
    let p = dir.path();
    assert!(frob(p, &["init"])["ok"].as_bool().unwrap_or(false));
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let id = frob(p, &["ticket", "new", "--title", "t", "--scope", "a/**"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let started = frob(p, &["work", "--here", &id]);
    assert_eq!(started["ok"], true, "{started}");
    std::fs::create_dir_all(p.join("a")).expect("mkdir");
    std::fs::write(p.join("a/x.txt"), "hi\n").expect("write");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "change on main"]);
    let planned = frob(p, &["test", "--base", "main", "--dry-run"]);
    let files = planned["data"]["touched"]["files"].to_string();
    assert!(files.contains("a/x.txt"), "{planned}");
}
