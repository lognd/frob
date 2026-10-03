//! The shared `[compute]` table and its canonical digest.

use gob_config::{ComputeTable, compute_digest};

// frob:tests crates/gob-config/src/compute.rs::compute_digest
#[test]
fn the_default_digest_is_the_pinned_canonical_blake3() {
    let dir = tempfile::tempdir().unwrap();
    let (table, source) = ComputeTable::load_for_product(dir.path(), "grimble").unwrap();
    assert_eq!(source, "grimble");
    assert_eq!(
        compute_digest(&table),
        "blake3:d2159af7d6267882f0176e553b7db75cd7ce68c9d1cd6dcc2b9a3a35a059f5eb"
    );
}

// frob:tests crates/gob-config/src/compute.rs::compute_digest
#[test]
fn a_changed_knob_changes_the_digest_and_frob_toml_wins() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(
        dir.path().join("frob.toml"),
        "[compute]\neffects = \"required\"\n",
    )
    .unwrap();
    let (table, source) = ComputeTable::load_for_product(dir.path(), "grimble").unwrap();
    assert_eq!(source, "frob");
    assert_eq!(table.effects, "required");
    assert_ne!(
        compute_digest(&table),
        compute_digest(&ComputeTable::default())
    );
}
