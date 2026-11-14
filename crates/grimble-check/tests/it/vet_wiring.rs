//! `grimble check` runs `grimble-vet` over the repo's `Cargo.lock` and reports its findings.

// frob:ticket 01M5A63T4BZ3XH842F3RDFJ929

use std::path::Path;

use grimble_check::{CheckOptions, run};

/// A lockfile that locks `dup` at two versions.
const DUPLICATE_LOCK: &str = "version = 4\n\n[[package]]\nname = \"dup\"\nversion = \"1.0.0\"\nsource = \"registry+https://github.com/rust-lang/crates.io-index\"\n\n[[package]]\nname = \"dup\"\nversion = \"2.0.0\"\nsource = \"registry+https://github.com/rust-lang/crates.io-index\"\n";

/// The rule ids a run over `dir` reports.
fn run_ids(dir: &Path) -> Vec<String> {
    let done = run(dir, &CheckOptions::default()).expect("run");
    done.report
        .findings
        .iter()
        .map(|f| f.rule.as_str().to_owned())
        .collect()
}

/// A duplicated lockfile version is reported as VET004, so the VET family is registered and run.
// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/product.rs::vet_report
#[test]
fn check_reports_grimble_vet_findings() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("Cargo.lock"), DUPLICATE_LOCK).expect("write");
    let found = run_ids(dir.path());
    assert!(found.iter().any(|r| r == "VET004"), "got {found:?}");
}

/// A repo without a lockfile reports no VET finding.
// frob:tests crates/grimble-check/src/lib.rs::run
#[test]
fn check_without_lockfile_reports_no_vet() {
    let dir = tempfile::tempdir().expect("tempdir");
    assert!(run_ids(dir.path()).iter().all(|r| !r.starts_with("VET")));
}

/// Run a git command in `dir`, panicking on failure.
fn git(dir: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args([
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
        ])
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

/// With a base ref, a dependency new relative to the base lockfile is reported as VET001.
// frob:tests crates/grimble-check/src/product.rs::vet_report
// frob:tests crates/grimble-check/src/product.rs::base_lock
// frob:tests crates/grimble-check/src/product.rs::Grimble.with_base
#[test]
fn check_with_base_reports_new_direct_dependency() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    std::fs::write(
        root.join("Cargo.toml"),
        "[package]\nname = \"app\"\nversion = \"0.1.0\"\n\n[dependencies]\nnewdep = \"1\"\n",
    )
    .expect("manifest");
    let lock = |extra: &str| {
        format!("version = 4\n\n[[package]]\nname = \"app\"\nversion = \"0.1.0\"\n{extra}")
    };
    std::fs::write(root.join("Cargo.lock"), lock("")).expect("lock");
    git(root, &["init", "-q", "-b", "main"]);
    git(root, &["add", "."]);
    git(root, &["commit", "-q", "-m", "base"]);
    let with_dep = lock(
        "dependencies = [\"newdep\"]\n\n[[package]]\nname = \"newdep\"\nversion = \"1.0.0\"\nsource = \"registry+https://github.com/rust-lang/crates.io-index\"\n",
    );
    std::fs::write(root.join("Cargo.lock"), with_dep).expect("lock");
    git(root, &["commit", "-q", "-am", "add dep"]);
    let opts = CheckOptions {
        base: Some("HEAD~1".to_owned()),
        ..CheckOptions::default()
    };
    let done = run(root, &opts).expect("run");
    let found: Vec<&str> = done
        .report
        .findings
        .iter()
        .map(|f| f.rule.as_str())
        .collect();
    assert!(found.contains(&"VET001"), "got {found:?}");
    let plain = run_ids(root);
    assert!(!plain.iter().any(|r| r == "VET001"), "got {plain:?}");
}

/// A root `grimble-vet.toml` allowlist silences VET001 for a new dependency; the legacy file does too.
// frob:ticket 01M73470XDYYF3D5BV77G165PS
// frob:tests crates/grimble-check/src/product.rs::vet_report
#[test]
fn check_honours_root_and_legacy_allowlist() {
    for path in ["grimble-vet.toml", ".grimble/vet.toml"] {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        std::fs::write(
            root.join("Cargo.toml"),
            "[package]\nname = \"app\"\nversion = \"0.1.0\"\n\n[dependencies]\nnewdep = \"1\"\n",
        )
        .expect("manifest");
        let lock = |extra: &str| {
            format!("version = 4\n\n[[package]]\nname = \"app\"\nversion = \"0.1.0\"\n{extra}")
        };
        std::fs::write(root.join("Cargo.lock"), lock("")).expect("lock");
        git(root, &["init", "-q", "-b", "main"]);
        git(root, &["add", "."]);
        git(root, &["commit", "-q", "-m", "base"]);
        std::fs::write(
            root.join("Cargo.lock"),
            lock("dependencies = [\"newdep\"]\n\n[[package]]\nname = \"newdep\"\nversion = \"1.0.0\"\nsource = \"registry+https://github.com/rust-lang/crates.io-index\"\n"),
        )
        .expect("lock");
        std::fs::create_dir_all(root.join(path).parent().expect("parent")).expect("dir");
        std::fs::write(root.join(path), "allow = [\"newdep\"]\n").expect("allow");
        git(root, &["add", "-f", "."]);
        git(root, &["commit", "-q", "-m", "add dep"]);
        let opts = CheckOptions {
            base: Some("HEAD~1".to_owned()),
            ..CheckOptions::default()
        };
        let done = run(root, &opts).expect("run");
        assert!(
            done.report
                .findings
                .iter()
                .all(|f| f.rule.as_str() != "VET001"),
            "{path}: {:?}",
            done.report.findings
        );
    }
}
