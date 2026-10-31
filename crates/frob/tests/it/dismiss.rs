//! `frob dismiss` through the real verb: it persists a dismissal and rejects a missing or blank reason.
// frob:ticket 01M68K5GXB2C7G082PGAA9C2BY

use crate::common;

// frob:tests crates/frob/src/dismiss_cmd.rs::Dismiss
#[test]
fn a_dismissal_with_a_reason_is_recorded_in_the_precision_history() {
    let dir = common::git_repo();
    std::fs::write(dir.path().join("frob.toml"), "").unwrap();
    let (code, stdout, stderr) = gob_cli::run_for_test(
        &frob_cli::cli(),
        &[
            "dismiss",
            "DOC001",
            "abc123",
            "--reason",
            "false positive in generated code",
        ],
        dir.path(),
    );
    assert_eq!(code, 0, "{stdout}{stderr}");
    assert!(stdout.contains("abc123"), "{stdout}");
    let found = walk(dir.path())
        .into_iter()
        .find(|p| p.file_name().is_some_and(|n| n == "precision-history.json"))
        .expect("history file written");
    let text = std::fs::read_to_string(found).unwrap();
    assert!(
        text.contains("abc123") && text.contains("false positive in generated code"),
        "{text}"
    );
}

// frob:tests crates/frob/src/dismiss_cmd.rs::Dismiss
#[test]
fn a_missing_or_blank_reason_is_rejected_and_nothing_is_written() {
    let dir = common::git_repo();
    std::fs::write(dir.path().join("frob.toml"), "").unwrap();
    for args in [
        &["dismiss", "DOC001", "abc123"][..],
        &["dismiss", "DOC001", "abc123", "--reason", "  "][..],
    ] {
        let (code, stdout, stderr) = gob_cli::run_for_test(&frob_cli::cli(), args, dir.path());
        assert_eq!(code, 2, "{args:?}: {stdout}{stderr}");
    }
    assert!(
        !walk(dir.path())
            .iter()
            .any(|p| p.file_name().is_some_and(|n| n == "precision-history.json"))
    );
}

/// Every file under `root`, skipping `.git`.
fn walk(root: &std::path::Path) -> Vec<std::path::PathBuf> {
    let mut out = Vec::new();
    for entry in std::fs::read_dir(root).unwrap().flatten() {
        let p = entry.path();
        if p.file_name().is_some_and(|n| n == ".git") {
            continue;
        }
        if p.is_dir() {
            out.extend(walk(&p));
        } else {
            out.push(p);
        }
    }
    out
}
