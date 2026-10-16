//! `work --unplanned` and `--reason` parsing: a usage error before any ticket is touched.
// frob:ticket 01M4D6NSXSZXY4G6282RSHJV4M

use crate::common;

use std::path::Path;
use std::process::Output;

fn frob(cwd: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn error_code(out: &Output) -> String {
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).expect("json stdout");
    v["error"]["code"].as_str().unwrap_or_default().to_owned()
}

fn initialised() -> tempfile::TempDir {
    let dir = common::git_repo();
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    dir
}

// frob:tests crates/frob-worktree/src/verbs.rs::flag_reasons
#[test]
fn unplanned_without_a_reason_is_a_usage_error() {
    let dir = initialised();
    let out = frob(dir.path(), &["work", "~ABCDEFG", "--unplanned"]);
    assert_eq!(
        out.status.code(),
        Some(2),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    assert_eq!(error_code(&out), "E-USAGE");
}

// frob:tests crates/frob-worktree/src/verbs.rs::flag_reasons
#[test]
fn unplanned_with_a_blank_reason_is_a_usage_error() {
    let dir = initialised();
    let out = frob(
        dir.path(),
        &["work", "~ABCDEFG", "--unplanned", "--reason", "  "],
    );
    assert_eq!(
        out.status.code(),
        Some(2),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
}

// frob:tests crates/frob-worktree/src/verbs.rs::flag_reasons
#[test]
fn a_reason_alone_is_a_usage_error() {
    let dir = initialised();
    let out = frob(dir.path(), &["work", "~ABCDEFG", "--reason", "why"]);
    assert_eq!(
        out.status.code(),
        Some(2),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
}
