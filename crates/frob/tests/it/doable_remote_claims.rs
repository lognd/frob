//! `ticket doable` hides tickets whose claim branch sits in the remote-tracking refs with no ledger event.
// frob:ticket 01M5DBVT9HH0MRR30JVCJZYRTY

use crate::common;

use std::path::Path;

use serde_json::Value;

fn git(dir: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .env("GIT_AUTHOR_NAME", "t")
        .env("GIT_AUTHOR_EMAIL", "t@t")
        .env("GIT_COMMITTER_NAME", "t")
        .env("GIT_COMMITTER_EMAIL", "t@t")
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

fn frob(dir: &Path, args: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(dir)
        .env("CI", "true")
        .env_remove("FROB_LOG")
        .env_remove("FROB_SYNC_INNER")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob");
    serde_json::from_slice(&out.stdout).unwrap_or(Value::Null)
}

fn doable_handles(dir: &Path) -> (Vec<String>, Value) {
    let v = frob(dir, &["ticket", "doable"]);
    let handles = v["data"]["tickets"]
        .as_array()
        .expect("rows")
        .iter()
        .map(|r| r["handle"].as_str().expect("handle").to_owned())
        .collect();
    (handles, v)
}

// frob:tests crates/frob/src/ticket/read.rs::drop_remote_claimed
// frob:tests crates/frob-worktree/src/claim.rs::cached_remote_claim
#[test]
fn doable_skips_tickets_claimed_on_origin_without_a_ledger_event() {
    let clone = common::git_repo();
    git(clone.path(), &["commit", "-q", "--allow-empty", "-m", "c1"]);
    git(
        clone.path(),
        &["remote", "add", "origin", "https://example.invalid/r.git"],
    );
    std::fs::write(
        clone.path().join("frob.toml"),
        "[tickets]\nref = \"main\"\n",
    )
    .expect("toml");
    let mut handles = Vec::new();
    for title in ["claimed elsewhere", "free"] {
        let v = frob(
            clone.path(),
            &["ticket", "new", "--title", title, "--scope", "a/**"],
        );
        handles.push(v["data"]["handle"].as_str().expect("handle").to_owned());
    }
    let (before, _) = doable_handles(clone.path());
    assert_eq!(before.len(), 2, "both start doable: {before:?}");
    let bare = handles[0].trim_start_matches('~');
    git(
        clone.path(),
        &[
            "update-ref",
            &format!("refs/remotes/origin/ticket/{bare}"),
            "HEAD",
        ],
    );
    let (after, v) = doable_handles(clone.path());
    assert_eq!(after, vec![handles[1].clone()], "{v}");
    let warnings = v["warnings"].to_string();
    assert!(
        warnings.contains(&handles[0]),
        "names the hidden ticket: {v}"
    );
}
