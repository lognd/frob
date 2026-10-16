//! A walked file the gates cannot read is a required Unresolved finding, never silence (READ001).

use std::path::Path;

use frob_check::{CheckOptions, run};
use gob_diagnostics::ExitCode;
use gob_rules::{Finding, RequiredReason, Severity};

fn write(root: &Path, path: &str, bytes: &[u8]) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, bytes).expect("write");
}

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

fn read001(findings: &[Finding]) -> Vec<&Finding> {
    findings
        .iter()
        .filter(|f| f.rule.as_str() == "READ001")
        .collect()
}

fn clean_repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "README.md", b"# Title\n\nText.\n");
    dir
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
// frob:tests crates/gob-check/src/pipeline.rs::unreadable_findings
#[test]
fn a_non_utf8_markdown_file_is_a_required_unresolved_that_fails_the_gate() {
    let clean = clean_repo();
    let without = run(clean.path(), &options()).expect("run");
    assert!(read001(&without.findings).is_empty());
    assert_eq!(without.fidelity.skipped.files, 0);

    write(
        clean.path(),
        "docs/bad.md",
        &[b'#', b' ', 0xff, 0xfe, b'\n'],
    );
    let with = run(clean.path(), &options()).expect("run");
    let found = read001(&with.findings);
    assert_eq!(found.len(), 1, "{found:?}");
    let f = found[0];
    assert_eq!(f.severity, Severity::Unresolved);
    assert!(f.message.contains("docs/bad.md"), "{}", f.message);
    assert!(f.message.contains("encoding"), "{}", f.message);
    assert!(
        f.message.contains("utf-8"),
        "decode error named: {}",
        f.message
    );
    assert!(matches!(
        f.required,
        Some(RequiredReason::ZeroSubjects { .. })
    ));
    assert_eq!(with.exit_code(), ExitCode::Negative, "default gate fails");
    assert_ne!(
        serde_json::to_string(&without.fidelity).expect("json"),
        serde_json::to_string(&with.fidelity).expect("json"),
        "the report differs with the file"
    );
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
// frob:tests crates/gob-check/src/status.rs::FidelityReport.add_skipped
#[test]
fn fidelity_counts_skipped_files_by_reason() {
    let dir = clean_repo();
    write(dir.path(), "frob.toml", b"[check]\nsize_cap = 64\n");
    write(dir.path(), "bad.md", &[0xff, 0xfe, b'\n']);
    write(dir.path(), "big.txt", &[b'x'; 200]);
    write(dir.path(), "logo.png", &[0u8; 200]);
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(
        report.fidelity.skipped.files, 2,
        "{:?}",
        report.fidelity.skipped
    );
    assert_eq!(report.fidelity.skipped.reasons.get("encoding"), Some(&1));
    assert_eq!(report.fidelity.skipped.reasons.get("size"), Some(&1));
    let paths: Vec<&str> = read001(&report.findings)
        .iter()
        .map(|f| f.message.as_str())
        .collect();
    assert!(
        paths
            .iter()
            .any(|m| m.contains("big.txt") && m.contains("size_cap"))
    );
    assert!(
        !paths.iter().any(|m| m.contains("logo.png")),
        "a declared-binary oversized file is not reported: {paths:?}"
    );
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
// frob:tests crates/gob-check/src/core.rs::walk_core
#[test]
fn an_excluded_file_is_never_read_or_reported() {
    let dir = clean_repo();
    write(
        dir.path(),
        "frob.toml",
        b"[check]\nexclude = [\"vendor/\"]\n",
    );
    write(dir.path(), "vendor/bad.md", &[0xff, 0xfe, b'\n']);
    let report = run(dir.path(), &options()).expect("run");
    assert!(read001(&report.findings).is_empty());
    assert_eq!(report.fidelity.skipped.files, 0);
    assert_eq!(report.exit_code(), ExitCode::Ok);
}
