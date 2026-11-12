//! Small public entry points: `survey`, `file_row`, `graph_document`, the model view and the
//! bind cache digest.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5


use std::path::Path;

use grimble_check::model_view::file_row;
use grimble_check::{CheckOptions, graph_document, run, survey};

/// Write `text` at `rel` under `dir`, creating parents.
fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// A repo with one model, one Rust file and one file no adapter reads.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/model.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/model.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn f() {}\n");
    dir
}

// frob:tests crates/grimble-check/src/lib.rs::survey
// frob:tests crates/grimble-check/src/fidelity.rs::language_tag
#[test]
fn survey_counts_languages_and_lists_model_files() {
    let dir = repo();
    let s = survey(dir.path()).unwrap();
    assert_eq!(s.models, vec!["design/model.grmb".to_owned()]);
    assert_eq!(s.languages.get("grmb"), Some(&1));
    assert!(s.languages.get("rust").is_some_and(|n| *n >= 1));
}

// frob:tests crates/grimble-check/src/model_view.rs::file_row
#[test]
fn file_row_reports_parsed_model_files() {
    let row = file_row(
        "design/m.grmb",
        b"grimble = \"2\";\nmodule m;\nnode a : trusted { }\n",
    );
    assert_eq!(row.path, "design/m.grmb");
    assert_eq!(row.status, "parsed");
    assert!(row.reason.is_none());
}

// frob:tests crates/grimble-check/src/sibling.rs::graph_document
// frob:tests crates/grimble-check/src/model_view.rs::ModelView.entities_json
// frob:tests crates/grimble-check/src/bind_cache.rs::digest
// frob:tests crates/grimble-check/src/bind_cache.rs::BindSummary.of
#[test]
fn graph_document_lists_the_entities_of_the_model() {
    let dir = repo();
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = graph_document(&r);
    let entities = doc["entities"].as_array().unwrap();
    assert!(
        entities.iter().any(|e| e["name"].to_string().contains('a')),
        "{entities:?}"
    );
    assert_eq!(entities, &r.view.entities_json());
}

// frob:tests crates/grimble-check/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule_for_the_grimble_product() {
    let bound = grimble_check::rules::bind::<grimble_check::GrimbleInputs>();
    assert_eq!(bound.len(), grimble_check::rules::METAS.len());
}
