//! `frob init` on repositories of different shapes: the ledger ref and `[check] base` follow the repository's default branch.
// frob:ticket 01M40FXTW5FYKQWG82PD8STDJR
// frob:ticket 01M4069Z0HH5RV8TNPFVA936C5
// frob:ticket 01M4FD03W4D4XZZ3XBP32Q9XFQ

mod common;

use std::path::Path;
use std::process::Output;
use std::time::Duration;

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
        std::fs::write(
            root.join("Cargo.toml"),
            "[package]\nname = \"tiny\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        )
        .expect("write");
        std::fs::create_dir_all(root.join("src")).expect("mkdir");
        std::fs::write(
            root.join("src/lib.rs"),
            "//! A.\n\n/// One.\npub fn one() -> u8 {\n    1\n}\n",
        )
        .expect("write");
        git(root, &["add", "-A"]);
        git(root, &["commit", "-q", "-m", "initial"]);
    }
    dir
}

/// Run `frob --json <args>` in `dir` with the outer nextest environment scrubbed.
fn frob(dir: &Path, args: &[&str]) -> Output {
    let mut cmd = common::frob_command();
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

/// The `[check] base` line of a materialized `frob.toml`.
fn base_line(dir: &Path, base: &str) -> bool {
    config_text(dir).contains(&format!("base = \"{base}\""))
}

/// Acceptance 1: on main with existing code, init then check exits 0 and base is main.
#[test]
fn init_then_check_on_main_exits_zero_with_base_main() {
    let dir = repo("main", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(base_line(dir.path(), "main"), "{}", config_text(dir.path()));
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "chore: frob init"]);
    let check = frob(dir.path(), &["check"]);
    assert_eq!(check.status.code(), Some(0), "{}", json(&check));
}

/// Acceptance 2: on master the base is master, not a hard-coded main.
#[test]
fn init_on_master_detects_base_master() {
    let dir = repo("master", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(
        base_line(dir.path(), "master"),
        "{}",
        config_text(dir.path())
    );
}

/// A repository on trunk gets base trunk.
#[test]
fn init_on_trunk_detects_base_trunk() {
    let dir = repo("trunk", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(
        base_line(dir.path(), "trunk"),
        "{}",
        config_text(dir.path())
    );
}

/// Point `origin/HEAD` at `origin/<default>` while a different branch is checked out.
fn with_origin_head(dir: &Path, default: &str) {
    git(
        dir,
        &[
            "update-ref",
            &format!("refs/remotes/origin/{default}"),
            "HEAD",
        ],
    );
    git(
        dir,
        &[
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            &format!("refs/remotes/origin/{default}"),
        ],
    );
}

/// The remote HEAD of origin wins over the checked-out branch, for the base and the ledger ref alike.
#[test]
fn init_prefers_the_origin_head_for_base() {
    let dir = repo("feature", true);
    with_origin_head(dir.path(), "develop");
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(
        base_line(dir.path(), "develop"),
        "{}",
        config_text(dir.path())
    );
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/develop\""));
}

/// A detached HEAD with an origin HEAD still detects the base; without one init refuses (ledger ref cannot be named).
#[test]
fn init_on_a_detached_head_refuses_before_writing_a_base() {
    let dir = repo("main", true);
    with_origin_head(dir.path(), "develop");
    git(dir.path(), &["checkout", "-q", "--detach"]);
    let out = frob(dir.path(), &["init"]);
    assert_eq!(out.status.code(), Some(3), "{}", json(&out));
    assert!(!dir.path().join("frob.toml").exists());
}

/// Re-running init, even after the default branch changes, never rewrites an existing base.
#[test]
fn init_rerun_keeps_an_existing_base() {
    let dir = repo("main", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    git(dir.path(), &["switch", "-q", "-c", "other"]);
    with_origin_head(dir.path(), "develop");
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    assert!(base_line(dir.path(), "main"), "{}", config_text(dir.path()));
}

/// `config sync` on a config missing both knobs writes the detected values, not the main default.
#[test]
fn config_sync_detects_ref_and_base() {
    let dir = repo("master", true);
    std::fs::write(
        dir.path().join("frob.toml"),
        "[directives]\nnamespaces = [\"frob\"]\n",
    )
    .expect("write");
    assert_eq!(frob(dir.path(), &["config", "sync"]).status.code(), Some(0));
    let text = config_text(dir.path());
    assert!(text.contains("ref = \"refs/heads/master\""), "{text}");
    assert!(base_line(dir.path(), "master"), "{text}");
}

/// Init ignores `.frob/`, installs the merge driver and leaves only config files in the working tree.
#[test]
fn init_touches_only_config_files_and_installs_the_driver() {
    let dir = repo("main", true);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    let ignore = std::fs::read_to_string(dir.path().join(".gitignore")).expect("gitignore");
    assert!(ignore.lines().any(|l| l == ".frob/"));
    git(
        dir.path(),
        &["config", "--local", "--get", "merge.frob-ledger.driver"],
    );
    let mut untracked: Vec<String> = std::fs::read_dir(dir.path())
        .expect("ls")
        .map(|e| e.expect("entry").file_name().to_string_lossy().into_owned())
        .filter(|n| n != ".git")
        .collect();
    untracked.sort();
    assert!(
        !untracked.iter().any(|n| n == "tickets" || n == ".frob"),
        "{untracked:?}"
    );
}

/// A feature branch with `main` present: the ledger ref names main, not the checkout.
#[test]
fn init_on_a_feature_branch_names_main_as_the_ledger_ref() {
    let dir = repo("main", true);
    git(dir.path(), &["switch", "-q", "-c", "feature"]);
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    let text = config_text(dir.path());
    assert!(text.contains("ref = \"refs/heads/main\""), "{text}");
    assert!(base_line(dir.path(), "main"), "{text}");
}

/// `--ledger-ref` overrides the detected default; a value that is not a branch ref is a usage error.
#[test]
fn init_ledger_ref_flag_overrides_and_is_validated() {
    let dir = repo("main", true);
    git(dir.path(), &["switch", "-q", "-c", "feature"]);
    let bad = frob(dir.path(), &["init", "--ledger-ref", "main"]);
    assert_eq!(bad.status.code(), Some(2), "{}", json(&bad));
    assert!(!dir.path().join("frob.toml").exists());
    let out = frob(dir.path(), &["init", "--ledger-ref", "refs/heads/feature"]);
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    assert!(config_text(dir.path()).contains("ref = \"refs/heads/feature\""));
}
