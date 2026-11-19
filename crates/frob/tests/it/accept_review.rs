//! `frob accept-review` through the real verb: self-review is refused, a second identity is recorded.
// frob:ticket 01M6BNZX417F7NT1CGXR8NFWKA

use crate::common;

fn git(dir: &std::path::Path, args: &[&str]) {
    let s = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(s.success(), "git {args:?}");
}

fn repo_with_accept() -> tempfile::TempDir {
    let dir = common::git_repo();
    std::fs::write(dir.path().join("frob.toml"), "").unwrap();
    std::fs::write(
        dir.path().join("a.rs"),
        "// frob:accept DOC001 reason\nfn a() {}\n",
    )
    .unwrap();
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "add accept"]);
    dir
}

// frob:tests crates/frob/src/accept_review_cmd.rs::AcceptReview
#[test]
fn the_author_cannot_review_their_own_accept() {
    let dir = repo_with_accept();
    let (code, stdout, stderr) = gob_cli::run_for_test(
        &frob_cli::cli(),
        &["accept-review", "DOC001", "a.rs"],
        dir.path(),
    );
    assert_ne!(code, 0, "{stdout}{stderr}");
    assert!(
        format!("{stdout}{stderr}").contains("E-ACCEPT-SELF-REVIEW"),
        "{stdout}{stderr}"
    );
    assert!(!dir.path().join("frob.lock").exists());
}

// frob:tests crates/frob/src/accept_review_cmd.rs::AcceptReview
#[test]
fn a_second_identity_records_a_review_in_the_lock() {
    let dir = repo_with_accept();
    git(dir.path(), &["config", "user.name", "Reviewer"]);
    git(dir.path(), &["config", "user.email", "rev@example.com"]);
    let (code, stdout, stderr) = gob_cli::run_for_test(
        &frob_cli::cli(),
        &["accept-review", "DOC001", "a.rs", "--note", "fine"],
        dir.path(),
    );
    assert_eq!(code, 0, "{stdout}{stderr}");
    let lock = std::fs::read_to_string(dir.path().join("frob.lock")).unwrap();
    assert!(lock.contains("accept:a.rs:DOC001"), "{lock}");
    assert!(lock.contains("rev@example.com"), "{lock}");
}
