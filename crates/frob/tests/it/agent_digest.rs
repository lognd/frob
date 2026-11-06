//! `frob agent digest`: stores full output content-addressed and prints a bounded summary.
// frob:ticket 01M4P2N1Q1F8PKS9FY2MRH4QCR

use crate::common;

use serde_json::Value;

/// A git repo that `frob init` has set up.
fn repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let init = common::frob_command()
        .current_dir(dir.path())
        .env_remove("FROB_LOG")
        .arg("init")
        .output()
        .expect("init");
    assert_eq!(init.status.code(), Some(0));
    dir
}

fn digest(dir: &std::path::Path, args: &[&str]) -> (Option<i32>, Value) {
    let out = common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(["agent", "digest", "--head", "2", "--tail", "2", "--"])
        .args(args)
        .output()
        .expect("run frob");
    let v = serde_json::from_slice(&out.stdout).expect("json");
    (out.status.code(), v)
}

// frob:tests crates/frob/src/agent_digest_cmd.rs::AgentDigest
#[test]
fn stores_output_and_summarises() {
    let dir = repo();
    let (code, v) = digest(dir.path(), &["sh", "-c", "seq 1 50; echo error: boom"]);
    assert_eq!(code, Some(0));
    let d = &v["data"];
    assert_eq!(d["exit_code"], 0);
    assert_eq!(d["total_lines"], 51);
    assert_eq!(d["head"].as_array().expect("head").len(), 2);
    assert_eq!(d["errors"][0], "51: error: boom");
    let stored = std::fs::read_to_string(
        dir.path()
            .join(".frob/artifacts")
            .join(format!("{}.log", d["address"].as_str().expect("address"))),
    )
    .expect("artifact");
    assert!(stored.starts_with("1\n2\n"));
}

// frob:tests crates/frob/src/agent_digest_cmd.rs::AgentDigest
#[test]
fn nonzero_exit_is_reported_and_fails_the_verb() {
    let dir = repo();
    let (code, v) = digest(dir.path(), &["sh", "-c", "echo hi; exit 7"]);
    assert_eq!(code, Some(1));
    assert_eq!(v["data"]["exit_code"], 7);
}

// frob:tests crates/frob/src/agent_digest_cmd.rs::AgentDigest
#[test]
fn summary_text_prints_the_wrapped_status() {
    let dir = repo();
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["--text", "agent", "digest", "--", "sh", "-c", "exit 0"])
        .output()
        .expect("run");
    assert!(String::from_utf8_lossy(&out.stdout).contains("wrapped command exit 0"));
}
