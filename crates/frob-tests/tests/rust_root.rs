//! Nextest runs from the Cargo workspace that owns the selected tests, and a failed runner explains itself (~ZWTT8J3).

// frob:ticket 01M4CTTRCCJMVJDYVEJZWTT8J3

use std::path::Path;
use std::time::Duration;

use frob_tests::{
    Framework, RunOptions, build_repo_graph, failure_cause, run, select_tests, touched_set,
};
use gob_exec::{Limits, Runner};
use gob_git::Repo;

mod common;
use common::{git, write};

/// The manifest of a one-crate workspace named `name` (unique per test: tests share one cargo target dir).
fn manifest(name: &str) -> String {
    format!(
        "[package]\nname = \"{name}\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[workspace]\n"
    )
}
const LIB: &str = "pub fn double(n: i32) -> i32 {\n    n * 2\n}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn doubles() {\n        assert_eq!(super::double(2), 4);\n    }\n}\n";

/// A repository with a crate under `rs/` and no root `Cargo.toml`; returns the dir and the base commit.
fn nested_repo(name: &str) -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    write(p, "rs/Cargo.toml", &manifest(name));
    write(p, "rs/src/lib.rs", LIB);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let base = git(p, &["rev-parse", "HEAD"]);
    (dir, base)
}

fn run_selected(dir: &Path, base: &str) -> frob_tests::RunReport {
    let repo = Repo::discover(dir).expect("repo");
    let graph = build_repo_graph(dir).expect("graph");
    let touched = touched_set(&repo, &graph, base).expect("touched");
    let selected = select_tests(dir, &graph, &touched);
    assert!(
        selected.iter().any(|t| t.framework == Framework::Nextest),
        "a nextest test is selected: {selected:?}"
    );
    let opts = RunOptions::new(
        dir.to_path_buf(),
        Duration::from_secs(300),
        String::new(),
        Vec::new(),
        false,
    );
    run(&Runner::new(Limits { jobs: 1 }), &selected, &opts).expect("run")
}

#[test]
fn a_crate_under_a_subdirectory_runs_nextest_from_that_directory() {
    // frob:tests crates/frob-tests/src/run.rs::run
    let (dir, base) = nested_repo("frob_rust_root_ok");
    write(dir.path(), "rs/src/lib.rs", &LIB.replace("n * 2", "n + n"));
    let report = run_selected(dir.path(), &base);
    assert!(report.passed(), "{}", failure_cause(&report));
    assert_eq!(report.runs.len(), 1);
    assert_eq!(report.runs[0].member, "rs");
    assert_eq!(report.executed(), ["tests::doubles"]);
}

#[test]
fn a_runner_that_fails_before_running_tests_shows_its_stderr_tail_and_exit_code() {
    // frob:tests crates/frob-tests/src/run.rs::failure_cause
    let (dir, base) = nested_repo("frob_rust_root_broken");
    write(
        dir.path(),
        "rs/src/lib.rs",
        &LIB.replace("n * 2", "{ let _x: u8 = \"no\"; n }"),
    );
    let report = run_selected(dir.path(), &base);
    assert!(!report.passed(), "{report:?}");
    assert!(report.executed().is_empty());
    let cause = failure_cause(&report);
    assert!(cause.contains("exit code 101"), "{cause}");
    assert!(cause.contains("mismatched types"), "{cause}");
}
