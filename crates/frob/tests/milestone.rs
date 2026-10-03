//! `milestone new`, `add`, `show` and `list`: acceptance, refusals and idempotency.

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
        assert_eq!(code(&repo.run(&["--json", "init"])), 0);
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn run(&self, args: &[&str]) -> Output {
        Command::cargo_bin("frob")
            .expect("frob binary")
            .current_dir(self.dir.path())
            .env_remove("FROB_LOG")
            .args(args)
            .output()
            .expect("run frob")
    }

    fn frob(&self, args: &[&str]) -> Output {
        let mut a = vec!["--json"];
        a.extend_from_slice(args);
        self.run(&a)
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

    fn ticket(&self, ty: &str) -> String {
        self.ok(&["ticket", "new", "--title", "t", "--type", ty])["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned()
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
fn new_creates_the_milestone_with_unbound_criteria() {
    let repo = Repo::new();
    let v = repo.ok(&[
        "milestone",
        "new",
        "0.532.0",
        "--goal",
        "Ship PM",
        "--target",
        "2026-11-01",
        "--criterion",
        "a, b stays whole",
        "--criterion",
        "second",
    ]);
    assert_eq!(v["verb"], "milestone.new");
    assert_eq!(v["already"], false);
    let m = &v["data"]["milestone"];
    assert_eq!(m["version"], "0.532.0");
    assert_eq!(m["goal"], "Ship PM");
    assert_eq!(m["target"], "2026-11-01");
    assert_eq!(m["state"], "open");
    let c = m["criteria"].as_array().expect("criteria");
    assert_eq!(c.len(), 2);
    assert_eq!(c[0]["text"], "a, b stays whole");
    assert_eq!(c[0]["position"], 1);
    assert_eq!(c[0]["bound"], false);
    assert_eq!(c[1]["bound"], false);
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    assert_eq!(shown["data"]["milestone"]["criteria"], m["criteria"]);
}

#[test]
fn new_repeat_is_already_and_a_different_repeat_is_refused() {
    let repo = Repo::new();
    let args = [
        "milestone",
        "new",
        "0.532.0",
        "--goal",
        "g",
        "--criterion",
        "c",
    ];
    assert_eq!(repo.ok(&args)["already"], false);
    let again = repo.ok(&args);
    assert_eq!(again["already"], true);
    assert_eq!(again["data"]["commit"], Value::Null);
    let out = repo.frob(&["milestone", "new", "0.532.0", "--goal", "other"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-MILESTONE-EXISTS");
    assert!(e["message"].as_str().expect("message").contains("goal"));
    assert_eq!(e["remedy"], "frob milestone show 0.532.0");
    assert_eq!(repo.ok(&["milestone", "list"])["data"]["count"], 1);
}

#[test]
fn non_semver_version_is_refused_with_a_remedy() {
    let repo = Repo::new();
    for bad in ["v1", "1.2", "01.2.3", "latest"] {
        let out = repo.frob(&["milestone", "new", bad, "--goal", "g"]);
        assert_eq!(
            code(&out),
            2,
            "{bad}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        let e = &json(&out)["error"];
        assert_eq!(e["code"], "E-MILESTONE-VERSION");
        assert!(
            e["remedy"]
                .as_str()
                .expect("remedy")
                .contains("MAJOR.MINOR.PATCH")
        );
    }
    assert_eq!(repo.ok(&["milestone", "list"])["data"]["count"], 0);
}

#[test]
fn add_lists_the_epic_in_show_and_a_repeat_is_already() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let epic = repo.ticket("epic");
    let first = repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    assert_eq!(first["already"], false);
    let again = repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    assert_eq!(again["already"], true);
    assert_eq!(again["data"]["events"].as_array().expect("events").len(), 0);
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    let epics = shown["data"]["milestone"]["epics"]
        .as_array()
        .expect("epics");
    assert_eq!(epics.len(), 1);
    assert_eq!(epics[0]["id"], epic.as_str());
    assert_eq!(epics[0]["title"], "t");
}

#[test]
fn add_refuses_a_ticket_that_is_not_an_epic() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let task = repo.ticket("task");
    let out = repo.frob(&["milestone", "add", &task, "0.532.0"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-MILESTONE-NOT-EPIC");
    assert!(e["remedy"].is_string());
    let shown = repo.ok(&["milestone", "show", "0.532.0"]);
    assert_eq!(
        shown["data"]["milestone"]["epics"]
            .as_array()
            .expect("epics")
            .len(),
        0
    );
}

#[test]
fn show_of_an_unknown_version_suggests_existing_ones() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "g"]);
    let out = repo.frob(&["milestone", "show", "0.533.0"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-MILESTONE-NOT-FOUND");
    assert!(
        e["message"]
            .as_str()
            .expect("message")
            .contains("did you mean 0.532.0")
    );
    assert_eq!(e["remedy"], "frob milestone show 0.532.0");
}

#[test]
fn schema_works_without_positionals() {
    let repo = Repo::new();
    for verb in ["new", "add", "show", "list"] {
        let out = repo.run(&["--schema", "milestone", verb]);
        assert_eq!(
            code(&out),
            0,
            "{verb}: {}",
            String::from_utf8_lossy(&out.stderr)
        );
        assert!(json(&out).is_object(), "{verb}");
    }
}

#[test]
fn text_view_shows_the_milestone() {
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.532.0", "--goal", "Ship PM"]);
    let out = repo.run(&["--format", "text", "milestone", "show", "0.532.0"]);
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(
        text.contains("0.532.0") && text.contains("Ship PM"),
        "{text}"
    );
}
