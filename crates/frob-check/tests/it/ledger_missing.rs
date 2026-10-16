//! A configured ledger ref absent from a repository with commits is one required finding, never zero-subject ledger rules.

use std::path::Path;

use frob_check::{CheckOptions, run};
use gob_diagnostics::ExitCode;

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

/// A committed repository on `main` whose `frob.toml` points the ledger at `refs/heads/ledger`, which does not exist.
fn fixture(configured: bool) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    git(root, &["init", "-q", "-b", "main"]);
    let toml = if configured {
        "[tickets]\nref = \"refs/heads/ledger\"\nref_mode = \"trunk\"\n"
    } else {
        ""
    };
    std::fs::write(root.join("frob.toml"), toml).expect("write");
    std::fs::create_dir_all(root.join("src")).expect("mkdir");
    std::fs::write(
        root.join("src/lib.rs"),
        "// frob:ticket 01M4069Z0HH5RV8TNPFVA936C5\npub const X: u8 = 1;\n",
    )
    .expect("write");
    git(root, &["add", "-A"]);
    git(root, &["commit", "-q", "-m", "init"]);
    dir
}

// frob:ticket 01M44VQ57WQW4G5JTZDDYEVJPW
// frob:tests crates/frob-check/src/snapshot.rs::open_ledger
#[test]
fn an_absent_ledger_ref_is_one_required_finding_naming_the_ref_and_a_remedy() {
    let dir = fixture(true);
    let r = run(dir.path(), &options()).expect("run");
    let required: Vec<_> = r.findings.iter().filter(|f| f.required.is_some()).collect();
    assert_eq!(required.len(), 1, "{required:?}");
    let msg = &required[0].message;
    assert!(msg.contains("refs/heads/ledger"), "{msg}");
    assert!(msg.contains("git fetch"), "{msg}");
    assert!(
        !r.findings
            .iter()
            .any(|f| f.message.contains("examined zero subjects")),
        "{:?}",
        r.findings
    );
    assert_eq!(r.exit_code(), ExitCode::Negative);
}

// frob:ticket 01M44VQ57WQW4G5JTZDDYEVJPW
// frob:tests crates/frob-check/src/snapshot.rs::open_ledger
#[test]
fn without_a_tickets_table_a_missing_ledger_ref_stays_silent() {
    let dir = fixture(false);
    let r = run(dir.path(), &options()).expect("run");
    assert!(
        !r.findings.iter().any(|f| f.message.contains("ledger ref")),
        "{:?}",
        r.findings
    );
}
