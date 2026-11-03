//! Small public surface of the reader: shared runner, commit ranges and error codes.

use std::path::Path;
use std::sync::Arc;

use gob_exec::{Limits, Runner};
use gob_git::{GitError, Repo};

fn git(dir: &Path, args: &[&str]) {
    let status = std::process::Command::new("git")
        .args(["-c", "user.name=t", "-c", "user.email=t@example.com"])
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git runs");
    assert!(status.success(), "git {args:?}");
}

// frob:tests crates/gob-git/src/read.rs::Repo.with_runner
#[test]
fn a_repo_uses_the_runner_it_was_given() {
    let dir = tempfile::tempdir().unwrap();
    let runner = Arc::new(Runner::new(Limits { jobs: 1 }));
    let repo = Repo::init(dir.path()).unwrap().with_runner(runner.clone());
    assert!(std::ptr::eq(repo.runner(), Arc::as_ptr(&runner)));
}

// frob:tests crates/gob-git/src/read.rs::Repo.commits_not_in
#[test]
fn commits_not_in_lists_the_tip_only_commits_newest_first() {
    let dir = tempfile::tempdir().unwrap();
    git(dir.path(), &["init", "-q", "-b", "main"]);
    git(dir.path(), &["commit", "-q", "--allow-empty", "-m", "base"]);
    git(dir.path(), &["checkout", "-q", "-b", "topic"]);
    git(dir.path(), &["commit", "-q", "--allow-empty", "-m", "one"]);
    git(dir.path(), &["commit", "-q", "--allow-empty", "-m", "two"]);
    let repo = Repo::discover(dir.path()).unwrap();
    let subjects: Vec<String> = repo
        .commits_not_in("topic", "main", 10)
        .unwrap()
        .into_iter()
        .map(|(_, s)| s)
        .collect();
    assert_eq!(subjects, ["two", "one"]);
    assert_eq!(repo.commits_not_in("topic", "main", 1).unwrap().len(), 1);
    assert!(repo.commits_not_in("nope", "main", 1).is_err());
}

// frob:tests crates/gob-git/src/error.rs::GitError.code
#[test]
fn every_error_has_a_stable_code() {
    assert_eq!(GitError::NoIdentity.code(), "E-GIT-IDENTITY");
}
