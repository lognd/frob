//! Toggling `core.autocrlf` with unchanged content must not change findings or their spans.

use std::path::Path;
use std::process::Command;

use frob_check::{CheckOptions, run};

fn git(root: &Path, args: &[&str]) {
    let out = Command::new("git")
        .args(args)
        .current_dir(root)
        .output()
        .expect("run git");
    assert!(out.status.success(), "git {args:?}: {out:?}");
}

fn findings(root: &Path) -> Vec<String> {
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    let report = run(root, &opts).expect("check runs");
    let mut out: Vec<String> = report.findings.iter().map(|f| format!("{f:?}")).collect();
    out.sort();
    out
}

const LINES: [&str; 5] = [
    "// padding",
    "// padding",
    "// frob:ticket",
    "/// Documented.",
    "pub fn a() {}",
];

/// A committed one-file repository whose worktree uses `eol` line endings under `autocrlf`.
fn repo(eol: &str, autocrlf: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    git(root, &["init", "-q"]);
    git(root, &["config", "user.name", "Test User"]);
    git(root, &["config", "user.email", "test@example.com"]);
    git(root, &["config", "core.autocrlf", autocrlf]);
    std::fs::write(root.join(".gitignore"), ".frob/\n").expect("write");
    std::fs::write(root.join("lib.rs"), LINES.join(eol) + eol).expect("write");
    git(root, &["add", "-A"]);
    git(root, &["commit", "-q", "-m", "init"]);
    dir
}

// frob:ticket 01M40XYVF7485BENTAZ9W1PXF5
// frob:tests crates/frob-obligations/src/lib.rs::evaluate
#[test]
fn toggling_autocrlf_with_unchanged_content_keeps_findings_and_spans_identical() {
    gob_git::install_content_backend();
    let dir = repo("\n", "true");
    let before = findings(dir.path());
    assert!(!before.is_empty(), "the fixture must produce a finding");
    git(dir.path(), &["config", "core.autocrlf", "false"]);
    assert_eq!(before, findings(dir.path()));
}

// frob:ticket 01M40XYVF7485BENTAZ9W1PXF5
// frob:tests crates/frob-obligations/src/lib.rs::evaluate
#[test]
fn a_crlf_worktree_under_autocrlf_reports_the_spans_of_the_normalized_text() {
    gob_git::install_content_backend();
    let lf = repo("\n", "true");
    let crlf = repo("\r\n", "true");
    assert_eq!(findings(lf.path()), findings(crlf.path()));
}
