//! `release status` end to end: the readiness report is always exit 0.
// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q

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
        self.titled(ty, "t")
    }

    fn titled(&self, ty: &str, title: &str) -> String {
        self.ok(&["ticket", "new", "--title", title, "--type", ty])["data"]["id"]
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

fn fragment(repo: &Repo, id: &str, kind: &str, body: &str) -> std::path::PathBuf {
    let dir = repo.dir.path().join("changelog.d");
    std::fs::create_dir_all(&dir).expect("mkdir");
    let p = dir.join(format!("{id}.{kind}.md"));
    std::fs::write(&p, body).expect("write fragment");
    p
}

fn report(v: &Value) -> &Value {
    &v["data"]["report"]
}

fn kinds(v: &Value) -> Vec<String> {
    report(v)["blockers"]
        .as_array()
        .expect("blockers")
        .iter()
        .map(|b| b["kind"].as_str().expect("kind").to_owned())
        .collect()
}

fn milestone(repo: &Repo, criteria: &[&str]) {
    let mut a = vec!["milestone", "new", "0.532.0", "--goal", "Ship PM"];
    for c in criteria {
        a.push("--criterion");
        a.push(c);
    }
    repo.ok(&a);
}

#[test]
fn an_unevidenced_criterion_is_listed_and_the_exit_is_zero() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    milestone(&repo, &["first", "second"]);
    std::fs::write(repo.dir.path().join("proof.txt"), "proof").expect("write");
    repo.ok(&[
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        "file",
        "--ref",
        "proof.txt",
        "--accepts",
        "1",
    ]);
    let out = repo.frob(&["release", "status"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["verb"], "release.status");
    let r = report(&v);
    assert_eq!(r["version"], "0.532.0");
    assert_eq!(r["ready"], false);
    assert_eq!(r["criteria"][0]["state"], "bound");
    assert_eq!(r["criteria"][0]["evidence"][0]["provider"], "file");
    assert_eq!(r["criteria"][1]["state"], "unbound");
    assert_eq!(kinds(&v), ["unbound-criterion"]);
    assert_eq!(r["verdict"], "NOT READY: 1 blocker");
    let unresolved = r["unresolved"].to_string();
    assert!(
        unresolved.contains("not checked yet (~4PT3KZB)"),
        "{unresolved}"
    );
    assert!(unresolved.contains("no history yet") && unresolved.contains("owner action"));
}

#[test]
fn everything_ready_prints_ready_and_the_changelog_preview() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    // frob:tests crates/frob-release/src/status.rs::assess
    let repo = Repo::new();
    milestone(&repo, &["only"]);
    std::fs::write(repo.dir.path().join("proof.txt"), "proof").expect("write");
    repo.ok(&[
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        "file",
        "--ref",
        "proof.txt",
        "--accepts",
        "1",
    ]);
    let t = repo.ticket("task");
    fragment(&repo, &t, "added", "frob: Added release status.\n");
    let v = repo.ok(&["release", "status", "0.532.0"]);
    let r = report(&v);
    assert_eq!(r["ready"], true);
    assert_eq!(r["verdict"], "READY");
    assert!(r["blockers"].as_array().expect("blockers").is_empty());
    assert_eq!(r["fragments"]["state"], "valid");
    assert!(
        r["changelog_preview"]
            .as_str()
            .expect("preview")
            .contains("Added release status.")
    );
    let out = repo.run(&["--text", "release", "status"]);
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.contains("0.532.0: READY"), "{text}");
}

#[test]
fn open_tickets_of_member_epics_are_listed_by_category_and_block() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    milestone(&repo, &[]);
    let epic = repo.titled("epic", "The epic");
    let child = repo.titled("task", "Child work");
    repo.ok(&[
        "ticket",
        "update",
        &child,
        "--set",
        &format!("parent={epic}"),
    ]);
    let done = repo.titled("task", "Finished work");
    repo.ok(&[
        "ticket",
        "update",
        &done,
        "--set",
        &format!("parent={epic}"),
    ]);
    repo.ok(&[
        "ticket",
        "close",
        &done,
        "--outcome",
        "done",
        "--no-evidence",
        "--reason",
        "test",
    ]);
    repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    let v = repo.ok(&["release", "status"]);
    let r = report(&v);
    let groups = &r["open_tickets"];
    let listed = groups.to_string();
    assert!(listed.contains("Child work"), "{listed}");
    assert!(!listed.contains("Finished work") && !listed.contains("The epic"));
    assert_eq!(kinds(&v), ["open-ticket"]);
}

#[test]
fn a_ticket_claiming_the_release_outside_its_epics_surfaces_pm034() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    // frob:tests crates/frob-pm/src/rules/membership.rs::claimants
    let repo = Repo::new();
    milestone(&repo, &[]);
    let epic = repo.titled("epic", "The epic");
    repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    let stray = repo.titled("task", "Stray work");
    repo.ok(&["ticket", "update", &stray, "--add-label", "release:0.532.0"]);
    let v = repo.ok(&["release", "status"]);
    let r = report(&v);
    assert_eq!(r["pm034"].as_array().expect("pm034").len(), 1);
    assert!(r["pm034"][0].as_str().expect("msg").contains("Stray work"));
    let k = kinds(&v);
    assert!(
        k.contains(&"pm034".to_owned()) && k.contains(&"open-ticket".to_owned()),
        "{k:?}"
    );
}

#[test]
fn label_claims_are_listed_before_the_milestone_object_exists() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    let t = repo.titled("task", "Claimed work");
    repo.ok(&["ticket", "update", &t, "--add-label", "release:0.532.0"]);
    let out = repo.frob(&["release", "status", "0.532.0"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert!(
        report(&v)["open_tickets"]
            .to_string()
            .contains("Claimed work")
    );
    assert_eq!(kinds(&v)[0], "no-milestone");
}

#[test]
fn invalid_fragments_are_reported_without_failing_the_command() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    milestone(&repo, &[]);
    let dir = repo.dir.path().join("changelog.d");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(dir.join("oops.md"), "frob: x\n").expect("write");
    let out = repo.frob(&["release", "status"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    let r = report(&v);
    assert_eq!(r["fragments"]["state"], "invalid");
    assert!(
        r["fragments"]["errors"][0]
            .as_str()
            .expect("e")
            .contains("changelog.d/oops.md")
    );
    assert_eq!(kinds(&v), ["invalid-fragment"]);
    assert!(r["changelog_preview"].is_null());
}

#[test]
fn no_milestone_at_all_is_a_helpful_message_and_exit_zero() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    let out = repo.frob(&["release", "status"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["data"]["outcome"], "no-milestone");
    assert!(v["data"]["report"].is_null());
    assert!(
        v["data"]["message"]
            .as_str()
            .expect("message")
            .contains("frob milestone new")
    );
}

#[test]
fn the_default_version_is_the_lowest_open_milestone() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.10.0", "--goal", "later"]);
    repo.ok(&["milestone", "new", "0.9.0", "--goal", "sooner"]);
    let v = repo.ok(&["release", "status"]);
    assert_eq!(report(&v)["version"], "0.9.0");
}
