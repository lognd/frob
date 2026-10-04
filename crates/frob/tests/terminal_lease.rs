//! Terminal transitions release the lease; leases of terminal tickets are reaped by doctor.

use std::path::{Path, PathBuf};
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
use frob_lease::{Holder, LeaseConfig, LeaseStore};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

/// A trunk-mode repository with `frob init` run and one commit.
struct Repo {
    dir: tempfile::TempDir,
}

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

impl Repo {
    fn new() -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
        git(dir.path(), &["config", "user.name", "Test User"]);
        git(dir.path(), &["config", "user.email", "test@example.com"]);
        git(dir.path(), &["config", "core.autocrlf", "false"]);
        let repo = Self { dir };
        assert_eq!(code(&repo.frob(&["init"])), 0);
        git(repo.path(), &["add", "-A"]);
        git(repo.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn path(&self) -> &Path {
        self.dir.path()
    }

    fn frob(&self, args: &[&str]) -> Output {
        Command::cargo_bin("frob")
            .expect("frob binary")
            .current_dir(self.path())
            .env_remove("FROB_LOG")
            .arg("--json")
            .args(args)
            .output()
            .expect("run frob")
    }

    fn ok(&self, args: &[&str]) -> Value {
        let out = self.frob(args);
        assert_eq!(
            code(&out),
            0,
            "{args:?}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        json(&out)
    }

    /// A ticket with `scope`, leased to `actor`.
    fn leased(&self, actor: &str, scope: &str) -> (String, frob_ledger::TicketId) {
        let id = self.ok(&["ticket", "new", "--title", "t", "--scope", scope])["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned();
        let tid: frob_ledger::TicketId = id.parse().expect("ulid");
        let holder = Holder {
            actor: actor.to_owned(),
            worktree: PathBuf::from("/wt/other"),
        };
        self.store()
            .acquire(tid, &holder, &[scope.to_owned()])
            .expect("acquire");
        (id, tid)
    }

    fn store(&self) -> LeaseStore {
        let repo = gob_git::Repo::discover(self.path()).expect("discover");
        LeaseStore::open(&repo, LeaseConfig::default()).expect("store")
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

const CLOSE: [&str; 7] = [
    "--outcome",
    "done",
    "--no-evidence",
    "--no-changelog",
    "--no-land",
    "--reason",
    "x",
];

fn close(repo: &Repo, id: &str) -> Value {
    let mut args = vec!["ticket", "close", id];
    args.extend(CLOSE);
    repo.ok(&args)
}

#[test]
fn close_releases_the_lease() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    close(&repo, &id);
    assert!(repo.store().live_lease(t).expect("read").is_none());
    let (_, t2) = repo.leased("Test User", "b/**");
    assert!(repo.store().live_lease(t2).expect("read").is_some());
}

#[test]
fn drop_releases_the_lease() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    repo.ok(&["ticket", "drop", &id, "--reason", "no"]);
    assert!(repo.store().live_lease(t).expect("read").is_none());
}

#[test]
fn doctor_reports_then_reaps_a_lease_of_a_terminal_ticket() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    // An older binary left the lease behind: close, then recreate it.
    close(&repo, &id);
    let holder = Holder {
        actor: "Test User".to_owned(),
        worktree: PathBuf::from("/wt/other"),
    };
    repo.store()
        .acquire(t, &holder, &["a/**".to_owned()])
        .expect("reacquire");
    let report = repo.frob(&["ticket", "doctor"]);
    assert!(String::from_utf8_lossy(&report.stdout).contains("E-DOCTOR-TERMINAL-LEASE"));
    assert!(repo.store().live_lease(t).expect("read").is_some());
    let fixed = repo.ok(&["ticket", "doctor", "--fix"]);
    assert_eq!(fixed["data"]["reaped_leases"], serde_json::json!([id]));
    assert!(repo.store().live_lease(t).expect("read").is_none());
}
