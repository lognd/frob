//! `grimble check` runs UNITY201 and UNITY202 over Unity C# and reports hot-path lookups and allocations.

// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn script(body: &str) -> String {
    format!("using UnityEngine;\npublic class Mover : MonoBehaviour {{\n{body}\n}}\n")
}

/// Findings of `rule` and the whole document for a repo holding `config` and one C# `source`.
fn hits(config: &str, source: &str, rule: &str) -> (Vec<serde_json::Value>, serde_json::Value) {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", config);
    write(dir.path(), "Assets/Scripts/Mover.cs", source);
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let found = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == rule)
        .cloned()
        .collect();
    (found, doc)
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
fn get_component_in_update_reports_unity201_through_the_pipeline() {
    let src = script("void Update() { var r = GetComponent<Rigidbody>(); }");
    let (found, doc) = hits("[check]\n", &src, "UNITY201");
    assert_eq!(found.len(), 1, "{doc}");
    assert!(lists_rule(&doc, "UNITY201"), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn allocation_in_update_reports_unity202_through_the_pipeline() {
    let src = script("void Update() { var l = new List<int>(); }");
    let (found, doc) = hits("[check]\n", &src, "UNITY202");
    assert_eq!(found.len(), 1, "{doc}");
    assert!(lists_rule(&doc, "UNITY202"), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_lookup_cached_in_awake_reports_nothing() {
    let src = script(
        "Rigidbody rb;\nvoid Awake() { rb = GetComponent<Rigidbody>(); }\nvoid Update() { rb.AddForce(Vector3.up); }",
    );
    let (found, doc) = hits("[check]\n", &src, "UNITY201");
    assert!(found.is_empty(), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn csharp_outside_unity_reports_nothing() {
    let src = "public class Plain {\n  void Update() { var l = new List<int>(); }\n}\n";
    let (found, doc) = hits("[check]\n", src, "UNITY202");
    assert!(found.is_empty(), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_severity_override_applies_to_unity201() {
    let src = script("void Update() { var r = GetComponent<Rigidbody>(); }");
    let (found, doc) = hits(
        "[check]\n\n[rules.UNITY201]\nseverity = \"error\"\n",
        &src,
        "UNITY201",
    );
    assert_eq!(found.len(), 1, "{doc}");
    assert_eq!(found[0]["severity"], "error", "{doc}");
}
