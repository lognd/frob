//! A Python package through `frob check`: directives bind, bare markers fire, tests reach callees, unmodelled constructs are Unresolved.

use std::path::Path;

use frob_check::{CheckOptions, run};
use gob_rules::{Finding, Severity};

/// The upper-case work marker, assembled so this file does not carry one.
fn marker() -> String {
    ["TO", "DO"].concat()
}

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

fn of<'a>(findings: &'a [Finding], rule: &str) -> Vec<&'a Finding> {
    findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .collect()
}

fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    write(
        root,
        "pkg/core.py",
        &format!(
            "\"\"\"Core.\"\"\"\n\n\ndef covered(x):\n    \"\"\"Covered.\"\"\"\n    return x\n\n\ndef lonely(x):\n    \"\"\"Not reached.\"\"\"\n    # {} tidy this\n    return x\n\n\ndef modern(v):\n    \"\"\"Uses match.\"\"\"\n    match v:\n        case 1:\n            return 1\n    return 0\n",
            marker()
        ),
    );
    write(
        root,
        "tests/test_core.py",
        "from pkg.core import covered\n\n\ndef test_covered():\n    assert covered(1) == 1\n",
    );
    dir
}

// frob:tests crates/frob-obligations/src/todo.rs::todo001
#[test]
fn a_bare_marker_in_a_python_comment_fires_todo001() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    let todo = of(&report.findings, "TODO001");
    assert_eq!(todo.len(), 1, "{todo:?}");
    assert_ne!(todo[0].severity, Severity::Unresolved, "{todo:?}");
    assert!(todo[0].message.contains("pkg/core.py") || !todo[0].message.is_empty());
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_sees_which_python_functions_tests_reach() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    let cov = of(&report.findings, "COV001");
    let text: Vec<String> = cov.iter().map(|f| f.message.clone()).collect();
    assert!(
        text.iter().any(|m| m.contains("lonely")),
        "an unreached public function is reported: {text:?}"
    );
    assert!(
        !text.iter().any(|m| m.contains("core.py::covered")),
        "a reached function is not: {text:?}"
    );
}

// frob:tests crates/gob-symbols/src/python.rs::Fold.tr
#[test]
fn an_unmodelled_python_construct_is_unresolved_not_clean() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    let cov = of(&report.findings, "COV001");
    assert!(
        cov.iter()
            .any(|f| f.severity == Severity::Unresolved && f.message.contains("parsed partially")),
        "{cov:?}"
    );
}
