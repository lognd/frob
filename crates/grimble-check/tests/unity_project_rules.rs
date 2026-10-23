//! `grimble check` runs UNITY301 and UNITY302 and reports input-handler and physics-timing misuse.

// frob:ticket 01M5HGRWG7RDR3DTS7PT08HTWJ

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

const SETTINGS: &str = "ProjectSettings/ProjectSettings.asset";

fn settings(handler: u8) -> String {
    format!("%YAML 1.1\n--- !u!129 &1\nPlayerSettings:\n  activeInputHandler: {handler}\n")
}

const INPUT: &str = "using UnityEngine;\npublic class M : MonoBehaviour {\n void Update() { if (Input.GetKey(KeyCode.W)) {} }\n}\n";
const FORCE: &str = "using UnityEngine;\npublic class P : MonoBehaviour {\n Rigidbody body;\n void Update() { body.AddForce(Vector3.up); }\n}\n";

/// The whole document for a repo holding the given `(path, text)` files.
fn document(files: &[(&str, String)]) -> serde_json::Value {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    sibling_document(&r)
}

fn hits(doc: &serde_json::Value, rule: &str) -> usize {
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == rule)
        .count()
}

fn lists_rule(doc: &serde_json::Value, rule: &str) -> bool {
    doc["rules"]
        .as_array()
        .unwrap()
        .iter()
        .any(|r| r["rule"] == rule)
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn legacy_input_under_the_input_system_reports_unity301() {
    let doc = document(&[
        ("Assets/Scripts/M.cs", INPUT.to_owned()),
        (SETTINGS, settings(1)),
    ]);
    assert_eq!(hits(&doc, "UNITY301"), 1, "{doc}");
    assert!(lists_rule(&doc, "UNITY301"), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn default_input_handler_and_missing_settings_report_nothing() {
    let both = document(&[
        ("Assets/Scripts/M.cs", INPUT.to_owned()),
        (SETTINGS, settings(2)),
    ]);
    assert_eq!(hits(&both, "UNITY301"), 0, "{both}");
    let none = document(&[("Assets/Scripts/M.cs", INPUT.to_owned())]);
    assert_eq!(hits(&none, "UNITY301"), 0, "{none}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_force_from_update_reports_unity302() {
    let doc = document(&[("Assets/Scripts/P.cs", FORCE.to_owned())]);
    assert_eq!(hits(&doc, "UNITY302"), 1, "{doc}");
    assert!(lists_rule(&doc, "UNITY302"), "{doc}");
}
