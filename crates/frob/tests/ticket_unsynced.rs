//! A ledger write from a linked worktree names checkouts it could not sync.

mod common;

use std::path::Path;
use std::process::{Command as Std, Output};

use serde_json::Value;

fn git(dir: &Path, args: &[&str]) {
    let out = Std::new("git")
        .current_dir(dir)
        .args(args)
        .output()
        .expect("run git");
    assert!(out.status.success(), "git {args:?}: {out:?}");
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

// frob:ticket 01M42MGNZZ1BY6YCG49BDHEZAT
#[test]
fn comment_from_a_linked_worktree_warns_about_the_blocked_primary() {
    let primary = tempfile::tempdir().expect("tempdir");
    let p = primary.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    assert!(frob(p, &["init"]).status.success());
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let new = json(&frob(p, &["ticket", "new", "--title", "t"]));
    let id = new["data"]["id"].as_str().expect("id").to_owned();

    let side = tempfile::tempdir().expect("tempdir");
    let wt = side.path().join("wt");
    git(
        p,
        &[
            "worktree",
            "add",
            "-q",
            "-b",
            "feature",
            wt.to_str().unwrap(),
            "main",
        ],
    );
    let ticket_md = p.join("tickets").join(&id).join("ticket.md");
    let mut text = std::fs::read_to_string(&ticket_md).expect("ticket.md");
    text.push_str("\nlocal note\n");
    std::fs::write(&ticket_md, &text).expect("edit");

    let out = frob(&wt, &["ticket", "comment", &id, "--body", "from side"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    let v = json(&out);
    let warnings = v["warnings"].as_array().expect("warnings");
    let joined = warnings
        .iter()
        .filter_map(Value::as_str)
        .collect::<Vec<_>>()
        .join("\n");
    assert!(joined.contains("ticket.md"), "{joined}");
    assert!(joined.contains("not synced"), "{joined}");
    assert!(joined.contains("git restore"), "{joined}");
    // the new event file must not be staged-deleted in the primary
    let status = Std::new("git")
        .current_dir(p)
        .args(["status", "--porcelain"])
        .output()
        .expect("status");
    let status = String::from_utf8_lossy(&status.stdout);
    assert!(!status.contains("events/"), "{status}");
}
