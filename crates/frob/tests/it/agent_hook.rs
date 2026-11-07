//! `frob agent hook`: reads hook JSON on stdin, prints the reply JSON, fails open on bad input.
// frob:ticket 01M4P2N1D8ZJN8A3EDD9T7ZT21

use std::io::Write;
use std::process::Stdio;

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

/// Run `frob --text agent hook EVENT` with `stdin`; return exit code, stdout and stderr.
fn hook(dir: &std::path::Path, event: &str, stdin: &str) -> (Option<i32>, String, String) {
    let mut child = std::process::Command::new(env!("CARGO_BIN_EXE_frob"))
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .args(["--text", "agent", "hook", event])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn");
    child
        .stdin
        .take()
        .expect("stdin")
        .write_all(stdin.as_bytes())
        .expect("write");
    let out = child.wait_with_output().expect("wait");
    (
        out.status.code(),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

// frob:tests crates/frob/src/agent_hook_cmd.rs::AgentHook
#[test]
fn pre_read_denies_a_big_whole_file_read() {
    let dir = repo();
    let big = dir.path().join("big.txt");
    std::fs::write(&big, "x".repeat(300_000)).expect("write");
    let payload = serde_json::json!({"tool_input": {"file_path": big}}).to_string();
    let (code, out, _) = hook(dir.path(), "pre-read", &payload);
    assert_eq!(code, Some(0));
    let v: Value = serde_json::from_str(out.trim()).expect("reply json");
    assert_eq!(v["hookSpecificOutput"]["permissionDecision"], "deny");
}

// frob:tests crates/frob/src/agent_hook_cmd.rs::AgentHook
#[test]
fn pre_bash_routes_heavy_commands_to_frob_agent_heavy() {
    let dir = repo();
    let payload = r#"{"tool_input": {"command": "cargo test -p x"}}"#;
    let (_, out, _) = hook(dir.path(), "pre-bash", payload);
    let v: Value = serde_json::from_str(out.trim()).expect("reply json");
    let reason = v["hookSpecificOutput"]["permissionDecisionReason"]
        .as_str()
        .expect("reason");
    assert!(reason.contains("frob agent heavy"), "{reason}");
}

// frob:tests crates/frob/src/agent_hook_cmd.rs::AgentHook
#[test]
fn malformed_stdin_fails_open_with_a_warning() {
    let dir = repo();
    let (code, out, err) = hook(dir.path(), "pre-bash", "{not json");
    assert_eq!(code, Some(0));
    assert_eq!(out.trim(), "{}");
    assert!(err.contains("hook payload unusable"), "{err}");
}

// frob:tests crates/frob/src/agent_hook_cmd.rs::AgentHook
#[test]
fn session_start_outside_a_lease_still_replies_with_json() {
    let dir = repo();
    let (code, out, _) = hook(dir.path(), "session-start", "{}");
    assert_eq!(code, Some(0));
    assert!(serde_json::from_str::<Value>(out.trim()).is_ok(), "{out}");
}

/// The `guard` rows of `.frob/telemetry.jsonl` under `dir`.
fn guard_rows(dir: &std::path::Path) -> Vec<Value> {
    std::fs::read_to_string(dir.join(".frob/telemetry.jsonl"))
        .unwrap_or_default()
        .lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .filter(|v| v["kind"] == "guard")
        .collect()
}

// frob:tests crates/frob/src/agent_hook_cmd.rs::AgentHook
#[test]
fn every_hook_guard_logs_bytes_avoided_to_telemetry() {
    let dir = repo();
    let big = dir.path().join("big.txt");
    std::fs::write(&big, "x".repeat(300_000)).expect("write");
    let read = serde_json::json!({"tool_input": {"file_path": big}}).to_string();
    hook(dir.path(), "pre-read", &read);
    hook(
        dir.path(),
        "pre-bash",
        r#"{"tool_input": {"command": "cargo test -p x"}}"#,
    );
    hook(
        dir.path(),
        "pre-bash",
        r#"{"tool_input": {"command": "git log"}}"#,
    );
    let rows = guard_rows(dir.path());
    let names: Vec<&str> = rows.iter().filter_map(|r| r["guard"].as_str()).collect();
    assert_eq!(names, ["pre-read", "pre-bash-heavy", "pre-bash-cap"]);
    assert_eq!(rows[0]["bytes_avoided"], 300_000);
    assert_eq!(rows[0]["basis"], "file_size");
    assert_eq!(rows[1]["basis"], "unmeasured");
}
