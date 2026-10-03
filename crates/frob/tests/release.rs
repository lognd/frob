//! `release changelog` end to end: compile, dry-run, check and the exit-3 refusals.
// frob:ticket 01M4069W8ECWEPBH6YPAR7X0X0

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
        let toml = repo.dir.path().join("frob.toml");
        let text = std::fs::read_to_string(&toml).expect("frob.toml");
        std::fs::write(
            &toml,
            text.replace("tag = \"v{version}\"", "tag = \"{product}-v{version}\"")
                .replace("products = []", "products = [\"frob\", \"grimble\"]"),
        )
        .expect("write frob.toml");
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

fn fragment(repo: &Repo, id: &str, kind: &str, body: &str) -> std::path::PathBuf {
    let dir = repo.dir.path().join("changelog.d");
    std::fs::create_dir_all(&dir).expect("mkdir");
    let p = dir.join(format!("{id}.{kind}.md"));
    std::fs::write(&p, body).expect("write fragment");
    p
}

#[test]
fn compiles_fragments_grouped_by_product_and_type_and_removes_them() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseChangelog.run
    let repo = Repo::new();
    let a = repo.ticket("task");
    let b = repo.ticket("task");
    let fa = fragment(&repo, &a, "added", "frob: Added a thing.\n");
    let fb = fragment(&repo, &b, "fixed", "gob: Fixed a gob thing.\n");
    let dry = repo.ok(&["release", "changelog", "--version", "0.532.0", "--dry-run"]);
    assert_eq!(dry["data"]["written"], false);
    assert!(fa.exists() && fb.exists());
    let v = repo.ok(&[
        "release",
        "changelog",
        "--version",
        "0.532.0",
        "--date",
        "2026-10-03",
    ]);
    assert_eq!(v["data"]["written"], true);
    let text = std::fs::read_to_string(repo.dir.path().join("CHANGELOG.md")).expect("changelog");
    assert!(text.contains("## 0.532.0 - 2026-10-03"), "{text}");
    assert!(text.contains("### frob") && text.contains("### gob"));
    assert!(text.contains(&a) && !text.contains("tickets/"));
    assert!(!fa.exists() && !fb.exists());
    repo.ok(&["release", "changelog", "--version", "0.532.0", "--check"]);
}

#[test]
fn check_refuses_a_malformed_name_with_exit_3_naming_the_file() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseChangelog.run
    let repo = Repo::new();
    let dir = repo.dir.path().join("changelog.d");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(dir.join("oops.md"), "frob: x\n").expect("write");
    let out = repo.frob(&["release", "changelog", "--version", "0.532.0", "--check"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let v = json(&out);
    assert!(
        v["error"]["message"]
            .as_str()
            .expect("message")
            .contains("changelog.d/oops.md")
    );
}

#[test]
fn a_ulid_that_is_not_a_ticket_is_refused() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseChangelog.run
    let repo = Repo::new();
    let p = fragment(&repo, "01ARZ3NDEKTSV4RRFFQ69G5FAV", "added", "frob: x\n");
    let out = repo.frob(&["release", "changelog", "--version", "0.532.0"]);
    assert_eq!(code(&out), 3);
    assert!(p.exists());
}

#[test]
fn release_notes_prints_exactly_one_versions_section_body() {
    // frob:ticket 01M41B4KPWQVBT234N2DY20758
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseNotes.run
    let repo = Repo::new();
    let a = repo.ticket("task");
    fragment(&repo, &a, "added", "frob: Added a thing.\n");
    repo.ok(&[
        "release",
        "changelog",
        "--version",
        "0.1.0",
        "--date",
        "2026-10-03",
    ]);
    let b = repo.ticket("task");
    fragment(&repo, &b, "fixed", "frob: Fixed a thing.\n");
    repo.ok(&[
        "release",
        "changelog",
        "--version",
        "0.2.0",
        "--date",
        "2026-10-04",
    ]);
    let v = repo.ok(&["release", "notes", "--version", "0.1.0"]);
    let notes = v["data"]["notes"].as_str().expect("notes");
    assert!(notes.starts_with("### frob"), "{notes}");
    assert!(notes.contains("Added a thing.") && !notes.contains("Fixed a thing."));
    assert!(
        !notes.contains("## 0.1.0") && !notes.contains("frob-section"),
        "{notes}"
    );
    let missing = repo.frob(&["release", "notes", "--version", "9.9.9"]);
    assert_eq!(code(&missing), 3);
    assert_eq!(json(&missing)["error"]["code"], "E-CHANGELOG-NO-SECTION");
}
