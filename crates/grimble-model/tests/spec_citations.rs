//! Code comments cite grmb-spec sections, never the retired grmb-planning document.

// frob:ticket 01M69AHE03R04HDKKDT03B2YRN

use std::fs;
use std::path::{Path, PathBuf};

/// Every `.rs` file under `dir`, recursively.
fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).expect("read_dir").flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_files(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

#[test]
fn no_source_cites_the_retired_grmb_planning_document() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let needle = ["grmb", "planning"].join("-");
    let mut files = Vec::new();
    rust_files(&root.join("src"), &mut files);
    let offenders: Vec<_> = files
        .iter()
        .filter(|f| fs::read_to_string(f).expect("read").contains(&needle))
        .collect();
    assert!(offenders.is_empty(), "retired citation in {offenders:?}");
}
