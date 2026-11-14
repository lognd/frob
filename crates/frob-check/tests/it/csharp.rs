//! The .NET solution and Unity fixtures through `frob check` end to end: no panic, C# files examined, expected findings.

// frob:ticket 01M44YQVN6PMK0D8NJ801ENJEW

use std::path::Path;

use frob_check::{CheckOptions, run};
use gob_rules::{Finding, Severity};

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

/// Copies the fixture tree `from` into `to`, file by file.
fn copy_tree(from: &Path, to: &Path) {
    gob_fs::copy_tree(from, to).expect("copy tree");
}

/// A temp repo holding one gob-symbols C# fixture.
fn fixture(name: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let src = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../gob-symbols/tests/corpus/csharp")
        .join(name);
    copy_tree(&src, dir.path());
    dir
}

fn of<'a>(findings: &'a [Finding], rule: &str) -> Vec<&'a Finding> {
    findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .collect()
}

/// The messages of every finding of `rule` at `severity`.
fn messages(findings: &[Finding], rule: &str, severity: Severity) -> Vec<String> {
    of(findings, rule)
        .into_iter()
        .filter(|f| f.severity == severity)
        .map(|f| f.message.clone())
        .collect()
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn the_dotnet_solution_runs_end_to_end_with_the_expected_cov001_findings() {
    let dir = fixture("solution");
    let report = run(dir.path(), &options()).expect("run");
    // The C# adapter is F1 (no resolved references), so an unreached public
    // callable is Unresolved, never a certified Error.
    let errors = messages(&report.findings, "COV001", Severity::Error);
    assert!(errors.is_empty(), "F1 never certifies a miss: {errors:?}");
    let warn = messages(&report.findings, "COV001", Severity::Unresolved);
    assert!(warn.iter().any(|m| m.contains("Program.Main")), "{warn:?}");
    assert!(
        warn.iter().any(|m| m.contains("Platform.Label")),
        "{warn:?}"
    );
    for reached in ["Widget.Describe", "StringExtensions.Shout"] {
        assert!(
            !warn.iter().any(|m| m.contains(reached)),
            "{reached} is reached by a test: {warn:?}"
        );
    }
    // The #if-guarded `Platform.Label` is still reported (Unresolved above), never a silent pass.
}

// frob:tests crates/frob-obligations/src/doc.rs::doc001
#[test]
fn the_dotnet_solution_documented_types_pass_doc001_and_namespaces_are_skipped() {
    let dir = fixture("solution");
    let report = run(dir.path(), &options()).expect("run");
    let warn = messages(&report.findings, "DOC001", Severity::Error);
    assert!(
        warn.is_empty(),
        "every documented type and member is satisfied by its XML doc comment, and namespaces are skipped: {warn:?}"
    );
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn the_unity_fixture_runs_end_to_end_and_the_unity_test_reaches_the_behaviour() {
    let dir = fixture("unity");
    let report = run(dir.path(), &options()).expect("run");
    let warn = messages(&report.findings, "COV001", Severity::Error);
    assert!(warn.is_empty(), "UnityTest reaches Travelled: {warn:?}");
    let unresolved = messages(&report.findings, "AFFECT001", Severity::Unresolved);
    assert!(
        unresolved.iter().any(|m| m.contains("asmdef")),
        "the asmdef files are opaque and reported as such: {unresolved:?}"
    );
}
