//! `frob init` pins the ledger to LF checkouts when `core.autocrlf=true`.
// frob:ticket 01M4FD43P9VMJC9BE0KGEKVBBH

use std::path::Path;

use serde_json::Value;

use crate::common;

const PIN: &str = "tickets/** text eol=lf";

fn set_autocrlf(dir: &Path, value: &str) {
    let status = std::process::Command::new("git")
        .args(["config", "core.autocrlf", value])
        .current_dir(dir)
        .status()
        .expect("git config");
    assert!(status.success(), "git config core.autocrlf");
}

fn init(dir: &Path, extra: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .arg("init")
        .args(extra)
        .output()
        .expect("run frob");
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    serde_json::from_slice(&out.stdout).expect("json envelope")
}

fn attrs(dir: &Path) -> String {
    std::fs::read_to_string(dir.join(".gitattributes")).unwrap_or_default()
}

// frob:tests crates/frob/src/init.rs::ensure_gitattributes
#[test]
fn autocrlf_true_writes_the_lf_pin_and_the_report_says_so() {
    let dir = common::git_repo();
    set_autocrlf(dir.path(), "true");
    let env = init(dir.path(), &[]);
    let attrs = attrs(dir.path());
    assert_eq!(attrs.lines().filter(|l| *l == PIN).count(), 1, "{attrs}");
    assert_eq!(env["data"]["eol_pin"]["target"], PIN);
    assert_eq!(env["data"]["eol_pin"]["changed"], true);
    assert_eq!(env["data"]["gitattributes"]["changed"], true);
}

// frob:tests crates/frob/src/init.rs::ensure_gitattributes
#[test]
fn a_second_init_leaves_the_pin_alone_and_reports_no_change() {
    let dir = common::git_repo();
    set_autocrlf(dir.path(), "true");
    init(dir.path(), &[]);
    let before = attrs(dir.path());
    let again = init(dir.path(), &[]);
    assert_eq!(attrs(dir.path()), before);
    assert_eq!(again["data"]["eol_pin"]["changed"], false);
    assert_eq!(again["already"], true);
}

// frob:tests crates/frob/src/init.rs::ensure_gitattributes
#[test]
fn an_existing_gitattributes_keeps_its_lines_and_gains_the_pin_once() {
    let dir = common::git_repo();
    set_autocrlf(dir.path(), "true");
    std::fs::write(dir.path().join(".gitattributes"), "*.png binary").expect("seed");
    init(dir.path(), &[]);
    let text = attrs(dir.path());
    assert!(text.starts_with("*.png binary\n"), "{text}");
    assert_eq!(text.matches(PIN).count(), 1, "{text}");
    // A pin written with different spacing already counts.
    let spaced = text.replace(PIN, "tickets/**   text   eol=lf");
    std::fs::write(dir.path().join(".gitattributes"), &spaced).expect("write");
    let again = init(dir.path(), &[]);
    assert_eq!(again["data"]["eol_pin"]["changed"], false);
    assert_eq!(attrs(dir.path()), spaced);
}

// frob:tests crates/frob/src/init.rs::ensure_gitattributes
#[test]
fn autocrlf_input_or_unset_writes_no_pin() {
    for value in [Some("input"), Some("false"), None] {
        let dir = common::git_repo();
        if let Some(v) = value {
            set_autocrlf(dir.path(), v);
        }
        let env = init(dir.path(), &[]);
        assert!(!attrs(dir.path()).contains("eol=lf"), "{value:?}");
        assert_eq!(env["data"]["eol_pin"], Value::Null, "{value:?}");
    }
}

// frob:tests crates/frob/src/init.rs::ensure_gitattributes
#[test]
fn dry_run_reports_the_pin_without_writing_it() {
    let dir = common::git_repo();
    set_autocrlf(dir.path(), "true");
    let env = init(dir.path(), &["--dry-run"]);
    assert_eq!(env["data"]["eol_pin"]["changed"], true);
    assert!(!dir.path().join(".gitattributes").exists());
}
