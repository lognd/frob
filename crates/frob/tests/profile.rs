//! `frob profile`: the default, setting it, and the one-time switch suggestion.

mod common;

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

// frob:ticket 01M3ZX87FNRDNXXC2VTYPHN173
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
        common::set_done_requires(repo.dir.path(), &[]);
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn frob(&self, args: &[&str]) -> Output {
        common::frob_command()
            .current_dir(self.dir.path())
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

    fn close_one(&self, title: &str) {
        let id = self.ok(&["ticket", "new", "--title", title, "--type", "chore"])["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned();
        self.ok(&["ticket", "close", &id, "--outcome", "done"]);
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
fn fresh_clone_is_newcomer_and_experienced_is_recorded() {
    let repo = Repo::new();
    let v = repo.ok(&["profile"]);
    assert_eq!(v["data"]["profile"], "newcomer");
    assert_eq!(v["data"]["chosen"], false);
    let set = repo.ok(&["profile", "experienced"]);
    assert_eq!(set["data"]["profile"], "experienced");
    let stored = std::fs::read_to_string(repo.dir.path().join(".frob/profile.toml"))
        .expect("profile.toml written");
    assert!(stored.contains("profile = \"experienced\""), "{stored}");
    assert_eq!(repo.ok(&["profile"])["data"]["profile"], "experienced");
    assert_eq!(repo.ok(&["profile", "experienced"])["already"], true);
}

#[test]
fn third_closed_ticket_suggests_switching_once() {
    let repo = Repo::new();
    for t in ["a", "b"] {
        repo.close_one(t);
    }
    let before = repo.ok(&["profile"]);
    assert_eq!(before["data"]["suggested"], false, "{before}");
    repo.close_one("c");
    let third = repo.ok(&["profile"]);
    assert_eq!(third["data"]["suggested"], true, "{third}");
    assert_eq!(third["data"]["closed_by_actor"], 3);
    assert!(
        third["warnings"][0]
            .as_str()
            .is_some_and(|w| w.contains("frob profile experienced")),
        "{third}"
    );
    let again = repo.ok(&["profile"]);
    assert_eq!(again["data"]["suggested"], false, "{again}");
    assert_eq!(again["data"]["profile"], "newcomer");
}

// frob:ticket 01M4MMGDBXRGC9X90CZPPSKN6Z
#[test]
fn the_closed_count_stops_at_the_suggestion_threshold() {
    let repo = Repo::new();
    for t in ["a", "b", "c", "d", "e"] {
        repo.close_one(t);
    }
    let first = repo.ok(&["profile"]);
    assert_eq!(first["data"]["suggested"], true, "{first}");
    assert_eq!(
        first["data"]["closed_by_actor"], 3,
        "the scan must stop at SUGGEST_AFTER instead of reading every done ticket: {first}"
    );
}
