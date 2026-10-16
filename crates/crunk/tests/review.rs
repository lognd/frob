//! `crunk review`, `crunk ack` and `crunk check --gate release` end to end through the binary.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use std::path::Path;

use assert_cmd::Command;
use serde_json::Value;

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::presets::preset("default")
        .expect("default preset")
        .replace(
            "[lint]",
            "[lint]\nTOKENS001 = \"off\"\nEXPORT001 = \"off\"\nORG001 = \"off\"",
        );
    let spec = format!(
        "{spec}\n[[screen]]\nid = \"home\"\nentry = \"/\"\nreview = \"human\"\n[[screen.states]]\nid = \"default\"\n"
    );
    std::fs::write(dir.path().join("crunk.toml"), spec).expect("write spec");
    std::fs::create_dir_all(dir.path().join("styles")).expect("mkdir");
    std::fs::write(dir.path().join("styles/a.css"), ".a { margin: 0; }\n").expect("css");
    dir
}

/// Run the binary with piped (non-terminal) stdio; returns the exit code and stdout.
fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    let out = Command::cargo_bin("crunk")
        .expect("crunk binary")
        .current_dir(dir)
        .args(args)
        .output()
        .expect("runs");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

// frob:tests crates/crunk/src/review.rs::Ack
#[test]
fn ack_without_a_terminal_and_without_non_interactive_refuses() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["ack", "--all-stale", "--json"]);
    assert_ne!(code, 0, "{out} {err}");
    assert!(
        format!("{out}{err}").contains("E-ACK-NO-TTY"),
        "{out} {err}"
    );
    assert!(
        !dir.path().join("crunk.lock").exists(),
        "nothing was written"
    );
}

// frob:tests crates/crunk/src/review.rs::Ack
#[test]
fn a_non_interactive_ack_is_recorded_and_marked_and_review_then_lists_it_current() {
    let dir = project();
    let (code, out, _) = crunk(dir.path(), &["review", "--json"]);
    assert_eq!(code, 0, "{out}");
    let env: Value = serde_json::from_str(&out).expect("json");
    assert_eq!(env["data"]["pending"], 1, "{out}");
    assert_eq!(env["data"]["subjects"][0]["status"], "missing");

    let (code, out, err) = crunk(
        dir.path(),
        &["ack", "screen/home/default", "--non-interactive", "--json"],
    );
    assert_eq!(code, 0, "{out} {err}");
    let lock = std::fs::read_to_string(dir.path().join("crunk.lock")).expect("lock written");
    assert!(lock.contains("[[review]]"), "{lock}");
    assert!(lock.contains("non_interactive = true"), "{lock}");

    let (_, out, _) = crunk(dir.path(), &["review", "--json"]);
    let env: Value = serde_json::from_str(&out).expect("json");
    assert_eq!(env["data"]["pending"], 0, "{out}");
}

// frob:tests crates/crunk/src/lib.rs::CrunkProduct
#[test]
fn the_release_gate_fails_check_on_a_missing_review_that_the_default_gate_only_advises() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let (code, out, err) = crunk(dir.path(), &["check", "--gate", "release", "--json"]);
    assert_eq!(code, 1, "{out} {err}");
}
