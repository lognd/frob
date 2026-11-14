//! `frob plan --from-design`: idempotent creation of tickets that implement design anchors.
// frob:ticket 01M4FDBDC401KMNN4C12QTA3PK
// frob:ticket 01M6PJTS38G6EGSH32FPD01BKM

#![cfg(unix)]

use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::process::Output;

use serde_json::Value;

use crate::common;

const GRAPH: &str = r#"{"schema":"grimble.graph/1","entities":[{"anchor":"goal/web","kind":"goal","status":"declared","status_hi":null,"name":"Web"},{"anchor":"impl/web.server","kind":"impl","status":"declared","status_hi":null,"name":"Server"}],"obligations":[],"edges":[{"from":"impl/web.server","to":"goal/web","kind":"serves"}]}"#;

fn frob(dir: &Path, grimble: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .env("FROB_GRIMBLE", grimble)
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn data(out: &Output) -> Value {
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    let v: Value = serde_json::from_slice(&out.stdout).expect("json");
    v["data"].clone()
}

/// Run `git args` in `dir`, asserting success.
fn git_in(dir: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

/// A fresh git repository on `main` with `frob init` applied and committed.
fn initialised_repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    git_in(root, &["init", "-q"]);
    git_in(root, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git_in(root, &["config", "user.name", "Test User"]);
    git_in(root, &["config", "user.email", "test@example.com"]);
    assert!(
        common::frob_command()
            .current_dir(root)
            .arg("init")
            .output()
            .expect("init")
            .status
            .success()
    );
    git_in(root, &["add", "-A"]);
    git_in(root, &["commit", "-q", "-m", "base"]);
    dir
}

// frob:tests crates/frob/src/plan_cmd.rs::Plan.run
#[test]
fn a_second_apply_proposes_nothing_and_every_ticket_implements_an_anchor() {
    let dir = initialised_repo();
    let script = dir.path().join("fake-grimble");
    std::fs::write(&script, format!("#!/bin/sh\ncat <<'EOF'\n{GRAPH}\nEOF\n")).expect("script");
    std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).expect("chmod");

    let first = data(&frob(
        dir.path(),
        &script,
        &["plan", "--from-design", "--apply"],
    ));
    assert_eq!(
        first["proposed"].as_array().expect("rows").len(),
        2,
        "{first}"
    );
    let anchors: Vec<&str> = first["proposed"]
        .as_array()
        .expect("rows")
        .iter()
        .map(|r| r["anchor"].as_str().expect("anchor"))
        .collect();
    assert!(anchors.contains(&"goal/web") && anchors.contains(&"impl/web.server"));

    let second = data(&frob(
        dir.path(),
        &script,
        &["plan", "--from-design", "--apply"],
    ));
    assert!(
        second["proposed"].as_array().expect("rows").is_empty(),
        "{second}"
    );
}

const GRAPH_REQ: &str = r#"{"schema":"grimble.graph/1","entities":[{"anchor":"goal/a","kind":"goal","status":"declared","status_hi":null,"name":"A"},{"anchor":"goal/b","kind":"goal","status":"declared","status_hi":null,"name":"B"},{"anchor":"impl/a.x","kind":"impl","status":"declared","status_hi":null,"name":"X","files":["src/x.rs"]},{"anchor":"step/odd","kind":"step","status":"declared","status_hi":null,"name":"Odd"}],"obligations":[{"rule":"PLAN001","kind":"unimplemented_step","anchor":"step/odd","detail":"d"}],"edges":[{"from":"goal/a","to":"goal/b","kind":"requires"},{"from":"impl/a.x","to":"goal/a","kind":"serves"}]}"#;

// frob:tests crates/frob/src/plan_cmd.rs::Plan.run
#[test]
fn requires_becomes_blocked_by_scope_is_seeded_and_findings_list_unmapped() {
    let dir = initialised_repo();
    let script = dir.path().join("fake-grimble");
    std::fs::write(
        &script,
        format!("#!/bin/sh\ncat <<'EOF'\n{GRAPH_REQ}\nEOF\n"),
    )
    .expect("script");
    std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).expect("chmod");

    let out = data(&frob(
        dir.path(),
        &script,
        &["plan", "--from-design", "--findings"],
    ));
    let rows = out["proposed"].as_array().expect("rows");
    let a = rows.iter().find(|r| r["anchor"] == "goal/a").expect("a");
    assert_eq!(a["blocked_by"][0], "goal/b", "{out}");
    let x = rows.iter().find(|r| r["anchor"] == "impl/a.x").expect("x");
    assert_eq!(x["scope"][0], "src/x.rs", "{out}");
    assert_eq!(out["unmapped"][0], "step/odd", "{out}");

    let applied = data(&frob(
        dir.path(),
        &script,
        &["plan", "--from-design", "--apply"],
    ));
    let first = applied["proposed"][0]["anchor"].as_str().expect("anchor");
    assert_eq!(
        first, "goal/b",
        "requires targets are created first: {applied}"
    );
}
