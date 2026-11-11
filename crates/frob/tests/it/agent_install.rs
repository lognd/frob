//! `frob agent install` and its uninstall counterpart for the native hooks, against tmp homes.
// frob:ticket 01M4P2N1GFSA69RHJR4D41NVHV

use std::path::Path;
use std::process::Output;

use serde_json::{Value, json};

use crate::common;

const USER: &str = r#"{"model": "x", "hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "mine.sh"}]}]}}"#;

/// A git repo that `frob init` has set up (every verb needs one).
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

fn run(home: &Path, verb: &str, extra: &[&str]) -> Output {
    let home_arg = gob_path::Shown::with_home(home, None);
    let mut args = vec![
        "agent",
        verb,
        "--agent",
        "claude",
        "--home",
        home_arg.as_str(),
    ];
    args.extend_from_slice(extra);
    let repo = repo();
    common::frob_command()
        .current_dir(repo.path())
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn read(home: &Path) -> Vec<u8> {
    std::fs::read(home.join("settings.json")).unwrap()
}

fn settings(home: &Path) -> Value {
    serde_json::from_slice(&read(home)).unwrap()
}

fn home_with(text: &str) -> tempfile::TempDir {
    let home = tempfile::tempdir().unwrap();
    std::fs::write(home.path().join("settings.json"), text).unwrap();
    home
}

fn commands(s: &Value) -> Vec<String> {
    s["hooks"]
        .as_object()
        .unwrap()
        .values()
        .flat_map(|g| g.as_array().unwrap())
        .flat_map(|g| g["hooks"].as_array().unwrap())
        .map(|e| e["command"].as_str().unwrap().to_owned())
        .collect()
}

// frob:tests crates/frob/src/agent_install_cmd.rs::AgentInstall
#[test]
fn install_adds_marked_text_mode_entries_and_keeps_user_keys() {
    let home = home_with(USER);
    let out = run(home.path(), "install", &[]);
    assert_eq!(out.status.code(), Some(0));
    let s = settings(home.path());
    assert_eq!(s["model"], "x");
    assert_eq!(
        s["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
        "mine.sh"
    );
    assert!(
        commands(&s)
            .contains(&"frob agent hook pre-bash --text # frob-owned:native-pre-bash".to_owned())
    );
}

// frob:tests crates/frob/src/agent/mod.rs::Emitter.install_native
// frob:tests crates/frob/src/agent_install_cmd.rs::AgentInstall
#[test]
fn a_second_install_leaves_identical_bytes() {
    let home = home_with(USER);
    run(home.path(), "install", &[]);
    let first = read(home.path());
    let out = run(home.path(), "install", &[]);
    assert_eq!(out.status.code(), Some(0));
    assert_eq!(read(home.path()), first);
}

// frob:tests crates/frob/src/agent_install_cmd.rs::AgentInstall
#[test]
fn uninstall_removes_only_marked_entries_added_before_or_after() {
    let home = home_with(USER);
    run(home.path(), "install", &[]);
    let mut s = settings(home.path());
    s["hooks"]["Stop"]
        .as_array_mut()
        .unwrap()
        .push(json!({"hooks": [{"type": "command", "command": "after.sh"}]}));
    std::fs::write(home.path().join("settings.json"), s.to_string()).unwrap();
    let out = run(home.path(), "uninstall", &[]);
    assert_eq!(out.status.code(), Some(0));
    let mut left = commands(&settings(home.path()));
    left.sort();
    assert_eq!(left, ["after.sh", "mine.sh"]);
}

// frob:tests crates/frob/src/agent_install_cmd.rs::AgentInstall
#[test]
fn install_check_writes_nothing_and_prints_the_plan() {
    let home = home_with(USER);
    let out = run(home.path(), "install", &["--check"]);
    assert_eq!(out.status.code(), Some(0));
    assert_eq!(read(home.path()), USER.as_bytes());
    let v: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(v["data"]["agents"][0]["hooks"][0]["action"], "add");
}

// frob:tests crates/frob/src/agent_cmd.rs::AgentUninstall
#[test]
fn uninstall_dry_run_reports_the_removals_and_writes_nothing() {
    let home = home_with(USER);
    run(home.path(), "install", &[]);
    let before = read(home.path());
    let out = run(home.path(), "uninstall", &["--dry-run"]);
    assert_eq!(read(home.path()), before);
    let v: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(v["data"]["agents"][0]["registrations_removed"], 6);
}

// frob:tests crates/frob/src/agent_install_cmd.rs::AgentInstall
#[test]
fn install_reports_an_unowned_conflict_and_does_not_overwrite_it() {
    let theirs = r#"{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "frob agent hook stop"}]}]}}"#;
    let home = home_with(theirs);
    let out = run(home.path(), "install", &[]);
    let v: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(v["data"]["conflicts"], 1);
    assert_eq!(
        settings(home.path())["hooks"]["Stop"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
}

// frob:ticket 01M5BN07NSGG64QPAH5HWNF3RV
// frob:tests crates/frob/src/agent/mod.rs::Emitter.install_native
#[test]
fn install_keeps_the_existing_top_level_key_order() {
    let home = home_with(r#"{"zeta": 1, "alpha": 2, "model": "x"}"#);
    run(home.path(), "install", &[]);
    let keys: Vec<String> = settings(home.path())
        .as_object()
        .unwrap()
        .keys()
        .cloned()
        .collect();
    assert_eq!(keys, ["zeta", "alpha", "model", "hooks"]);
}
