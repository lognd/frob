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
