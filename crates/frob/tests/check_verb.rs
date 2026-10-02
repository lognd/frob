//! `frob check` through the binary: exit codes, `--fail-on`, `--explain`, `--timing`.

use std::path::Path;

use assert_cmd::Command;
use serde_json::Value;

fn frob(dir: &Path, args: &[&str]) -> std::process::Output {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .current_dir(dir)
        .args(args)
        .output()
        .expect("run frob")
}

fn code(o: &std::process::Output) -> i32 {
    o.status.code().expect("exit code")
}

fn tree() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let marker = ["TO", "DO"].concat();
    std::fs::write(dir.path().join("lib.rs"), format!("// {marker}: later\n")).expect("write");
    dir
}

#[test]
fn error_finding_exits_1_and_fail_on_none_exits_0() {
    let dir = tree();
    let failing = frob(dir.path(), &["check", "--json"]);
    assert_eq!(code(&failing), 1);
    assert!(String::from_utf8_lossy(&failing.stdout).contains("TODO001"));
    let ok = frob(
        dir.path(),
        &["check", "--json", "--fail-on", "none", "--timing"],
    );
    assert_eq!(code(&ok), 0);
    let v: Value = serde_json::from_slice(&ok.stdout).expect("json");
    assert_eq!(v["data"]["counts"]["error"], 1);
    assert!(v["data"]["timing"]["stages"].is_array());
    assert_eq!(v["data"]["findings"][0]["rule"], "TODO001");
}

#[test]
fn explain_prints_the_rule_page_and_unknown_is_usage() {
    let dir = tree();
    let ok = frob(dir.path(), &["check", "--json", "--explain", "TODO001"]);
    assert_eq!(code(&ok), 0);
    let v: Value = serde_json::from_slice(&ok.stdout).expect("json");
    assert_eq!(v["data"]["explain"]["id"], "TODO001");
    assert_eq!(
        code(&frob(dir.path(), &["check", "--explain", "NOPE999"])),
        2
    );
    assert_eq!(code(&frob(dir.path(), &["check", "--only", "NOPE"])), 2);
}
