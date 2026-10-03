//! `frob init` on repositories of different shapes: the ledger ref follows the checked-out branch.
// frob:ticket 01M40FXTW5FYKQWG82PD8STDJR

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

/// Run git in `dir`; a failure is a test bug.
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

/// A repository whose `HEAD` names `branch`, with one commit when `commit` is true.
fn repo(branch: &str, commit: bool) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    git(root, &["init", "-q"]);
    git(
        root,
        &["symbolic-ref", "HEAD", &format!("refs/heads/{branch}")],
    );
    git(root, &["config", "user.name", "Test User"]);
    git(root, &["config", "user.email", "test@example.com"]);
    if commit {
        std::fs::write(root.join("a.txt"), "a\n").expect("write");
        git(root, &["add", "-A"]);
        git(root, &["commit", "-q", "-m", "initial"]);
    }
    dir
}

/// Run `frob --json <args>` in `dir` with the outer nextest environment scrubbed.
fn frob(dir: &Path, args: &[&str]) -> Output {
    let mut cmd = Command::cargo_bin("frob").expect("frob binary");
    cmd.current_dir(dir).env_remove("FROB_LOG").arg("--json");
    for (k, _) in std::env::vars() {
        if k.starts_with("NEXTEST") || k == "CARGO_TARGET_DIR" {
            cmd.env_remove(k);
        }
    }
    cmd.args(args).output().expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).expect("json envelope")
}

fn config_text(dir: &Path) -> String {
    std::fs::read_to_string(dir.join("frob.toml")).expect("read frob.toml")
}

/// Acceptance 1: a repository on trunk gets `refs/heads/trunk` and `ticket new` succeeds.
#[test]
fn init_on_trunk_points_the_ledger_at_trunk() {
    let dir = repo("trunk", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/trunk\""));
    let new = frob(
        dir.path(),
        &[
            "ticket",
            "new",
            "--title",
            "t",
            "--acceptance",
            "Given a, when b, then c",
        ],
    );
    assert_eq!(new.status.code(), Some(0), "{}", json(&new));
}

/// Acceptance 2: a repository on main keeps `refs/heads/main`.
#[test]
fn init_on_main_keeps_main() {
    let dir = repo("main", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/main\""));
}

/// An unborn branch (no commit yet) is named like any other: its ref exists after the first commit.
#[test]
fn init_on_an_unborn_branch_names_it() {
    let dir = repo("trunk", false);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/trunk\""));
}

/// A detached HEAD is refused with a remedy and writes nothing.
#[test]
fn init_on_a_detached_head_refuses_and_writes_nothing() {
    let dir = repo("main", true);
    git(dir.path(), &["checkout", "-q", "--detach"]);
    let out = frob(dir.path(), &["init"]);
    assert_eq!(out.status.code(), Some(3), "{}", json(&out));
    let env = json(&out);
    assert_eq!(env["error"]["code"], "E-DETACHED-HEAD");
    assert!(!dir.path().join("frob.toml").exists());
}

/// Re-running init, even from another branch or a detached HEAD, never changes an existing ref.
#[test]
fn init_rerun_keeps_an_existing_ref() {
    let dir = repo("main", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    git(dir.path(), &["switch", "-q", "-c", "other"]);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/main\""));
    git(dir.path(), &["checkout", "-q", "--detach"]);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/main\""));
}
