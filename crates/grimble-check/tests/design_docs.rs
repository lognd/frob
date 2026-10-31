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
fn grmb_spec_states_mdl005_is_a_warning_that_suppresses_sys001() {
    let flat = design_page("grmb-spec.md");
    assert!(
        flat.contains("| MDL005 | MDL-SELECTOR-NO-FILE | Warn |"),
        "MDL005 Warn row missing"
    );
    assert!(
        flat.contains(
            "It suppresses SYS001 for the same selector so one root cause is one finding"
        ),
        "one-root-cause folding missing"
    );
    assert!(
        flat.contains("a selector whose file matches but whose units do not is SYS001"),
        "SYS001 split missing"
    );
}
