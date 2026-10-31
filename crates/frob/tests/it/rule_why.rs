//! `frob rule why ID FILE:LINE` end to end: the trace text prints and the verb exits 0.

// frob:ticket 01M4PT1A52YR3QV6PYSGNC7N38

use gob_cli::run_for_test;

const RULE: &str = r#"rule NOPE001 "danger-call" {
  lang rust
  severity error
  find c: call where c.callee == "danger"
  report c "danger on line {c.line}"
  explain """
    Danger bites.

    ## Remedy
    Call something safe.
  """
}
"#;

// frob:tests crates/frob/src/rule_cmd.rs::RuleWhy
#[test]
fn rule_why_prints_the_trace_for_a_location_and_exits_zero() {
    let dir = tempfile::tempdir().unwrap();
    let init = std::process::Command::new("git")
        .args(["init", "-q"])
        .current_dir(dir.path())
        .status()
        .unwrap();
    assert!(init.success());
    let (code, out, err) = run_for_test(&frob_cli::cli(), &["init"], dir.path());
    assert_eq!(code, 0, "{out}{err}");
    std::fs::create_dir_all(dir.path().join("rules")).unwrap();
    std::fs::write(dir.path().join("rules/NOPE001.grl"), RULE).unwrap();
    std::fs::write(dir.path().join("a.rs"), "fn b() {\n    danger();\n}\n").unwrap();
    let cli = frob_cli::cli();
    let (code, out, err) = run_for_test(
        &cli,
        &["rule", "why", "NOPE001", "a.rs:2", "--text"],
        dir.path(),
    );
    assert_eq!(code, 0, "{out}{err}");
    assert!(out.contains("NOPE001 polarity"), "{out}");
    assert!(out.contains("1 candidate at 2:"), "{out}");
}
