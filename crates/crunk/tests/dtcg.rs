//! `crunk import dtcg` then `crunk export dtcg` end to end: the result equals the input.

// frob:ticket 01M4CXQYFA9ACDVWF4R62C50FH

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const DOC: &str = r##"{
  "color": {"$type": "color", "ink": {"$value": "#111111", "$description": "text"},
            "link": {"$value": "{color.ink}"}},
  "space": {"$type": "dimension", "s": {"$value": {"value": 4, "unit": "px"}}},
  "future": {"$type": "x-custom", "$extensions": {"a": 1}, "t": {"$value": [1, 2.50]}}
}"##;

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(
        dir.path().join("crunk.toml"),
        "[project]\ncss_root = \"styles\"\n",
    )
    .unwrap();
    std::fs::write(dir.path().join("in.tokens.json"), DOC).unwrap();
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn json(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not json ({e}): {out}"))
}

// frob:tests crates/crunk/src/dtcg.rs::ImportDtcg
// frob:tests crates/crunk/src/dtcg.rs::ExportDtcg
#[test]
fn import_then_export_equals_the_input_up_to_key_order() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["import", "dtcg", "in.tokens.json", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    assert_eq!(json(&out)["data"]["tokens"], 4);
    assert!(dir.path().join("design/tokens.dtcg.json").is_file());

    let (code, out, err) = crunk(
        dir.path(),
        &["export", "dtcg", "--out", "back.json", "--json"],
    );
    assert_eq!(code, 0, "{out} {err}");
    let back: Value =
        serde_json::from_str(&std::fs::read_to_string(dir.path().join("back.json")).unwrap())
            .unwrap();
    assert_eq!(back, serde_json::from_str::<Value>(DOC).unwrap());

    let (code, out, _) = crunk(dir.path(), &["export", "dtcg", "--json"]);
    assert_eq!(code, 0, "{out}");
    let printed = json(&out)["data"]["content"].as_str().unwrap().to_owned();
    assert_eq!(serde_json::from_str::<Value>(&printed).unwrap(), back);
}

// frob:tests crates/crunk/src/dtcg.rs::ImportDtcg
#[test]
fn dry_run_import_writes_nothing_and_a_bad_file_is_refused() {
    let dir = project();
    let (code, out, _) = crunk(
        dir.path(),
        &["import", "dtcg", "in.tokens.json", "--dry-run", "--json"],
    );
    assert_eq!(code, 0, "{out}");
    assert!(!dir.path().join("design").exists());

    std::fs::write(dir.path().join("bad.json"), r#"{"a": {"$value": 1}}"#).unwrap();
    let (code, out, _) = crunk(dir.path(), &["import", "dtcg", "bad.json", "--json"]);
    assert_ne!(code, 0, "{out}");
    assert!(out.contains("E-DTCG"), "{out}");
}
