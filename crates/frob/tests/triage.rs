//! `ticket triage accept|decline|snooze|duplicate|list` against fixture ledgers (never a real one).
// frob:ticket 01M44C546DQRE4D11HHPM0HX6M

use std::path::Path;
use std::process::Output;

use assert_cmd::Command;
use serde_json::Value;

mod common;

/// A repository on `main` with `frob init` run and a base commit.
struct Repo {
    dir: tempfile::TempDir,
}

impl Repo {
    fn new() -> Self {
        let dir = common::git_repo();
        let repo = Self { dir };
        assert_eq!(code(&repo.frob(&["init"])), 0);
        let git = |args: &[&str]| {
            let s = std::process::Command::new("git")
                .args(args)
                .current_dir(repo.path())
                .status()
                .expect("git");
            assert!(s.success(), "git {args:?}");
        };
        git(&["config", "core.autocrlf", "false"]);
        git(&["add", "-A"]);
        git(&["commit", "-q", "-m", "base"]);
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

    /// A ticket created in `category` with the given labels.
    fn ticket(&self, title: &str, category: &str, labels: &[&str]) -> String {
        let mut args = vec!["ticket", "new", "--title", title, "--category", category];
        for l in labels {
            args.extend(["--label", l]);
        }
        self.ok(&args)["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned()
    }

    fn category(&self, id: &str) -> String {
        self.ok(&["ticket", "show", id])["data"]["ticket"]["front"]["category"]
            .as_str()
            .expect("category")
            .to_owned()
    }

    fn ledger_commits(&self) -> usize {
        let out = std::process::Command::new("git")
            .args(["rev-list", "--count", "refs/heads/main"])
            .current_dir(self.path())
            .output()
            .expect("git rev-list");
        String::from_utf8_lossy(&out.stdout)
            .trim()
            .parse()
            .expect("count")
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
fn accept_by_label_moves_every_match_to_todo_in_one_commit_and_reports_each() {
    let repo = Repo::new();
    let a = repo.ticket("First", "triage", &["triage:accepted"]);
    let b = repo.ticket("Second", "triage", &["triage:accepted"]);
    let other = repo.ticket("Third", "triage", &["triage:later"]);
    let todo = repo.ticket("Already todo", "todo", &["triage:accepted"]);
    let before = repo.ledger_commits();

    let out = repo.ok(&["ticket", "triage", "accept", "--label", "triage:accepted"]);
    assert_eq!(repo.ledger_commits(), before + 1, "one ledger commit");
    let entries = out["data"]["entries"].as_array().expect("entries");
    assert_eq!(entries.len(), 2, "{out}");
    for e in entries {
        assert_eq!(e["status"], "applied");
        assert_eq!(e["category"], "todo");
    }
    assert!(out["data"]["commit"].is_string());
    assert_eq!(repo.category(&a), "todo");
    assert_eq!(repo.category(&b), "todo");
    assert_eq!(repo.category(&other), "triage");
    assert_eq!(repo.category(&todo), "todo");

    assert_eq!(
        code(&repo.frob(&["ticket", "doctor"])),
        0,
        "fold equals frontmatter"
    );

    // Idempotent: the query now matches nothing and the repeat writes nothing.
    let again = repo.frob(&["ticket", "triage", "accept", "--label", "triage:accepted"]);
    assert_eq!(code(&again), 0);
    assert_eq!(
        json(&again)["data"]["entries"].as_array().expect("e").len(),
        0
    );
    assert_eq!(repo.ledger_commits(), before + 1);

    // Naming an accepted ticket again is `already`, with no commit.
    let named = repo.ok(&["ticket", "triage", "accept", &a]);
    assert_eq!(named["data"]["entries"][0]["status"], "already");
    assert_eq!(named["already"], true);
    assert_eq!(repo.ledger_commits(), before + 1);
}

#[test]
fn accept_refuses_a_ticket_not_in_triage_with_a_remedy_and_writes_nothing() {
    let repo = Repo::new();
    let in_triage = repo.ticket("Inbox", "triage", &[]);
    let todo = repo.ticket("Queued", "todo", &[]);
    let before = repo.ledger_commits();
    let out = repo.frob(&["ticket", "triage", "accept", &in_triage, &todo]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.contains("E-TRIAGE-NOT-IN-TRIAGE"), "{text}");
    assert!(text.contains("frob ticket triage list"), "{text}");
    assert_eq!(repo.ledger_commits(), before, "nothing written");
    assert_eq!(repo.category(&in_triage), "triage");
}

#[test]
fn a_snoozed_ticket_is_hidden_until_its_date_and_shown_after() {
    let repo = Repo::new();
    let id = repo.ticket("Later", "triage", &[]);
    let kept = repo.ticket("Now", "triage", &[]);
    repo.ok(&[
        "ticket",
        "triage",
        "snooze",
        &id,
        "--until",
        "2999-01-01",
        "--reason",
        "next year",
    ]);
    let ids = |args: &[&str]| -> Vec<String> {
        repo.ok(args)["data"]["tickets"]
            .as_array()
            .expect("tickets")
            .iter()
            .map(|t| t["id"].as_str().expect("id").to_owned())
            .collect()
    };
    assert_eq!(ids(&["ticket", "triage", "list"]), vec![kept.clone()]);
    assert_eq!(
        ids(&["ticket", "triage", "list", "--at", "2998-12-31"]),
        vec![kept.clone()]
    );
    assert_eq!(
        ids(&["ticket", "triage", "list", "--at", "2999-01-01"]),
        vec![id.clone(), kept.clone()]
    );
    let all = repo.ok(&["ticket", "triage", "list", "--all"]);
    assert_eq!(all["data"]["count"], 2);
    assert!(all["data"]["tickets"][0]["snoozed_until"].is_string());
    // A snooze does not leave triage, and repeating it is a no-op.
    assert_eq!(repo.category(&id), "triage");
    let again = repo.ok(&["ticket", "triage", "snooze", &id, "--until", "2999-01-01"]);
    assert_eq!(again["already"], true);
    // A query accept leaves the snoozed ticket alone.
    let tagged = repo.ticket("Tagged", "triage", &["x"]);
    repo.ok(&[
        "ticket",
        "triage",
        "snooze",
        &tagged,
        "--until",
        "2999-01-01",
    ]);
    let none = repo.ok(&["ticket", "triage", "accept", "--label", "x"]);
    assert_eq!(none["data"]["entries"].as_array().expect("e").len(), 0);
}

#[test]
fn snooze_needs_a_future_date_and_decline_a_reason() {
    let repo = Repo::new();
    let id = repo.ticket("Soon", "triage", &[]);
    let past = repo.frob(&["ticket", "triage", "snooze", &id, "--until", "2001-01-01"]);
    assert_eq!(code(&past), 2, "{}", String::from_utf8_lossy(&past.stdout));
    let bad = repo.frob(&["ticket", "triage", "snooze", &id, "--until", "someday"]);
    assert_eq!(code(&bad), 2);
    let bare = repo.frob(&["ticket", "triage", "decline", &id]);
    assert_eq!(code(&bare), 2, "{}", String::from_utf8_lossy(&bare.stdout));
    let nothing = repo.frob(&["ticket", "triage", "accept"]);
    assert_eq!(code(&nothing), 2);
}

#[test]
fn decline_closes_wont_fix_and_duplicate_closes_with_a_link() {
    let repo = Repo::new();
    let noise = repo.ticket("Noise", "triage", &[]);
    let dup = repo.ticket("Dup", "triage", &[]);
    let orig = repo.ticket("Original", "todo", &[]);

    let declined = repo.ok(&[
        "ticket", "triage", "decline", &noise, "--reason", "not ours",
    ]);
    assert_eq!(declined["data"]["entries"][0]["outcome"], "wont-fix");
    let shown = repo.ok(&["ticket", "show", &noise]);
    assert_eq!(shown["data"]["ticket"]["front"]["category"], "done");
    assert_eq!(shown["data"]["ticket"]["front"]["outcome"], "wont-fix");
    let again = repo.ok(&[
        "ticket", "triage", "decline", &noise, "--reason", "not ours",
    ]);
    assert_eq!(again["already"], true);

    let before = repo.ledger_commits();
    let closed = repo.ok(&["ticket", "triage", "duplicate", &dup, "--of", &orig]);
    assert_eq!(repo.ledger_commits(), before + 1, "link and close together");
    assert_eq!(closed["data"]["entries"][0]["outcome"], "duplicate");
    let shown = repo.ok(&["ticket", "show", &dup]);
    assert_eq!(shown["data"]["ticket"]["front"]["outcome"], "duplicate");
    let links = shown["data"]["ticket"]["front"]["links"].to_string();
    assert!(
        links.contains("duplicates") && links.contains(&orig),
        "{links}"
    );
    let events = repo.ok(&["ticket", "show", &dup, "--events"]);
    let kinds: Vec<&str> = events["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .map(|e| e["kind"].as_str().expect("kind"))
        .collect();
    assert_eq!(kinds, ["create", "link", "transition", "triage"]);

    // Not in triage any more: a different decision is refused.
    let late = repo.frob(&["ticket", "triage", "accept", &dup]);
    assert_eq!(code(&late), 3);
}
