//! `[lease] shared_files` reaches every verb that opens the lease store.

mod common;

use std::path::Path;
use std::process::Output;
use std::time::Duration;

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

/// A repository on `main` with `frob init` run, `shared` as `[lease] shared_files`, worktrees in `wt`.
fn repo(shared: &str, wt: &Path) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    git(dir.path(), &["init", "-q"]);
    git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(dir.path(), &["config", "user.name", "Test User"]);
    git(dir.path(), &["config", "user.email", "test@example.com"]);
    git(dir.path(), &["config", "core.autocrlf", "false"]);
    assert_eq!(code(&frob(dir.path(), &["init"])), 0);
    let toml = dir.path().join("frob.toml");
    let base = std::fs::read_to_string(&toml).expect("frob.toml");
    let extra = format!(
        "\n[lease]\nshared_files = [{shared}]\n\n[worktree]\ndir = {:?}\n",
        wt.display().to_string()
    );
    std::fs::write(&toml, base + &extra).expect("write frob.toml");
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "base"]);
    dir
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

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn ok(dir: &Path, args: &[&str]) -> Value {
    let out = frob(dir, args);
    let text = String::from_utf8_lossy(&out.stdout).into_owned();
    assert_eq!(code(&out), 0, "{args:?}: {text}");
    serde_json::from_str(&text).expect("json")
}

/// A ticket scoped to `a/**` style glob plus `Cargo.lock`.
fn ticket(dir: &Path, glob: &str) -> String {
    ok(
        dir,
        &[
            "ticket",
            "new",
            "--title",
            "t",
            "--scope",
            glob,
            "--scope",
            "Cargo.lock",
        ],
    )["data"]["handle"]
        .as_str()
        .expect("handle")
        .to_owned()
}

// frob:tests crates/frob-lease/src/lib.rs::open_store
#[test]
fn work_grants_two_leases_that_share_a_shared_file() {
    let wt = tempfile::tempdir().expect("wt");
    let dir = repo("\"Cargo.lock\"", wt.path());
    let a = ticket(dir.path(), "a/**");
    let b = ticket(dir.path(), "b/**");
    ok(dir.path(), &["work", &a]);
    ok(dir.path(), &["work", &b]);
    let leases = ok(dir.path(), &["lease", "list"]);
    assert_eq!(leases["data"]["leases"].as_array().map(Vec::len), Some(2));
    let contention = ok(dir.path(), &["ticket", "contention"]);
    let files = contention["data"]["files"].as_array().expect("files");
    assert!(
        files.iter().all(|f| !f.to_string().contains("Cargo.lock")),
        "shared file reported as contended: {files:?}"
    );
}

#[test]
fn work_refuses_the_second_lease_when_the_file_is_not_shared() {
    let wt = tempfile::tempdir().expect("wt");
    let dir = repo("", wt.path());
    let a = ticket(dir.path(), "a/**");
    let b = ticket(dir.path(), "b/**");
    ok(dir.path(), &["work", &a]);
    let out = frob(dir.path(), &["work", &b]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
}
