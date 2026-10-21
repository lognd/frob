//! `crunk rule catalog` end to end: the `[packs] crunk_web` switch gates the pack rows.

// frob:ticket 01M50AQ6XHV6Z8GS0V8J66M9GD

use std::path::Path;

use assert_cmd::Command;
use serde_json::Value;

fn project(packs: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::presets::preset("default").expect("default preset");
    std::fs::write(dir.path().join("crunk.toml"), format!("{spec}\n{packs}")).expect("spec");
    dir
}

fn catalog(dir: &Path) -> Value {
    let out = Command::cargo_bin("crunk")
        .expect("crunk binary")
        .current_dir(dir)
        .args(["rule", "catalog", "--json"])
        .output()
        .expect("runs");
    let text = String::from_utf8_lossy(&out.stdout).into_owned();
    serde_json::from_str(&text).unwrap_or_else(|e| panic!("{e}: {text}"))
}

// frob:tests crates/crunk/src/rule.rs::RuleCatalog
#[test]
fn the_catalog_is_empty_until_crunk_web_is_switched_on() {
    let off = catalog(project("").path());
    assert_eq!(
        off["data"]["packs"].as_array().map(Vec::len),
        Some(0),
        "{off}"
    );
    let off = catalog(project("[packs]\ncrunk_web = false\n").path());
    assert_eq!(
        off["data"]["packs"].as_array().map(Vec::len),
        Some(0),
        "{off}"
    );
}

// frob:tests crates/crunk/src/rule.rs::RuleCatalog
#[test]
fn the_catalog_lists_the_pack_rules_when_crunk_web_is_on() {
    let on = catalog(project("[packs]\ncrunk_web = true\n").path());
    let rules: Vec<&str> = on["data"]["packs"]
        .as_array()
        .expect("rows")
        .iter()
        .map(|r| r["rule"].as_str().expect("rule"))
        .collect();
    let expected = crunk_check::packs::plans().expect("pack plans").len();
    assert_eq!(rules.len(), expected, "{on}");
    assert!(
        rules.contains(&"A11Y101") && rules.contains(&"WEBPERF101"),
        "{rules:?}"
    );
    assert_eq!(on["data"]["packs"][0]["pack"], "crunk-web");
}
