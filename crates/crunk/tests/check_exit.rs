//! `crunk check` exit codes end to end: findings, refused configs and usage errors.

// frob:ticket 01M43ATCF5GGK59S96K1ZF0G9C

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

fn crunk(dir: &Path, args: &[&str]) -> (i32, Value) {
    let (code, out, _) = run_for_test(&crunk::cli(), args, dir);
    (code, serde_json::from_str(&out).unwrap_or(Value::Null))
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

fn project(css: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::presets::preset("default")
        .expect("default preset")
        .replace(
            "[lint]",
            "[lint]\nTOKENS001 = \"off\"\nEXPORT001 = \"off\"\nORG001 = \"off\"",
        );
    write(
        dir.path(),
        "crunk.toml",
        &format!("{spec}\n[rules]\nramp = false\n"),
    );
    write(dir.path(), "styles/a.css", css);
    dir
}

/// A project with the default severity ramp left on.
fn ramped_project(css: &str) -> tempfile::TempDir {
    let dir = project(css);
    let spec = std::fs::read_to_string(dir.path().join("crunk.toml")).expect("read");
    write(
        dir.path(),
        "crunk.toml",
        &spec.replace("ramp = false", "ramp = true"),
    );
    dir
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn the_default_ramp_downgrades_a_new_rule_so_check_exits_zero() {
    let dir = ramped_project(".a { color: #ff0000; }\n");
    let (code, env) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{env}");
    let findings = env["data"]["findings"].as_array().expect("findings");
    let hit = findings
        .iter()
        .find(|f| f["rule"] == "COLOR001")
        .expect("COLOR001");
    assert_eq!(hit["severity"], "warning", "{hit}");
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn an_error_severity_violation_exits_one() {
    let dir = project(".a { color: #ff0000; }\n");
    let (code, env) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 1, "{env}");
    let findings = env["data"]["findings"].as_array().expect("findings");
    assert!(
        findings.iter().any(|f| f["rule"] == "COLOR001"),
        "{findings:?}"
    );
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn a_clean_project_exits_zero() {
    let dir = project(".a { margin: 0; }\n");
    let (code, env) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{env}");
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn an_unreadable_config_is_refused_with_e_config_not_passed() {
    let dir = project(".a { margin: 0; }\n");
    write(dir.path(), "crunk.toml", "this is = = not toml\n");
    let (code, env) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 3, "{env}");
    assert_eq!(env["error"]["code"], "E-CONFIG", "{env}");
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn a_usage_error_exits_two() {
    let dir = project(".a { margin: 0; }\n");
    let (code, _) = crunk(dir.path(), &["check", "--no-such-flag"]);
    assert_eq!(code, 2);
}
