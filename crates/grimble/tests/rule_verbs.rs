//! `rule test`, `rule check`, `rule catalog` and `rule fmt` through the grimble command line.

// frob:ticket 01M3ZX7FCFBJSWMTZGCQMW7215

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const RULE: &str = r#"rule NOPE001 "danger-call" {
  lang rust
  severity error
  find c: call where c.callee == "danger"
  report c "danger on line {c.line}"
  example fire rust """
    fn b() {
        danger(); //~ error
    }
  """
  example clean rust """
    fn b() {
        safe();
    }
  """
  explain """
    Danger bites.

    ## Remedy
    Call something safe.
  """
}
"#;

fn grimble(dir: &Path, args: &[&str]) -> (i32, Value, String) {
    let (code, out, err) = run_for_test(&grimble::cli(), args, dir);
    (code, serde_json::from_str(&out).unwrap_or(Value::Null), err)
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/grimble/src/rule_cmd.rs::RuleTest
#[test]
fn rule_test_prints_a_line_per_example_and_exits_one_on_a_failure() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "rules/NOPE001.grl", RULE);
    let (code, env, err) = grimble(dir.path(), &["rule", "test", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    assert_eq!(env["data"]["passed"], 2);
    assert_eq!(env["data"]["files"][0]["examples"][0]["status"], "ok");
    let (code, out, _) = run_for_test(&grimble::cli(), &["rule", "test", "--text"], dir.path());
    assert_eq!(code, 0);
    assert!(
        out.contains("NOPE001  fire   ok (1 finding on line 2)"),
        "{out}"
    );
    write(
        dir.path(),
        "rules/NOPE001.grl",
        &RULE.replace("safe();", "danger();"),
    );
    let (code, env, _) = grimble(dir.path(), &["rule", "test", "--json"]);
    assert_eq!(code, 1);
    assert_eq!(env["data"]["failed"], 1);
    assert_eq!(env["data"]["files"][0]["examples"][1]["status"], "fail");
}

// frob:tests crates/grimble/src/rule_cmd.rs::RuleCheck
#[test]
fn rule_check_json_lists_cost_or_compile_errors_with_codes() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "rules/NOPE001.grl", RULE);
    let (code, env, err) = grimble(dir.path(), &["rule", "check", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    assert_eq!(env["data"]["files"][0]["rules"][0]["cost"], "per-file");
    write(
        dir.path(),
        "rules/NOPE001.grl",
        &RULE.replace("call", "cal"),
    );
    let (code, env, _) = grimble(dir.path(), &["rule", "check", "--json"]);
    assert_eq!(code, 1);
    assert_eq!(env["data"]["files"][0]["diagnostics"][0]["code"], "GRL001");
}

// frob:tests crates/grimble/src/rule_cmd.rs::RuleCatalog
#[test]
fn rule_catalog_json_returns_the_entry_or_a_did_you_mean() {
    let dir = tempfile::tempdir().unwrap();
    let (code, env, err) = grimble(dir.path(), &["rule", "catalog", "test", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    assert_eq!(env["data"]["entries"][0]["word"], "test");
    let (code, env, _) = grimble(dir.path(), &["rule", "catalog", "tset", "--json"]);
    assert_eq!(code, 1);
    assert_eq!(env["data"]["did_you_mean"], "test");
}

// frob:tests crates/grimble/src/rule_cmd.rs::RuleFmt
#[test]
fn rule_fmt_check_fails_on_a_messy_file_and_fmt_rewrites_it() {
    let dir = tempfile::tempdir().unwrap();
    let messy = RULE.replace(
        "  lang rust\n  severity error\n",
        "lang rust severity error\n",
    );
    write(dir.path(), "rules/NOPE001.grl", &messy);
    let (code, env, _) = grimble(dir.path(), &["rule", "fmt", "--check", "--json"]);
    assert_eq!(code, 1);
    assert_eq!(env["data"]["rewritten"][0], "rules/NOPE001.grl");
    let (code, env, err) = grimble(dir.path(), &["rule", "fmt", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    let after = std::fs::read_to_string(dir.path().join("rules/NOPE001.grl")).unwrap();
    assert_ne!(after, messy);
    let (code, _, _) = grimble(dir.path(), &["rule", "fmt", "--check", "--json"]);
    assert_eq!(code, 0);
}

// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
// frob:tests crates/grimble/src/rule_cmd.rs::RuleNew
#[test]
fn rule_new_writes_a_scaffold_whose_only_check_error_is_the_missing_clean_example() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "src/parse.rs",
        "fn p() {\n    dbg!(tokens.len());\n}\n",
    );
    let args = [
        "rule",
        "new",
        "NOPE001",
        "--from",
        "src/parse.rs:2",
        "--json",
    ];
    let (code, env, err) = grimble(dir.path(), &args);
    assert_eq!(code, 0, "{env} {err}");
    let text = std::fs::read_to_string(dir.path().join("rules/NOPE001.grl")).unwrap();
    assert!(text.contains("find d: `dbg!($$$ARGS)`"), "{text}");
    assert!(
        text.contains("example fire") && text.contains("## Remedy"),
        "{text}"
    );
    let (code, env, _) = grimble(dir.path(), &["rule", "check", "--json"]);
    assert_eq!(code, 1, "{env}");
    let errors: Vec<&str> = env["data"]["files"][0]["diagnostics"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|d| d["severity"] == "error")
        .map(|d| d["code"].as_str().unwrap())
        .collect();
    assert_eq!(errors, ["GRL011"], "{env}");
    let (code, _, err) = grimble(dir.path(), &args);
    assert_eq!(code, 2, "a second run must refuse to overwrite: {err}");
}

// frob:ticket 01M4PT1A52YR3QV6PYSGNC7N38
// frob:tests crates/grimble/src/rule_cmd.rs::RuleWhy
#[test]
fn rule_why_prints_the_trace_for_a_location_and_exits_zero() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "rules/NOPE001.grl", RULE);
    write(dir.path(), "a.rs", "fn b() {\n    danger();\n}\n");
    let (code, out, err) = run_for_test(
        &grimble::cli(),
        &["rule", "why", "NOPE001", "a.rs:2", "--text"],
        dir.path(),
    );
    assert_eq!(code, 0, "{out}{err}");
    assert!(out.contains("NOPE001 polarity"), "{out}");
    assert!(out.contains("1 candidate at 2:"), "{out}");
}
