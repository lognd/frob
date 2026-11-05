//! `frob plan --from-design`: idempotent creation of tickets that implement design anchors.
// frob:ticket 01M4FDBDC401KMNN4C12QTA3PK

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

// frob:tests crates/frob/src/plan_cmd.rs::Plan.run
#[test]
fn a_second_apply_proposes_nothing_and_every_ticket_implements_an_anchor() {
    let dir = tempfile::tempdir().expect("tempdir");
    let git = |args: &[&str]| {
        let st = std::process::Command::new("git")
            .args(args)
            .current_dir(dir.path())
            .status()
            .expect("git");
        assert!(st.success(), "git {args:?}");
    };
    git(&["init", "-q"]);
    git(&["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(&["config", "user.name", "Test User"]);
    git(&["config", "user.email", "test@example.com"]);
    assert!(
        common::frob_command()
            .current_dir(dir.path())
            .arg("init")
            .output()
            .expect("init")
            .status
            .success()
    );
    git(&["add", "-A"]);
    git(&["commit", "-q", "-m", "base"]);
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
