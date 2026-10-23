#![allow(
    clippy::disallowed_methods,
    reason = "a test reads a design page, not a walked snapshot"
)]
//! The design docs state the folded end-owner and MDL005 behaviour the code implements.

// frob:ticket 01M5MRKJQ8JA1EBR70QJ3C9H73

use std::path::{Path, PathBuf};

/// Read a design page, whitespace-flattened, from the repository root (two levels above this crate).
fn design_page(name: &str) -> String {
    let path: PathBuf = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../docs/design")
        .join(name);
    let text = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

// frob:tests crates/grimble-bind/src/eval.rs::end_owner
#[test]
fn binding_md_says_end_owner_reports_once_per_clause() {
    let flat = design_page("binding.md");
    for needle in [
        "reports once",
        "count of units",
        "a sample of at most 3 units",
        "per-unit rows",
        "`bindings` of `grimble check --json`",
    ] {
        assert!(flat.contains(needle), "binding.md lacks `{needle}`");
    }
}

// frob:tests crates/grimble-model/src/check.rs::Checker.selector
#[test]
fn grmb_spec_example_has_two_mdl005_with_both_sites_listed() {
    let flat = design_page("grmb-spec.md");
    assert!(flat.contains("two MDL005 Warn findings"), "count missing");
    assert!(
        flat.contains("one finding that lists every clause site"),
        "folding missing"
    );
    assert!(
        flat.contains("`crates/grimble-*/**` (written twice) is one finding listing both sites"),
        "selector example missing"
    );
    assert!(!flat.contains("for the three selectors"), "stale count");
}
