//! `ticket doctor` and the merge driver over milestones and cycles, against temporary repositories.

mod common;

use std::path::{Path, PathBuf};
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

// frob:ticket 01M4095RVEYWMEWQJFT5Y8JFGW

fn git(dir: &Path, args: &[&str]) -> String {
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
        "git {args:?}: {}{}",
        out.stdout,
        out.stderr
    );
    out.stdout.trim().to_owned()
}

/// A trunk-mode repository with `frob init` run and the merge driver configured (path of this build).
struct Repo {
    dir: tempfile::TempDir,
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
        // `frob init` writes the driver itself; the merge below runs exactly what a user gets.
        let toml = repo.path().join("frob.toml");
        let text = std::fs::read_to_string(&toml).expect("frob.toml");
        std::fs::write(
            &toml,
            text.replace("ref_mode = \"trunk\"", "ref_mode = \"branch\""),
        )
        .expect("write");
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
        serde_json::from_slice(&out.stdout).expect("json")
    }

    fn milestone_file(&self, id: &str) -> PathBuf {
        self.path()
            .join(format!("tickets/_milestones/{id}/milestone.md"))
    }
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn milestone_id(repo: &Repo) -> String {
    repo.ok(&["milestone", "show", "0.1.0"])["data"]["milestone"]["id"]
        .as_str()
        .expect("id")
        .to_owned()
}

#[test]
fn doctor_reports_a_drifted_milestone_and_a_dangling_cycle_member_and_fix_repairs_them() {
    // frob:tests crates/frob/src/ticket/doctor_cmd.rs::TicketDoctor
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.1.0", "--goal", "first"]);
    let ticket = repo.ok(&["ticket", "new", "--title", "Member"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let cycle = repo.ok(&["cycle", "new", "--start", "2026-01-05", "--goal", "sprint"]);
    let cycle = cycle["data"]["cycle"]["id"]
        .as_str()
        .expect("cycle id")
        .to_owned();
    repo.ok(&["ticket", "update", &ticket, "--points", "1"]);
    repo.ok(&["cycle", "assign", &ticket, &cycle]);
    let clean = repo.ok(&["ticket", "doctor"]);
    assert_eq!(clean["data"]["ok"], true, "{clean}");
    assert_eq!(clean["data"]["milestones"], 1);
    assert_eq!(clean["data"]["cycles"], 1);

    let id = milestone_id(&repo);
    let file = repo.milestone_file(&id);
    let text = std::fs::read_to_string(&file).expect("milestone.md");
    assert!(text.contains("goal = \"first\""), "{text}");
    std::fs::write(
        &file,
        text.replace("goal = \"first\"", "goal = \"tampered\""),
    )
    .expect("write");
    git(repo.path(), &["rm", "-rq", &format!("tickets/{ticket}")]);
    git(repo.path(), &["add", "-A"]);
    git(repo.path(), &["commit", "-q", "-m", "tamper"]);

    // frob:ticket 01M4FG552GZ9FMB000B76AS8XH
    let bad_out = repo.frob(&["ticket", "doctor"]);
    assert_eq!(code(&bad_out), 1, "issues exit 1 like any failed gate");
    let bad: Value = serde_json::from_slice(&bad_out.stdout).expect("json");
    assert_eq!(bad["data"]["ok"], false, "{bad}");
    assert_eq!(bad["ok"], false, "envelope ok follows data.ok: {bad}");
    let codes: Vec<&str> = bad["data"]["pm_issues"]
        .as_array()
        .expect("issues")
        .iter()
        .map(|i| i["code"].as_str().expect("code"))
        .collect();
    assert!(codes.contains(&"E-PM-DRIFT"), "{codes:?}");
    assert!(codes.contains(&"E-PM-MEMBER"), "{codes:?}");
    let kinds: Vec<&str> = bad["data"]["pm_issues"]
        .as_array()
        .expect("issues")
        .iter()
        .map(|i| i["kind"].as_str().expect("kind"))
        .collect();
    assert!(kinds.contains(&"milestone") && kinds.contains(&"cycle"));

    let fixed = repo.ok(&["ticket", "doctor", "--fix"]);
    assert!(
        fixed["data"]["pm_fixed"]
            .as_array()
            .expect("fixed")
            .iter()
            .any(|v| v == &Value::from(id.clone())),
        "{fixed}"
    );
    // The drift is repaired; the dangling member is the only problem left.
    let after = repo.ok(&["ticket", "doctor"]);
    let left: Vec<&str> = after["data"]["pm_issues"]
        .as_array()
        .expect("issues")
        .iter()
        .map(|i| i["code"].as_str().expect("code"))
        .collect();
    assert!(!left.contains(&"E-PM-DRIFT"), "{left:?}");
}

#[test]
fn concurrent_milestone_edits_on_two_branches_merge_with_both_events_and_a_refolded_frontmatter() {
    // frob:tests crates/frob/src/ticket/merge_cmd.rs::MergeDriver
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.1.0", "--goal", "first"]);
    let id = milestone_id(&repo);
    git(repo.path(), &["checkout", "-q", "-b", "side"]);
    repo.ok(&["milestone", "criterion", "add", "0.1.0", "from side"]);
    git(repo.path(), &["checkout", "-q", "main"]);
    repo.ok(&["milestone", "criterion", "add", "0.1.0", "from main"]);

    git(repo.path(), &["merge", "--no-edit", "side"]);

    let events = repo.path().join(format!("tickets/_milestones/{id}/events"));
    let count = std::fs::read_dir(&events).expect("events").count();
    assert_eq!(count, 3, "create + one event per branch");
    let text = std::fs::read_to_string(repo.milestone_file(&id)).expect("milestone.md");
    assert!(!text.contains("<<<<<<<"), "{text}");
    assert!(
        text.contains("from side") && text.contains("from main"),
        "{text}"
    );
    let doctor = repo.ok(&["ticket", "doctor"]);
    assert_eq!(doctor["data"]["ok"], true, "{doctor}");
    assert_eq!(doctor["data"]["pm_events"], 3);
}

#[test]
fn merge_driver_verb_refolds_a_milestone_path() {
    // frob:tests crates/frob/src/ticket/merge_cmd.rs::MergeDriver
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.1.0", "--goal", "first"]);
    let id = milestone_id(&repo);
    let scratch = repo.path().join("ours.md");
    std::fs::write(&scratch, "<<<<<<< conflict").expect("seed");
    let path = format!("tickets/_milestones/{id}/milestone.md");
    let out = repo.frob(&["merge-driver", "base", "ours.md", "theirs", &path]);
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    let text = std::fs::read_to_string(&scratch).expect("ours");
    assert!(text.contains("goal = \"first\""), "{text}");
    assert_eq!(
        text,
        std::fs::read_to_string(repo.milestone_file(&id)).expect("file")
    );
}

#[test]
fn init_registers_milestone_and_cycle_attributes_once() {
    // frob:tests crates/frob/src/init.rs::Init
    let repo = Repo::new();
    let attrs = std::fs::read_to_string(repo.path().join(".gitattributes")).expect("attrs");
    assert_eq!(
        attrs,
        "tickets/**/ticket.md merge=frob-ledger\n\
         tickets/_milestones/*/milestone.md merge=frob-ledger\n\
         tickets/_cycles/*/cycle.md merge=frob-ledger\n"
    );
    let again = repo.ok(&["init"]);
    assert_eq!(again["data"]["gitattributes"]["changed"], false);
    assert_eq!(
        attrs,
        std::fs::read_to_string(repo.path().join(".gitattributes")).expect("attrs")
    );
}
