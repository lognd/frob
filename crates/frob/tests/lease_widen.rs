//! `ticket update` and `lease widen` keep a held lease in step with the ticket scope.

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

    fn lease_scope(&self, t: frob_ledger::TicketId) -> Vec<String> {
        self.store()
            .live_lease(t)
            .expect("read")
            .expect("lease")
            .scope
    }

    fn ticket_scope(&self, id: &str) -> Value {
        self.ok(&["ticket", "show", id])["data"]["fields"]["scope"].clone()
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

#[test]
fn update_by_the_holder_widens_and_narrows_the_lease() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    repo.ok(&["ticket", "update", &id, "--add-scope", "b/**"]);
    assert_eq!(repo.lease_scope(t), ["a/**", "b/**"]);
    repo.ok(&["ticket", "update", &id, "--set", "scope=c/**,d/**"]);
    assert_eq!(repo.lease_scope(t), ["c/**", "d/**"]);
    repo.ok(&["ticket", "update", &id, "--remove-scope", "d/**"]);
    assert_eq!(repo.lease_scope(t), ["c/**"]);
    repo.ok(&["ticket", "update", &id, "--clear", "scope"]);
    assert!(repo.lease_scope(t).is_empty());
}

#[test]
fn widening_into_another_live_lease_is_refused_and_the_ticket_is_unchanged() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    repo.leased("Someone Else", "b/**");
    let out = repo.frob(&["ticket", "update", &id, "--add-scope", "b/x.rs"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert!(String::from_utf8_lossy(&out.stdout).contains("E-LEASE-HELD"));
    assert_eq!(repo.ticket_scope(&id), serde_json::json!(["a/**"]));
    assert_eq!(repo.lease_scope(t), ["a/**"]);
}

#[test]
fn update_by_a_non_holder_succeeds_with_a_warning_naming_the_holder() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Someone Else", "a/**");
    let v = repo.ok(&["ticket", "update", &id, "--add-scope", "b/**"]);
    let warning = v["warnings"][0].as_str().expect("warning");
    assert!(warning.contains("Someone Else"), "{warning}");
    assert_eq!(repo.ticket_scope(&id), serde_json::json!(["a/**", "b/**"]));
    assert_eq!(repo.lease_scope(t), ["a/**"]);
    let out = repo.frob(&["lease", "widen", &id]);
    assert_eq!(code(&out), 3);
}

#[test]
fn lease_widen_rereads_the_scope_and_is_idempotent() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    // Simulate a scope change that bypassed the lease (another clone, a hand edit).
    repo.store().release(t, None).expect("release");
    repo.ok(&["ticket", "update", &id, "--add-scope", "b/**"]);
    let holder = Holder {
        actor: "Test User".to_owned(),
        worktree: PathBuf::from("/wt/other"),
    };
    repo.store()
        .acquire(t, &holder, &["a/**".to_owned()])
        .expect("reacquire");
    let first = repo.ok(&["lease", "widen", &id]);
    assert_eq!(first["data"]["scope"], serde_json::json!(["a/**", "b/**"]));
    assert_eq!(repo.lease_scope(t), ["a/**", "b/**"]);
    let second = repo.ok(&["lease", "widen", &id]);
    assert_eq!(second["already"], true);
    let with_glob = repo.ok(&["lease", "widen", &id, "--glob", "c/**"]);
    assert_eq!(with_glob["already"], false);
    assert_eq!(repo.lease_scope(t), ["a/**", "b/**", "c/**"]);
    assert_eq!(
        repo.ok(&["lease", "widen", &id, "--glob", "c/**"])["already"],
        true
    );
}

#[test]
fn lease_widen_without_a_lease_is_refused() {
    let repo = Repo::new();
    let id = repo.ok(&["ticket", "new", "--title", "t"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    assert_eq!(code(&repo.frob(&["lease", "widen", &id])), 3);
}
