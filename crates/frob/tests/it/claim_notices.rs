//! `frob claim notices [--ack]` lists and acknowledges the idle notices of live claims.

use crate::common;

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

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
    serde_json::from_slice(&out.stdout).expect("json envelope")
}

/// A repo with one in-progress ticket leased to this checkout.
fn claimed() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    assert_eq!(frob(p, &["init"]).status.code(), Some(0));
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let out = frob(p, &["ticket", "new", "--title", "t", "--scope", "a/**"]);
    let id = json(&out)["data"]["id"].as_str().expect("id").to_owned();
    let start = frob(p, &["work", &id, "--here"]);
    assert_eq!(
        start.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&start.stdout)
    );
    (dir, id)
}

// frob:tests crates/frob/src/claim_notices_cmd.rs::ClaimNotices
#[test]
fn notices_lists_a_quiet_live_claim() {
    let (dir, _id) = claimed();
    let out = frob(dir.path(), &["claim", "notices"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let v = json(&out);
    let rows = v["data"]["notices"].as_array().expect("notices");
    assert_eq!(rows.len(), 1, "{v}");
    assert_eq!(rows[0]["mine"], true);
    assert_eq!(rows[0]["rank"], 0);
    assert!(v["data"]["acked"].as_array().expect("acked").is_empty());
}

// frob:tests crates/frob/src/claim_notices_cmd.rs::ClaimNotices
#[test]
fn notices_ack_with_nothing_to_silence_reports_no_handles() {
    let (dir, _id) = claimed();
    let out = frob(dir.path(), &["claim", "notices", "--ack"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let v = json(&out);
    assert!(
        v["data"]["acked"].as_array().expect("acked").is_empty(),
        "{v}"
    );
}
