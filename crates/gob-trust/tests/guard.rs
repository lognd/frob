//! Tests for the tracked-state guard (security.md 2.2).

use std::path::Path;
use std::process::Command;

use gob_trust::{GuardError, check_state_untracked};

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
fn git(dir: &Path, args: &[&str]) {
    let st = Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("run git");
    assert!(st.success(), "git {args:?} failed");
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
fn repo() -> tempfile::TempDir {
    let d = tempfile::tempdir().expect("tempdir");
    git(d.path(), &["init", "-q"]);
    d
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
fn write(dir: &Path, rel: &str) {
    let p = dir.join(rel);
    std::fs::create_dir_all(p.parent().expect("parent")).expect("mkdir");
    std::fs::write(p, b"x").expect("write");
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
#[test]
fn tracked_state_files_are_named() {
    let d = repo();
    write(d.path(), ".frob/cache.sqlite");
    write(d.path(), ".grimble/a.json");
    write(d.path(), ".crunk/b/c.json");
    write(d.path(), "src/main.rs");
    git(d.path(), &["add", "-f", "."]);
    match check_state_untracked(d.path()) {
        Err(GuardError::StateTracked { files }) => assert_eq!(
            files,
            vec![".crunk/b/c.json", ".frob/cache.sqlite", ".grimble/a.json"]
        ),
        other => panic!("expected StateTracked, got {other:?}"),
    }
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
#[test]
fn tracked_state_is_found_from_a_subdirectory() {
    let d = repo();
    write(d.path(), ".frob/cache.sqlite");
    write(d.path(), "crates/x/lib.rs");
    git(d.path(), &["add", "-f", "."]);
    match check_state_untracked(&d.path().join("crates/x")) {
        Err(GuardError::StateTracked { files }) => assert_eq!(files, vec![".frob/cache.sqlite"]),
        other => panic!("expected StateTracked, got {other:?}"),
    }
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
#[test]
fn untracked_and_ignored_state_passes() {
    let d = repo();
    write(d.path(), ".frob/cache.sqlite");
    write(d.path(), ".grimble/a.json");
    write(d.path(), ".crunk/b.json");
    write(d.path(), ".gitignore");
    std::fs::write(d.path().join(".gitignore"), ".crunk/\n").expect("ignore");
    write(d.path(), "src/main.rs");
    git(d.path(), &["add", ".gitignore", "src"]);
    assert!(check_state_untracked(d.path()).is_ok());
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
#[test]
fn non_repository_passes() {
    let d = tempfile::tempdir().expect("tempdir");
    write(d.path(), ".frob/cache.sqlite");
    assert!(check_state_untracked(d.path()).is_ok());
}
