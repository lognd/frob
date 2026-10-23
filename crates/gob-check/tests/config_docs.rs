//! The generated config reference documents the `[check] exclude` report-directory opt-in.

#![allow(
    clippy::disallowed_methods,
    reason = "a test reads the generated reference, not a walked snapshot"
)]

use std::path::PathBuf;

// frob:ticket 01M5MDT81QR8F0E67N61AYZDN2
// frob:tests crates/gob-check/src/config.rs::CheckTable
#[test]
fn the_generated_config_reference_documents_the_exclude_opt_in() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../docs/reference/config.md");
    let text = std::fs::read_to_string(path).expect("read the config reference");
    let row = text
        .lines()
        .find(|l| l.starts_with("| `exclude` |") && l.contains("no rule inspects"))
        .expect("the check exclude row");
    assert!(row.contains("`!dir/`"), "opt-in undocumented: {row}");
    assert!(
        row.contains("htmlcov"),
        "default report dirs undocumented: {row}"
    );
}
