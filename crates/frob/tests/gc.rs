//! The automatic garbage-collection pass through the real verbs: `work`, `doctor` and the throttle stamp.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
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
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn new_ticket(repo: &Repo, scope: &str) -> String {
    repo.ok(&["ticket", "new", "--title", "t", "--scope", scope])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned()
}

/// Turn the disk guard off so a low-disk host cannot force extra passes into the count.
fn no_guard(repo: &Repo) {
    let path = repo.path().join("frob.toml");
    let text = std::fs::read_to_string(&path).expect("frob.toml");
    std::fs::write(path, format!("{text}\n[gc]\nguard_min_free_gb = 0\n")).expect("write");
}

fn passes(repo: &Repo) -> u64 {
    let stamp = repo.path().join(".git").join("frob").join("gc.json");
    let text = std::fs::read_to_string(stamp).expect("gc stamp");
    serde_json::from_str::<Value>(&text).expect("json")["passes"]
        .as_u64()
        .expect("passes")
}

// frob:tests crates/frob-worktree/src/gc/pass.rs::run
#[test]
fn work_runs_one_pass_then_the_interval_throttles_the_next() {
    let repo = Repo::new();
    no_guard(&repo);
    let a = new_ticket(&repo, "a/**");
    let b = new_ticket(&repo, "b/**");
    repo.ok(&["work", &a]);
    assert_eq!(passes(&repo), 1, "the first work runs a pass");
    repo.ok(&["work", &b]);
    assert_eq!(
        passes(&repo),
        1,
        "a pass ran within the interval, so none runs"
    );
}

// frob:tests crates/frob/src/doctor.rs::gc_info
#[test]
fn doctor_reports_the_last_pass_and_fix_runs_one_unthrottled() {
    let repo = Repo::new();
    no_guard(&repo);
    let before = repo.ok(&["doctor"])["data"]["gc"].clone();
    assert_eq!(before["state"], "ok");
    assert_eq!(before["passes"], 0);
    assert!(before["last_run_unix"].is_null());
    assert!(before["usage"].as_array().expect("usage").len() >= 4);
    let fixed = repo.ok(&["doctor", "--fix"]);
    assert_eq!(fixed["data"]["gc"]["fixed"]["reclaimed_bytes"], 0);
    let again = repo.ok(&["doctor", "--fix"]);
    assert!(again["data"]["gc"]["fixed"].is_object(), "not throttled");
    let after = repo.ok(&["doctor"])["data"]["gc"].clone();
    assert_eq!(after["passes"], 2);
    assert!(after["last_run_unix"].is_i64());
    assert_eq!(
        code(&repo.frob(&["doctor"])),
        0,
        "findings never fail doctor"
    );
}
