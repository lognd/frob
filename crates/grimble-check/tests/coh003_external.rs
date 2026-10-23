//! COH003 external callees and the single repo-level note of a repo with no layer source.

// frob:ticket 01M5M34XTDZEZ08TAA78872RRP

#![allow(unused_crate_dependencies)]

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

const TS_EXTERNAL: &str =
    "export function f(x: string) {\n  console.log(x);\n  return JSON.stringify(x);\n}\n";
const TOP: &str = "def f(order, raw):\n    total = price_order(order)\n    head = raw[2:5]\n    return total, head\n";
const PRICE: &str = "def price_order(order):\n    return order\n";

/// The COH003 findings of a repo made of `files`.
fn findings(files: &[(&str, &str)]) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    for (rel, text) in files {
        let path = dir.path().join(rel);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, text).unwrap();
    }
    let r = run(Path::new(dir.path()), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "COH003")
        .cloned()
        .collect()
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
// frob:tests crates/grimble-check/src/layers.rs::coh003_options
#[test]
fn external_callees_never_produce_unresolved() {
    let found = findings(&[
        ("grimble.toml", "[check]\n"),
        ("a.ts", TS_EXTERNAL),
        ("b.ts", TS_EXTERNAL),
    ]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
#[test]
fn single_depth_repo_without_layers_yields_one_repo_note() {
    let found = findings(&[
        ("grimble.toml", "[check]\n"),
        ("top.py", TOP),
        ("top2.py", TOP),
        ("price.py", PRICE),
        ("ext.ts", TS_EXTERNAL),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "unresolved", "{found:?}");
    let message = found[0]["message"].as_str().unwrap();
    assert!(message.contains("price_order"), "{message}");
    assert!(!message.contains("console"), "{message}");
}
