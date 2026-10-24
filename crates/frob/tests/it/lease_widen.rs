//! `ticket update` and `lease widen` keep a held lease in step with the ticket scope.

use crate::common;

use std::path::{Path, PathBuf};
use std::process::Output;
use std::time::Duration;

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
        common::frob_command()
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
        LeaseStore::open(
            &repo,
            LeaseConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
        .expect("store")
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

// frob:ticket 01M4D6NSC2DP2P09F4QTR723S3
#[test]
fn lease_release_frees_the_lease_and_is_idempotent_and_holder_only() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Someone Else", "a/**");
    assert_eq!(code(&repo.frob(&["lease", "release", &id])), 3);
    assert!(repo.store().live_lease(t).expect("read").is_some());
    let (id, t) = repo.leased("Test User", "b/**");
    let first = repo.ok(&["lease", "release", &id]);
    assert_eq!(first["already"], false);
    assert!(repo.store().live_lease(t).expect("read").is_none());
    assert_eq!(repo.ok(&["lease", "release", &id])["already"], true);
}

/// A `frob` child running on a thread, with a signal for when it has reported a blocking holder.
struct Spawned {
    /// Fires once the child has printed its `waiting` line, i.e. it is parked on the held overlap.
    waiting: std::sync::mpsc::Receiver<()>,
    /// Joins to the child's full output.
    handle: std::thread::JoinHandle<Output>,
}

impl Spawned {
    /// Block until the child is waiting on the holder (condition-based, no sleep).
    fn wait_until_blocked(&self) {
        self.waiting
            .recv_timeout(Duration::from_secs(30))
            .expect("the child reports the blocking holder");
    }

    /// Join the child and return its output.
    fn join(self) -> std::thread::Result<Output> {
        self.handle.join()
    }
}

/// Run a real `frob` process with `args` on a thread (stderr is only observable live from a process); the caller releases the blocker once it reports waiting.
fn spawn(repo: &Repo, args: &[&str]) -> Spawned {
    use std::io::{BufRead, BufReader, Read};
    use std::process::Stdio;
    let dir = repo.path().to_path_buf();
    let args: Vec<String> = args.iter().map(|a| (*a).to_owned()).collect();
    let (tx, rx) = std::sync::mpsc::channel();
    let handle = std::thread::spawn(move || {
        let mut child = std::process::Command::new(common::process_command().get_program())
            .env("PATH", common::hermetic_path())
            .env_remove("FROB_LOG")
            .current_dir(dir)
            .arg("--json")
            .args(args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("run frob");
        let mut out = child.stdout.take().expect("stdout");
        let stdout_reader = std::thread::spawn(move || {
            let mut buf = Vec::new();
            out.read_to_end(&mut buf).expect("read stdout");
            buf
        });
        let mut stderr = Vec::new();
        let mut lines = BufReader::new(child.stderr.take().expect("stderr"));
        let mut line = Vec::new();
        while lines.read_until(b'\n', &mut line).expect("read stderr") > 0 {
            if line.starts_with(b"waiting") {
                let _ = tx.send(());
            }
            stderr.append(&mut line);
        }
        let status = child.wait().expect("wait");
        Output {
            status,
            stdout: stdout_reader.join().expect("stdout thread"),
            stderr,
        }
    });
    Spawned {
        waiting: rx,
        handle,
    }
}

// frob:ticket 01M4HW9J243ZJRMVYW51K18GCM
// frob:tests Update.run
#[test]
fn add_scope_wait_blocks_on_a_held_overlap_and_succeeds_when_it_releases() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    let (_, other) = repo.leased("Someone Else", "b/**");
    let child = spawn(
        &repo,
        &[
            "ticket",
            "update",
            &id,
            "--add-scope",
            "b/x.rs",
            "--wait",
            "60",
        ],
    );
    child.wait_until_blocked();
    repo.store().release(other, None).expect("release");
    let out = child.join().expect("join");
    assert_eq!(code_of(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    assert!(
        String::from_utf8_lossy(&out.stderr).contains("Someone Else"),
        "the holder is reported: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert_eq!(repo.lease_scope(t), ["a/**", "b/x.rs"]);
    assert_eq!(
        repo.ticket_scope(&id),
        serde_json::json!(["a/**", "b/x.rs"])
    );
}

// frob:tests Update.run
#[test]
fn add_scope_wait_expiry_returns_the_original_held_error_and_leaves_state() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    repo.leased("Someone Else", "b/**");
    for wait in ["0", "1"] {
        let out = repo.frob(&[
            "ticket",
            "update",
            &id,
            "--add-scope",
            "b/x.rs",
            "--wait",
            wait,
        ]);
        assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
        assert!(String::from_utf8_lossy(&out.stdout).contains("E-LEASE-HELD"));
    }
    assert_eq!(repo.ticket_scope(&id), serde_json::json!(["a/**"]));
    assert_eq!(repo.lease_scope(t), ["a/**"]);
}

// frob:tests LeaseWiden.run
#[test]
fn lease_widen_wait_succeeds_once_the_holder_releases() {
    let repo = Repo::new();
    let (id, t) = repo.leased("Test User", "a/**");
    let (_, other) = repo.leased("Someone Else", "b/**");
    let child = spawn(
        &repo,
        &["lease", "widen", &id, "--glob", "b/x.rs", "--wait", "60"],
    );
    child.wait_until_blocked();
    repo.store().release(other, None).expect("release");
    let out = child.join().expect("join");
    assert_eq!(code_of(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(repo.lease_scope(t), ["a/**", "b/x.rs"]);
}

fn code_of(out: &std::process::Output) -> i32 {
    out.status.code().expect("exit code")
}
