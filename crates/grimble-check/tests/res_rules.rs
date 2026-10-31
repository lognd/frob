#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! `grimble check` runs RES001 over the walk: Certain sites warn, Unknown sites are Unresolved.

// frob:ticket 01M4MGE2XKGBNJEV1AECPBVHQF

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// The `(rule, severity)` of every RES finding, and the whole document for failure messages.
fn res_hits(dir: &Path) -> (Vec<(String, String)>, serde_json::Value) {
    let r = run(dir, &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let hits = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"].as_str().is_some_and(|r| r.starts_with("RES")))
        .map(|f| {
            (
                f["rule"].as_str().unwrap().to_owned(),
                f["severity"].as_str().unwrap_or_default().to_owned(),
            )
        })
        .collect();
    (hits, doc)
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn an_unpaired_performance_mark_warns_and_the_paired_one_is_quiet() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/a.ts",
        "export function f() {\n  performance.mark('start');\n}\n",
    );
    let (hits, doc) = res_hits(dir.path());
    assert_eq!(hits.len(), 1, "{doc}");
    assert_eq!(hits[0].0, "RES001");
    assert_eq!(hits[0].1, "error", "{doc}");

    write(
        dir.path(),
        "src/a.ts",
        "export function f() {\n  performance.mark('start');\n  performance.clearMarks('start');\n}\n",
    );
    let (hits, doc) = res_hits(dir.path());
    assert!(hits.is_empty(), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_handle_that_escapes_the_scope_is_unresolved_not_warn() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/a.ts",
        "export function f() {\n  const t = setTimeout(() => {}, 10);\n  return t;\n}\n",
    );
    let (hits, doc) = res_hits(dir.path());
    assert_eq!(hits.len(), 1, "{doc}");
    assert_eq!(hits[0].0, "RES001");
    assert_eq!(hits[0].1, "unresolved", "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_walk_without_script_files_is_not_applicable() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(dir.path(), "README.md", "# hi\n");
    write(dir.path(), "src/a.py", "import threading\n");
    let (hits, doc) = res_hits(dir.path());
    assert!(hits.is_empty(), "{doc}");
}

// frob:tests crates/grimble-lints/src/rules/res001.rs::Res001
#[test]
fn res001_has_a_page_with_a_fire_and_a_clean_case() {
    let rules = Path::new(env!("CARGO_MANIFEST_DIR")).join("../grimble-lints/src/rules");
    let page = std::fs::read_to_string(rules.join("res001.md")).unwrap();
    assert!(page.contains("expect=fire"), "no fire case");
    assert!(page.contains("expect=clean"), "no clean case");
}
