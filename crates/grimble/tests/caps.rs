//! `grimble check` standalone runs the capability rules like `grimble-check` hosted by frob.

// frob:ticket 01M4H408PG9RR728AQGGRETKJ3

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn rule_ids(doc: &Value, key: &str) -> Vec<String> {
    doc["data"][key]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|f| f["rule"].as_str())
        .map(str::to_owned)
        .collect()
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn standalone_check_lists_and_fires_the_cap_rules() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n",
    );
    write(
        dir.path(),
        "src/x.py",
        "import subprocess\n\ndef go():\n    subprocess.run([\"ls\"])\n",
    );
    let (_, out, err) = run_for_test(&grimble::cli(), &["check", "--json"], dir.path());
    let doc: Value = serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out} {err}"));
    let rules = rule_ids(&doc, "rules");
    assert!(
        rules.contains(&"CAP001".to_owned()) && rules.contains(&"CAP002".to_owned()),
        "{rules:?}"
    );
    assert!(
        rule_ids(&doc, "findings").contains(&"CAP001".to_owned()),
        "{doc}"
    );
    // The host that embeds grimble-check (frob) lists exactly the same rules.
    let hosted = grimble_check::sibling_document(
        &grimble_check::run(dir.path(), &grimble_check::CheckOptions::default()).unwrap(),
    );
    assert_eq!(rules, rule_ids(&hosted_envelope(&hosted), "rules"));
}

/// The hosted document wrapped like the CLI envelope, so one reader serves both.
fn hosted_envelope(doc: &Value) -> Value {
    serde_json::json!({ "data": doc })
}
