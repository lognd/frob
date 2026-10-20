//! Per-verb auto-refresh policy: `doable` probes in the foreground, reads kick a background refresh, CI turns both off.
// frob:ticket 01M5CW04GHM970H5KR4EV5KK0X

use crate::common;

use std::path::Path;
use std::time::{Duration, Instant};

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

fn frob(dir: &Path, ci: bool, args: &[&str]) -> (i32, Value) {
    let mut cmd = common::frob_command();
    cmd.current_dir(dir)
        .env_remove("FROB_LOG")
        .env_remove("FROB_SYNC_INNER")
        .arg("--json")
        .args(args);
    if ci {
        cmd.env("CI", "true");
    } else {
        cmd.env_remove("CI");
    }
    let out = cmd.output().expect("run frob");
    let json = serde_json::from_slice(&out.stdout).unwrap_or(Value::Null);
    (out.status.code().unwrap_or(-1), json)
}

/// A clone on `main` with a local `origin` that has `main`.
fn clone_with_origin() -> (tempfile::TempDir, tempfile::TempDir) {
    let origin = common::git_repo();
    git(
        origin.path(),
        &["commit", "-q", "--allow-empty", "-m", "c1"],
    );
    let clone = common::git_repo();
    git(clone.path(), &["commit", "-q", "--allow-empty", "-m", "c1"]);
    let url = gob_path::Shown::of(origin.path()).to_string();
    git(clone.path(), &["remote", "add", "origin", &url]);
    std::fs::write(
        clone.path().join("frob.toml"),
        "[tickets]\nref = \"main\"\n",
    )
    .expect("toml");
    (origin, clone)
}

fn state_file(clone: &Path) -> std::path::PathBuf {
    clone.join(".git").join("frob").join("refresh.toml")
}

fn warnings(v: &Value) -> String {
    v["warnings"].to_string()
}

// frob:tests crates/frob/src/ticket/read.rs::Doable
#[test]
fn doable_probes_in_the_foreground() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), false, &["ticket", "doable"]);
    assert_eq!(code, 0, "{v}");
    assert!(state_file(clone.path()).exists(), "foreground probe ran");
    let (_, v) = frob(clone.path(), false, &["refresh", "--status"]);
    assert_eq!(v["data"]["status"], "frob:ok", "{v}");
}

// frob:tests crates/frob/src/ticket/read.rs::Doable
#[test]
fn doable_warns_when_offline_and_the_view_is_old() {
    let (origin, clone) = clone_with_origin();
    frob(clone.path(), false, &["refresh"]);
    std::fs::remove_dir_all(origin.path().join(".git")).expect("rm");
    let path = state_file(clone.path());
    let old = std::fs::read_to_string(&path)
        .expect("state")
        .lines()
        .map(|l| match l.split_once(" = ") {
            Some(("probed_at" | "last_ok_at" | "next_attempt_at", _)) => {
                format!("{} = 1", l.split_once(" = ").expect("kv").0)
            }
            _ => l.to_owned(),
        })
        .collect::<Vec<_>>()
        .join("\n");
    std::fs::write(&path, old).expect("age the state");
    let (code, v) = frob(clone.path(), false, &["ticket", "doable"]);
    assert_eq!(code, 0, "{v}");
    assert!(warnings(&v).contains("W-SYNC-OFFLINE"), "{v}");
}

// frob:tests crates/frob/src/ticket/read.rs::Doable
#[test]
fn ci_disables_the_foreground_probe_and_the_kick() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), true, &["ticket", "doable"]);
    assert_eq!(code, 0, "{v}");
    let (code, v) = frob(clone.path(), true, &["ticket", "list"]);
    assert_eq!(code, 0, "{v}");
    std::thread::sleep(Duration::from_millis(500));
    assert!(!state_file(clone.path()).exists(), "CI never syncs");
}

// frob:tests crates/frob/src/ticket/mod.rs::open
#[test]
fn reads_kick_a_background_refresh() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), false, &["ticket", "list"]);
    assert_eq!(code, 0, "{v}");
    let deadline = Instant::now() + Duration::from_secs(10);
    while !state_file(clone.path()).exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(100));
    }
    assert!(state_file(clone.path()).exists(), "background refresh ran");
}
