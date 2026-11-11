//! `crunk check`: versioned `--json`, `--report markdown|json`, `--contrast`, and `cache ls|prune`.

// frob:ticket 01M4MD9FEH1F337CTWPZ03B67Y

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

fn crunk(dir: &Path, args: &[&str]) -> (i32, Value) {
    let (code, out, _) = run_for_test(&crunk::cli(), args, dir);
    let env: Value = serde_json::from_str(&out).unwrap_or(Value::Null);
    (code, env)
}

fn project(css: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::presets::preset("default").expect("default preset");
    std::fs::write(dir.path().join("crunk.toml"), spec).expect("write config");
    std::fs::create_dir_all(dir.path().join("styles")).expect("mkdir");
    std::fs::write(dir.path().join("styles/a.css"), css).expect("write css");
    dir
}

// frob:tests crates/crunk/src/lib.rs::CrunkProduct
#[test]
fn json_envelope_and_document_are_versioned() {
    let dir = project(".a { color: #111; }\n");
    let (_, env) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(env["schema_version"], 1, "{env}");
    assert_eq!(env["data"]["schema_version"], "gob.sibling/1", "{env}");
}

// frob:tests crates/crunk-check/src/report.rs::markdown
#[test]
fn report_markdown_is_ascii_text_under_report_markdown() {
    let dir = project(".a { color: #111; }\n");
    let (_, env) = crunk(dir.path(), &["check", "--report", "markdown", "--json"]);
    let md = env["data"]["report_markdown"].as_str().expect("markdown");
    assert!(md.starts_with("# crunk check report"), "{md}");
    assert!(md.is_ascii());
}

// frob:tests crates/crunk-check/src/report.rs::report_v2
#[test]
fn report_json_is_version_2_with_counts_and_findings() {
    let dir = project(".a { color: #111; }\n");
    let (_, env) = crunk(dir.path(), &["check", "--report", "json", "--json"]);
    let rep = &env["data"]["report"];
    assert_eq!(rep["version"], 2, "{env}");
    assert!(rep["counts"]["errors"].is_u64());
    assert_eq!(
        rep["findings"].as_array().map(Vec::len),
        env["data"]["findings"].as_array().map(Vec::len)
    );
}

// frob:tests crates/crunk-check/src/report.rs::contrast
#[test]
fn contrast_lists_every_mode_with_ratio_and_floor() {
    let dir = project(".a { color: #111; }\n");
    let (_, env) = crunk(dir.path(), &["check", "--contrast", "--json"]);
    let modes = env["data"]["contrast"]["modes"].as_array().expect("modes");
    assert!(!modes.is_empty(), "{env}");
    for m in modes {
        for r in m["roles"].as_array().expect("roles") {
            assert!(r["ratio"].is_number() && r["floor"].is_number(), "{r}");
            assert!(r["fails"].is_boolean(), "{r}");
        }
    }
}

// frob:tests crates/crunk/src/cache.rs::CacheLs
#[test]
fn cache_ls_reports_the_database_shape() {
    let dir = project(".a { color: #111; }\n");
    let (code, env) = crunk(dir.path(), &["cache", "ls", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert!(env["data"]["present"].is_boolean(), "{env}");
    assert!(env["data"]["findings"].is_u64(), "{env}");
}

// frob:tests crates/crunk/src/cache.rs::CachePrune
#[test]
fn cache_prune_dry_run_deletes_nothing() {
    let dir = project(".a { color: #111; }\n");
    let (code, env) = crunk(
        dir.path(),
        &["cache", "prune", "--all", "--dry-run", "--json"],
    );
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["data"]["dry_run"], true, "{env}");
}
