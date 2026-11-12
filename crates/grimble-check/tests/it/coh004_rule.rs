//! COH004 as a registered rule: the vocabulary heuristic through `grimble check`.

// frob:ticket 01M5K18043Y5V9TF7QD2KNYR34

use grimble_check::{CheckOptions, run, sibling_document};

/// The COH004 findings of a repo holding `app/a.py` with `source`.
fn coh004_findings(source: &str) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("grimble.toml"), "[check]\n").unwrap();
    std::fs::create_dir_all(dir.path().join("app")).unwrap();
    std::fs::write(dir.path().join("app/a.py"), source).unwrap();
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    sibling_document(&r)["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "COH004")
        .cloned()
        .collect()
}

// frob:tests crates/grimble-check/src/rules/coh004.rs::Coh004
// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
// frob:tests crates/grimble-check/src/host.rs::CohHost.coh_subjects_of
#[test]
fn disjoint_vocabularies_are_reported_unresolved_never_error() {
    let found = coh004_findings(include_str!("../fixtures/coh004/fire.py"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "unresolved", "{found:?}");
}

// frob:tests crates/grimble-check/src/rules/coh004.rs::Coh004
#[test]
fn one_vocabulary_is_clean() {
    let found = coh004_findings(include_str!("../fixtures/coh004/clean.py"));
    assert!(found.is_empty(), "{found:?}");
}
