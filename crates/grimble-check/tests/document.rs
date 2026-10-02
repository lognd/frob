//! `grimble-check` on its own: the compute digest and the shape of the document.

use std::path::Path;

use grimble_check::config::{ComputeTable, blake3_tagged};
use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/grimble-check/src/config.rs::ComputeTable
#[test]
fn the_default_compute_digest_is_the_blake3_of_the_canonical_object() {
    let table = gob_config_default();
    assert_eq!(
        table.canonical_json(),
        r#"{"dynamic_calls":"warn-unresolved","effects":"warn-unresolved","expansion_steps":1000,"normalization":"warn-unresolved","notebook_order":"warn-unresolved","public_signatures":"warn-unresolved"}"#
    );
    // Recomputed independently with python blake3 over the same bytes.
    assert_eq!(
        table.digest(),
        "blake3:d2159af7d6267882f0176e553b7db75cd7ce68c9d1cd6dcc2b9a3a35a059f5eb"
    );
    assert_eq!(
        blake3_tagged(b"[]"),
        "blake3:d53d18c23212ea7b6300594bb89bce60218f6eff2b9d628b8cc42d3e79bbd5ab"
    );
}

fn gob_config_default() -> ComputeTable {
    let dir = tempfile::tempdir().unwrap();
    ComputeTable::load_for(dir.path()).unwrap().0
}

// frob:tests crates/grimble-check/src/config.rs::ComputeTable
#[test]
fn frob_toml_wins_over_grimble_toml_for_compute() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[compute]\nexpansion_steps = 5\n");
    write(dir.path(), "frob.toml", "[compute]\nexpansion_steps = 7\n");
    let (table, source) = ComputeTable::load_for(dir.path()).unwrap();
    assert_eq!((table.expansion_steps, source), (7, "frob"));
    std::fs::remove_file(dir.path().join("frob.toml")).unwrap();
    let (table, source) = ComputeTable::load_for(dir.path()).unwrap();
    assert_eq!((table.expansion_steps, source), (5, "grimble"));
    assert_ne!(table.digest(), gob_config_default().digest());
}

// frob:tests crates/grimble-check/src/sibling.rs::sibling_document
#[test]
fn the_document_lists_the_languages_the_walk_saw() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "");
    write(dir.path(), "src/lib.rs", "pub fn f() {}\n");
    write(dir.path(), "README.md", "# t\n");
    let doc = sibling_document(&run(dir.path(), &CheckOptions::default()).unwrap());
    let langs: Vec<&str> = doc["fidelity"]
        .as_array()
        .unwrap()
        .iter()
        .map(|f| f["language"].as_str().unwrap())
        .collect();
    assert_eq!(langs, ["grmb", "markdown", "opaque", "rust"]);
    assert_eq!(doc["invocation"]["root"], ".");
    assert!(doc["bindings"].as_array().unwrap().is_empty());
}
