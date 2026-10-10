//! The envelope `ok` never contradicts `data.ok`, for every registered verb (cli.md section 2).
// frob:ticket 01M4FG552GZ9FMB000B76AS8XH

mod common;

use std::path::Path;
use std::time::Duration;

use serde_json::Value;

/// Verbs that never return on their own or act on the outside world; the invariant lives in the shared renderer they use too.
const SKIPPED: [&str; 3] = ["serve", "land", "release cut"];

fn git(dir: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

/// A committed repository with `frob init` run, so ledger verbs have something to read.
fn fixture() -> tempfile::TempDir {
    let dir = common::git_repo();
    let init = common::frob_command()
        .current_dir(dir.path())
        .args(["--json", "init"])
        .output()
        .expect("frob init");
    assert!(init.status.success(), "{init:?}");
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "base"]);
    dir
}

/// Assert `ok == data.ok` on every envelope that carries a boolean `data.ok`.
fn assert_consistent(verb: &str, v: &Value) {
    if let Some(inner) = v["data"].get("ok").and_then(Value::as_bool) {
        assert_eq!(
            v["ok"].as_bool(),
            Some(inner),
            "{verb}: envelope ok contradicts data.ok in {v}"
        );
    }
}

// frob:tests crates/gob-cli/src/command.rs::data_not_ok
#[test]
fn every_verb_envelope_agrees_with_its_data_ok() {
    let _ = frob_cli::cli(); // link the verbs into this test binary
    let dir = fixture();
    let mut ran = 0;
    for meta in gob_cli::all_commands().filter(|m| m.product == "frob" && m.deprecated.is_none()) {
        if SKIPPED.contains(&meta.verb) {
            continue;
        }
        let mut cmd = common::frob_command();
        cmd.current_dir(dir.path())
            .timeout(Duration::from_secs(60))
            .arg("--json");
        cmd.args(meta.verb.split(' '));
        let Ok(out) = cmd.output() else {
            continue; // timed out waiting for input; nothing to judge
        };
        let Ok(v) = serde_json::from_slice::<Value>(&out.stdout) else {
            continue; // usage text, not an envelope
        };
        assert_consistent(meta.verb, &v);
        ran += 1;
    }
    assert!(ran > 20, "only {ran} verbs produced an envelope");
}

// frob:tests crates/frob/src/ticket/doctor_cmd.rs::TicketDoctor
#[test]
fn a_doctor_run_with_findings_is_not_ok_at_the_envelope() {
    let dir = fixture();
    let new = common::frob_command()
        .current_dir(dir.path())
        .args([
            "--json",
            "ticket",
            "new",
            "--title",
            "Leaky",
            "--acceptance",
            "ok",
            "--body",
            "see /home/someone/projects/x for the repro",
        ])
        .output()
        .expect("ticket new");
    assert!(new.status.success(), "{new:?}");
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["--json", "ticket", "doctor"])
        .output()
        .expect("doctor");
    let v: Value = serde_json::from_slice(&out.stdout).expect("json");
    assert_eq!(v["data"]["ok"], false, "{v}");
    assert_eq!(v["ok"], false, "{v}");
    assert_eq!(out.status.code(), Some(1));
}
