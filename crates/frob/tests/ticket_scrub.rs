//! `ticket doctor --fix` scrubs absolute home paths out of the ledger in one commit and the ledger still folds the same.

mod common;

use std::path::{Path, PathBuf};
use std::process::Output;
use std::time::Duration;

use frob_evidence::record::digest_hex;
use frob_ledger::event::{Event, EventBody, EvidenceData};
use frob_ledger::{Ledger, LedgerConfig, RefMode};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

// frob:ticket 01M41RHBJ03PGD6JY0J6JTAH9Q

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
            .env("HOME", "/home/ann")
            .arg("--json")
            .args(args)
            .output()
            .expect("run frob")
    }

    fn json(&self, args: &[&str]) -> (i32, Value) {
        let out = self.frob(args);
        let v = serde_json::from_slice(&out.stdout).unwrap_or(Value::Null);
        (code(&out), v)
    }

    fn ledger(&self) -> Ledger {
        let repo = gob_git::Repo::discover(self.path()).expect("discover");
        let cfg = LedgerConfig {
            mode: RefMode::Branch,
            ..LedgerConfig::default()
        };
        Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock))
    }
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn tip(repo: &Repo) -> String {
    git(repo.path(), &["rev-parse", "HEAD"])
}

/// A repository whose ledger holds the old-style paths: a body, a lease-like event and an evidence transcript.
fn dirty() -> (Repo, String, PathBuf) {
    let repo = Repo::new();
    let parent = repo.path().parent().expect("parent").to_path_buf();
    let name = repo
        .path()
        .file_name()
        .expect("name")
        .to_string_lossy()
        .into_owned();
    let (_, v) = repo.json(&[
        "ticket",
        "new",
        "--title",
        "Dirty",
        "--acceptance",
        "it works",
        "--body",
        "built in /home/ann/work/app and /home/bob/other",
    ]);
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    let ledger = repo.ledger();
    let tid: frob_ledger::TicketId = id.parse().expect("ticket id");
    let transcript = format!(
        "Compiling x ({}/crates/x)\nsibling {}/{name}-wt/T1/y\nhome /home/ann/.cargo and /home/bob/z\nok\n",
        repo.path().display(),
        parent.display()
    );
    let mut record = toml::Table::new();
    record.insert("provider".into(), "command".into());
    record.insert("ref".into(), "cargo test".into());
    record.insert("digest".into(), digest_hex(transcript.as_bytes()).into());
    record.insert("status".into(), "measured".into());
    record.insert(
        "captured_at".into(),
        gob_time::Clock::now(&gob_time::SystemClock)
            .to_string()
            .into(),
    );
    record.insert("passed".into(), true.into());
    record.insert("inline".into(), transcript.clone().into());
    record.insert(
        "size".into(),
        i64::try_from(transcript.len()).expect("len").into(),
    );
    let ev = Event::new(
        gob_time::Clock::now(&gob_time::SystemClock),
        "ann",
        EventBody::Evidence(EvidenceData {
            accepts: vec![1],
            record,
        }),
    );
    let path = format!("tickets/{id}/events/{}", ev.file_name());
    std::fs::write(repo.path().join(&path), ev.to_toml().expect("toml")).expect("write event");
    let lease = format!(
        "kind = \"lease\"\nat = \"{}\"\nactor = \"a\"\nrev = 1\nreason = \"lease: ann in /home/ann/projects/{name}-wt/T2 and C:\\\\Users\\\\bo\\\\p\\\\{name}-wt\\\\T3; scope: x\"\n",
        gob_time::Clock::now(&gob_time::SystemClock)
    );
    let lease_ev = Event::parse(frob_ledger::EventId::mint(), &lease).expect("lease");
    std::fs::write(
        repo.path()
            .join(format!("tickets/{id}/events/{}", lease_ev.file_name())),
        lease,
    )
    .expect("write lease");
    git(repo.path(), &["add", "-A"]);
    git(repo.path(), &["commit", "-q", "-m", "dirty ledger"]);
    ledger.reconcile(tid).expect("reconcile");
    (repo, id, parent)
}

/// With `--fix` one commit scrubs the ledger, every ticket shows the same state and evidence binding, and a second run does nothing.
// frob:tests crates/frob/src/ticket/doctor_cmd.rs::scrub_ledger
#[test]
fn doctor_fix_scrubs_in_one_commit_and_the_ticket_shows_the_same() {
    let (repo, id, _parent) = dirty();
    let (_, plain) = repo.json(&["ticket", "doctor"]);
    assert_eq!(plain["data"]["ok"], false);
    let rules: Vec<&str> = plain["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter_map(|f| f["rule"].as_str())
        .collect();
    assert!(
        rules.iter().all(|r| *r == "TICK004") && rules.len() >= 3,
        "{rules:?}"
    );

    let list_before = repo.json(&["ticket", "list"]).1["data"].clone();
    let show_before = repo.json(&["ticket", "show", &id]).1["data"]["fields"].clone();
    let base = tip(&repo);

    let (c, fixed) = repo.json(&["ticket", "doctor", "--fix"]);
    assert_eq!(c, 0, "{fixed}");
    assert_eq!(fixed["data"]["ok"], true, "{fixed}");
    assert!(fixed["findings"].as_array().expect("findings").is_empty());
    assert_eq!(fixed["data"]["scrub_digests"], 1);
    assert_eq!(fixed["data"]["scrubbed_tickets"][0], id.as_str());
    let commit = fixed["data"]["scrub_commit"].as_str().expect("commit");
    assert_eq!(git(repo.path(), &["rev-parse", "HEAD"]), commit);
    assert_eq!(
        git(repo.path(), &["rev-parse", "HEAD~1"]),
        base,
        "exactly one forward commit"
    );
    assert_eq!(
        git(repo.path(), &["log", "-1", "--format=%s"])
            .split(':')
            .next(),
        Some("tickets(scrub)")
    );

    let list_after = repo.json(&["ticket", "list"]).1["data"].clone();
    let show_after = repo.json(&["ticket", "show", &id]).1["data"]["fields"].clone();
    assert_eq!(list_after, list_before, "ticket list is unchanged");
    assert!(show_before.is_object(), "{show_before}");
    let mut expect = show_before.clone();
    let body = expect["body"]
        .as_str()
        .expect("body")
        .replace("/home/ann", "~")
        .replace("/home/bob", "~other");
    expect["body"] = body.into();
    assert_eq!(show_after, expect, "only the scrubbed text differs");

    let again_tip = tip(&repo);
    let (c, again) = repo.json(&["ticket", "doctor", "--fix"]);
    assert_eq!(c, 0);
    assert_eq!(
        again["data"]["scrubbed"].as_array().expect("files").len(),
        0,
        "{again}"
    );
    assert_eq!(again["data"]["scrub_commit"], Value::Null);
    assert_eq!(tip(&repo), again_tip, "idempotent: no new commit");
}

/// Sibling worktrees become the form relative to the repository parent, other homes `~other`, and the repo root `<repo>`.
// frob:tests crates/frob-evidence/src/scrub.rs::PathScrub.for_repair
#[test]
fn placeholders_follow_the_repair_rules() {
    let (repo, id, _parent) = dirty();
    let name = repo
        .path()
        .file_name()
        .expect("name")
        .to_string_lossy()
        .into_owned();
    let (c, fixed) = repo.json(&["ticket", "doctor", "--fix"]);
    assert_eq!(c, 0, "{fixed}");
    let events = std::fs::read_dir(repo.path().join(format!("tickets/{id}/events"))).expect("dir");
    let mut all = String::new();
    for e in events {
        all.push_str(&std::fs::read_to_string(e.expect("entry").path()).expect("read"));
    }
    assert!(
        all.contains(&format!("{name}-wt/T2")),
        "lease reason: {all}"
    );
    assert!(
        all.contains(&format!("{name}-wt\\\\T3")),
        "windows-style sibling on any host: {all}"
    );
    assert!(!all.contains("Users"), "{all}");
    assert!(!all.contains("/home/ann"), "{all}");
    assert!(all.contains("~other/z"), "{all}");
    assert!(all.contains("~/.cargo"), "{all}");
    assert!(all.contains("<repo>/crates/x"), "{all}");
    assert!(all.contains(&format!("sibling {name}-wt/T1/y")), "{all}");
}
