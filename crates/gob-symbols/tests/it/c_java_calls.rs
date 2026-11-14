//! C and Java calls resolve to their own definitions, not through the Rust-only path.

use gob_symbols::{FileSymbols, Status, SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn extract(path: &str, text: &str) -> FileSymbols {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    extract_file(&entry, text)
}

/// The targets of every resolved call edge in `files`, printed.
fn targets(files: &[(&str, &str)]) -> Vec<(String, Status)> {
    let g = SymbolGraph::from_files(files.iter().map(|(p, t)| extract(p, t)).collect());
    g.edges_with_status()
        .iter()
        .filter_map(|e| e.to.as_ref().map(|t| (t.to_string(), e.status)))
        .collect()
}

// frob:ticket 01M7BSMQWJ77EENS87BQBQWFB4
// frob:tests crates/gob-symbols/src/graph/flat.rs::SymbolGraph.resolve_flat
#[test]
fn c_bare_call_resolves_to_same_file_function() {
    let t = targets(&[(
        "a.c",
        "static int helper(void) { return 1; }\nint caller(void) { return helper(); }\n",
    )]);
    assert!(t.iter().any(|(to, _)| to.ends_with("::helper")), "{t:?}");
}

// frob:ticket 01M7BSMQWJ77EENS87BQBQWFB4
// frob:tests crates/gob-symbols/src/graph/flat.rs::SymbolGraph.resolve_flat
#[test]
fn java_bare_call_resolves_to_private_method() {
    let t = targets(&[(
        "A.java",
        "class A {\n  private int helper() { return 1; }\n  int caller() { return helper(); }\n}\n",
    )]);
    assert!(t.iter().any(|(to, _)| to.ends_with("helper")), "{t:?}");
}
