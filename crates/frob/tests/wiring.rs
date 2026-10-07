//! The sibling-crate verbs wired into the `frob` binary: schemas, the evidence close guard and the lease check.

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

mod common;

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

/// A repository on `main` with `frob init` committed.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    git(dir.path(), &["init", "-q"]);
    git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(dir.path(), &["config", "user.name", "Test User"]);
    git(dir.path(), &["config", "user.email", "test@example.com"]);
    git(dir.path(), &["config", "core.autocrlf", "false"]);
    assert_eq!(code(&frob(dir.path(), &["init"])), 0);
    common::set_done_requires(dir.path(), &["no_open_children"]);
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "base"]);
    dir
}

fn frob(dir: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn ok(dir: &Path, args: &[&str]) -> Value {
    let out = frob(dir, args);
    assert_eq!(
        code(&out),
        0,
        "{args:?}: {}",
        String::from_utf8_lossy(&out.stdout)
    );
    json(&out)
}

fn new_ticket(dir: &Path, title: &str, ty: &str, scope: &str) -> String {
    ok(
        dir,
        &[
            "ticket", "new", "--title", title, "--type", ty, "--scope", scope,
        ],
    )["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned()
}

#[test]
fn sibling_verbs_print_schemas() {
    let dir = repo();
    // --schema waives every verb's required positionals.
    let cases: [&[&str]; 7] = [
        &["work", "--schema"],
        &["test", "--schema"],
        &["ack", "--schema"],
        &["ticket", "evidence", "add", "--schema"],
        &["ticket", "evidence", "list", "--schema"],
        &["ticket", "evidence", "fetch", "--schema"],
        &["ticket", "show", "--schema"],
    ];
    for args in cases {
        let out = frob(dir.path(), args);
        assert_eq!(
            code(&out),
            0,
            "{args:?}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        assert!(json(&out).is_object(), "{args:?}");
    }
}

#[test]
fn close_of_a_task_without_evidence_is_refused_with_the_test_remedy() {
    let dir = repo();
    let id = new_ticket(dir.path(), "needs evidence", "task", "src/**");
    let out = frob(dir.path(), &["ticket", "close", &id, "--outcome", "done"]);
    assert_eq!(code(&out), 3);
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-EVIDENCE-MISSING");
    assert!(
        v["error"]["remedy"]
            .as_str()
            .expect("remedy")
            .starts_with("frob test"),
        "{v}"
    );
}

#[test]
fn no_evidence_with_a_reason_closes_and_records_a_bypass_event() {
    let dir = repo();
    let id = new_ticket(dir.path(), "bypass", "task", "src/**");
    let missing = frob(
        dir.path(),
        &["ticket", "close", &id, "--outcome", "done", "--no-evidence"],
    );
    assert_eq!(
        code(&missing),
        2,
        "--no-evidence without --reason is a usage error"
    );
    let closed = ok(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-evidence",
            "--reason",
            "x",
        ],
    );
    assert_eq!(closed["data"]["category"], "done");
    let shown = ok(dir.path(), &["ticket", "show", &id, "--events"]);
    let kinds: Vec<_> = shown["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .map(|e| e["kind"].as_str().expect("kind"))
        .collect();
    assert!(kinds.contains(&"evidence-bypass"), "{kinds:?}");
}

#[test]
fn doable_hides_tickets_overlapping_a_live_lease_and_shows_them_otherwise() {
    let dir = repo();
    let held = new_ticket(dir.path(), "held", "chore", "src/**");
    let other = new_ticket(dir.path(), "overlapping", "chore", "src/lib.rs");
    let before = ok(dir.path(), &["ticket", "doable"]);
    assert_eq!(before["data"]["count"], 2, "no lease: both shown");
    ok(dir.path(), &["work", "--here", &held]);
    let after = ok(dir.path(), &["ticket", "doable"]);
    let ids: Vec<_> = after["data"]["tickets"]
        .as_array()
        .expect("tickets")
        .iter()
        .map(|t| t["id"].as_str().expect("id"))
        .collect();
    assert!(!ids.contains(&other.as_str()), "overlap hidden: {ids:?}");
}

#[test]
fn registry_files_alias_is_dropped_and_shared_tables_are_listed() {
    let dir = repo();
    let toml = dir.path().join("frob.toml");
    let text = std::fs::read_to_string(&toml).expect("frob.toml");
    let aliased = text.replacen(
        "[tickets]\n",
        "[tickets]\nregistry_files = [\"Cargo.lock\"]\n",
        1,
    );
    std::fs::write(&toml, aliased).expect("write");
    let refused = frob(dir.path(), &["config", "show", "--effective"]);
    assert_ne!(code(&refused), 0, "alias must be an unknown key");
    assert!(
        String::from_utf8_lossy(&refused.stdout).contains("registry_files"),
        "names the key: {}",
        String::from_utf8_lossy(&refused.stdout)
    );
    std::fs::write(&toml, text).expect("restore");
    let shown = ok(dir.path(), &["config", "show", "--effective"]);
    let tables: Vec<_> = shown["data"]["tables"]
        .as_array()
        .expect("tables")
        .iter()
        .map(|t| t["table"].as_str().expect("table"))
        .collect();
    for t in ["lease", "worktree", "evidence"] {
        assert!(tables.contains(&t), "{t} in {tables:?}");
    }
}

#[test]
fn ticket_evidence_actions_are_subcommands_with_their_own_help() {
    let dir = repo();
    let out = frob(dir.path(), &["ticket", "evidence", "--help"]);
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout).into_owned();
    for action in ["add", "list", "fetch"] {
        assert!(text.contains(action), "{action} missing from: {text}");
    }
    let add = frob(dir.path(), &["ticket", "evidence", "add", "--help"]);
    assert_eq!(code(&add), 0);
    let text = String::from_utf8_lossy(&add.stdout).into_owned();
    assert!(
        text.contains("--provider") && text.contains("--accepts"),
        "{text}"
    );
    let fetch = frob(dir.path(), &["ticket", "evidence", "fetch", "--help"]);
    assert!(String::from_utf8_lossy(&fetch.stdout).contains("INDEX"));
    // An unknown action is a usage error with the verb tree's suggestion.
    assert_eq!(code(&frob(dir.path(), &["ticket", "evidence", "nope"])), 2);
}
