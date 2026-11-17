//! BASE001 and BASE002 run in `frob check`: the head baseline against the `[check] base` file and the ledger.

use std::path::Path;

use frob_check::{CheckOptions, run};

const KEY_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const KEY_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

fn git(root: &Path, args: &[&str]) {
    let out = std::process::Command::new("git")
        .current_dir(root)
        .args(["-c", "user.name=T", "-c", "user.email=t@example.com"])
        .args(args)
        .output()
        .expect("git runs");
    assert!(out.status.success(), "git {args:?}: {out:?}");
}

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

fn baseline(keys: &[&str]) -> String {
    let list: Vec<String> = keys.iter().map(|k| format!("\"{k}\"")).collect();
    format!(
        "version = 1\n\n[rules.DOC001]\nreason = \"burn down\"\nticket = \"~NOPE\"\nfindings = [{}]\n",
        list.join(", ")
    )
}

/// A repository on `main` whose committed baseline lists `committed` (when any) and whose working tree lists `working`.
fn fixture(committed: Option<&[&str]>, working: &[&str]) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    git(root, &["init", "-q", "-b", "main"]);
    std::fs::write(root.join("frob.toml"), "").expect("write");
    if let Some(keys) = committed {
        std::fs::write(root.join("frob-baseline.toml"), baseline(keys)).expect("write");
    }
    git(root, &["add", "-A"]);
    git(root, &["commit", "-q", "-m", "init"]);
    std::fs::write(root.join("frob-baseline.toml"), baseline(working)).expect("write");
    dir
}

fn fired(dir: &tempfile::TempDir, rule: &str) -> usize {
    let report = run(dir.path(), &options()).expect("run");
    report
        .findings
        .iter()
        .filter(|f| f.rule.to_string() == rule)
        .count()
}

// frob:ticket 01M7KME88Y8N7JD506Y0WRG2MX
// frob:tests crates/frob-check/src/host.rs::FrobInputs
#[test]
fn base001_fires_when_the_working_baseline_grew_against_the_base_ref() {
    let dir = fixture(Some(&[KEY_A]), &[KEY_A, KEY_B]);
    assert_eq!(fired(&dir, "BASE001"), 1);
}

// frob:ticket 01M7KME88Y8N7JD506Y0WRG2MX
// frob:tests crates/frob-check/src/host.rs::FrobInputs
#[test]
fn base001_is_silent_when_the_base_ref_has_no_baseline_file() {
    let dir = fixture(None, &[KEY_A, KEY_B]);
    assert_eq!(fired(&dir, "BASE001"), 0);
}

// frob:ticket 01M7KME88Y8N7JD506Y0WRG2MX
// frob:tests crates/frob-check/src/host.rs::FrobInputs
#[test]
fn base002_reports_a_ticket_missing_from_the_ledger_as_unresolved() {
    let dir = fixture(None, &[KEY_A]);
    assert_eq!(fired(&dir, "BASE002"), 1);
}
