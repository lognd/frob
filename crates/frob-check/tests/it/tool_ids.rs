//! The evidence-ranked external linters through `frob check`, end to end: recorded tool output in, frob ids with the tool's own id kept out.

use std::path::Path;

use frob_check::{CheckOptions, CheckReport, run};
use gob_diagnostics::ExitCode;
use gob_rules::Severity;

const CLIPPY: &str = include_str!("../../../gob-check/tests/fixtures/cargo-clippy.jsonl");
const RUFF: &str = include_str!("../../../gob-check/tests/fixtures/ruff.json");
const ESLINT: &str = include_str!("../../../gob-check/tests/fixtures/eslint.json");
const ROSLYN: &str = include_str!("../../../gob-check/tests/fixtures/sarif-roslyn-unity.json");

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: false,
        only: [
            "TOOL", "LINT", "DEAD", "ERR", "CONC", "TYPING", "A11Y", "REACT", "UNITY", "SPELL",
            "LOGIC", "NEAT", "TESTQ",
        ]
        .map(str::to_owned)
        .to_vec(),
        ..CheckOptions::default()
    }
}

/// A stage `name` that prints the recorded `output` through `sh` and exits 0.
fn stage(root: &Path, name: &str, parser: &str, output: &str) -> String {
    write(root, &format!("{name}.out"), output);
    write(root, &format!("{name}.sh"), &format!("cat {name}.out\n"));
    format!(
        "[[check.tool]]\nname = \"{name}\"\ncommand = \"sh\"\nargs = [\"{name}.sh\"]\nparser = \"{parser}\"\nversion_args = [\"-c\", \"echo {name} 1.0.0\"]\n\n"
    )
}

/// The `(rule, severity)` of every finding whose message starts `stage/tool_id:`.
fn mapped(report: &CheckReport, stage: &str, tool_id: &str) -> Vec<(String, Severity)> {
    let prefix = format!("{stage}/{tool_id}: ");
    report
        .findings
        .iter()
        .filter(|f| f.message.starts_with(&prefix))
        .map(|f| (f.rule.to_string(), f.severity))
        .collect()
}

fn one(report: &CheckReport, stage: &str, tool_id: &str) -> String {
    let found = mapped(report, stage, tool_id);
    assert_eq!(found.len(), 1, "{stage}/{tool_id}: {found:?}");
    found[0].0.clone()
}

// frob:ticket 01M4D8X558Q07HCMEBP224NQP4
// frob:tests crates/gob-check/src/tool_parse.rs::parse
// frob:tests crates/gob-check/src/tool_parse.rs::classify
#[test]
fn clippy_ruff_eslint_roslyn_and_typos_arrive_under_frob_ids_and_unreadable_output_is_required() {
    if !gob_exec::require_sh(
        "clippy_ruff_eslint_roslyn_and_typos_arrive_under_frob_ids_and_unreadable_output_is_required",
    ) {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    // Recorded output carries `/work/` absolute paths; rebase it onto the temp repo.
    let rebase = |text: &str| text.replace("file:///work/", "").replace("/work/", "");
    // Built at runtime so the repository's own typos stage does not flag the fixture.
    let bad = ["te", "h"].concat();
    let typos = format!(
        "{{\"type\":\"typo\",\"path\":\"README.md\",\"line_num\":1,\"byte_offset\":0,\"typo\":\"{bad}\",\"corrections\":[\"the\"]}}\n"
    );
    let mut toml = String::new();
    toml.push_str(&stage(root, "clippy", "cargo-json", CLIPPY));
    toml.push_str(&stage(root, "ruff", "ruff-json", &rebase(RUFF)));
    toml.push_str(&stage(root, "eslint", "eslint-json", &rebase(ESLINT)));
    toml.push_str(&stage(root, "roslyn", "roslyn-sarif", &rebase(ROSLYN)));
    toml.push_str(&stage(root, "typos", "typos-json", &typos));
    toml.push_str(&stage(root, "broken", "eslint-json", "not json"));
    write(root, "frob.toml", &toml);

    let report = run(root, &options()).expect("run");

    // Rust: rustc and clippy lints.
    assert_eq!(
        one(&report, "clippy", "clippy::too_many_arguments"),
        "NEAT002"
    );
    assert_eq!(
        one(&report, "clippy", "clippy::absurd_extreme_comparisons"),
        "LOGIC001"
    );
    assert_eq!(one(&report, "clippy", "clippy::needless_return"), "LINT001");
    // Python: ruff.
    assert_eq!(one(&report, "ruff", "F401"), "DEAD001");
    assert_eq!(one(&report, "ruff", "E722"), "ERR003");
    assert_eq!(one(&report, "ruff", "S110"), "ERR001");
    assert_eq!(one(&report, "ruff", "ASYNC110"), "CONC001");
    assert_eq!(one(&report, "ruff", "PT011"), "TESTQ001");
    assert!(
        mapped(&report, "ruff", "PLR2004").is_empty(),
        "off by default"
    );
    // TypeScript: the ESLint family.
    assert_eq!(one(&report, "eslint", "jsx-a11y/alt-text"), "A11Y001");
    assert_eq!(
        one(&report, "eslint", "react-hooks/exhaustive-deps"),
        "REACT001"
    );
    assert_eq!(
        one(&report, "eslint", "@typescript-eslint/no-floating-promises"),
        "CONC001"
    );
    assert_eq!(
        one(&report, "eslint", "@typescript-eslint/no-explicit-any"),
        "TYPING001"
    );
    assert_eq!(one(&report, "eslint", "no-console"), "LINT001");
    // Unity: Roslyn and Microsoft.Unity.Analyzers.
    assert_eq!(one(&report, "roslyn", "UNT0008"), "UNITY101");
    assert_eq!(one(&report, "roslyn", "VSTHRD100"), "CONC001");
    assert_eq!(one(&report, "roslyn", "CA1822"), "LINT001");
    // typos.
    assert_eq!(one(&report, "typos", "typo"), "SPELL001");

    // Unreadable tool output is a required TOOL001 that fails the gate.
    let tool001: Vec<_> = report
        .findings
        .iter()
        .filter(|f| f.rule.to_string() == "TOOL001")
        .collect();
    assert_eq!(tool001.len(), 1, "{tool001:?}");
    assert!(tool001[0].required.is_some());
    assert_eq!(report.exit_code(), ExitCode::Negative);
}
