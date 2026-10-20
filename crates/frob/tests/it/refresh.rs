//! `frob refresh` probes the remote once, caches the answer, and `--status` reads the cache alone.
// frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2

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

fn frob(dir: &Path, args: &[&str]) -> (i32, Value) {
    let out = common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob");
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

// frob:tests crates/frob/src/refresh_cmd.rs::Refresh
#[test]
fn refresh_probes_then_status_reads_the_cache() {
    let (_origin, clone) = clone_with_origin();
    let (code, v) = frob(clone.path(), &["refresh"]);
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["data"]["outcome"], "probed");
    assert_eq!(v["data"]["class"], "ok");
    let (code, v) = frob(clone.path(), &["refresh", "--status"]);
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["data"]["status"], "frob:ok");
    assert_eq!(v["data"]["outcome"], "status");
}

// frob:tests crates/frob/src/refresh_cmd.rs::Refresh
#[test]
fn no_remote_is_local_only_without_warnings() {
    let repo = common::git_repo();
    git(repo.path(), &["commit", "-q", "--allow-empty", "-m", "c1"]);
    std::fs::write(repo.path().join("frob.toml"), "[tickets]\nref = \"main\"\n").expect("toml");
    let (code, v) = frob(repo.path(), &["refresh"]);
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["data"]["status"], "frob:local-only");
    let (code, v) = frob(repo.path(), &["refresh", "--status"]);
    assert_eq!(code, 0);
    assert_eq!(v["data"]["status"], "frob:local-only");
}

// frob:tests crates/frob/src/refresh_cmd.rs::Refresh
#[test]
fn missing_base_exits_one_with_e_sync_no_base() {
    let (_origin, clone) = clone_with_origin();
    std::fs::write(
        clone.path().join("frob.toml"),
        "[tickets]\nref = \"experimental\"\n",
    )
    .expect("toml");
    let (code, v) = frob(clone.path(), &["refresh"]);
    assert_eq!(code, 1, "{v}");
    assert_eq!(v["error"]["code"], "E-SYNC-NO-BASE", "{v}");
}

// frob:tests crates/frob/src/refresh_cmd.rs::Refresh
#[test]
fn unreachable_remote_exits_three() {
    let (origin, clone) = clone_with_origin();
    std::fs::remove_dir_all(origin.path().join(".git")).expect("rm");
    let (code, v) = frob(clone.path(), &["refresh"]);
    assert_eq!(code, 3, "{v}");
    assert_eq!(v["error"]["code"], "W-SYNC-OFFLINE", "{v}");
}
