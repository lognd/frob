//! `[rules.<id>] severity` in `grimble.toml` overrides a rule's severity through `grimble check`.

// frob:ticket 01M5FSSDC7EG5QA70CRABC8SMA

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

const STAMP: &str = "import datetime\n\n\ndef stamp(record):\n    record.created = datetime.datetime.now()\n    return record\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// Severity of the first TIME001 finding of a run over a repo with `config` as its grimble.toml.
fn time001_severity(config: &str) -> Result<String, String> {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", config);
    write(dir.path(), "app/stamp.py", STAMP);
    let r = run(dir.path(), &CheckOptions::default()).map_err(|e| e.to_string())?;
    let doc = sibling_document(&r);
    let f = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["rule"] == "TIME001")
        .unwrap_or_else(|| panic!("no TIME001 in {doc}"))
        .clone();
    Ok(f["severity"].as_str().unwrap().to_owned())
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn rules_severity_raises_time001_to_error() {
    assert_eq!(time001_severity("[check]\n").unwrap(), "warning");
    let raised = time001_severity("[rules.TIME001]\nseverity = \"error\"\n").unwrap();
    assert_eq!(raised, "error");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn rules_severity_can_lower_and_ignores_unknown_ids() {
    let cfg = "[rules.TIME001]\nseverity = \"advisory\"\n[rules.NOPE999]\nseverity = \"error\"\n";
    assert_eq!(time001_severity(cfg).unwrap(), "advisory");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn rules_severity_invalid_token_fails_the_run() {
    let err = time001_severity("[rules.TIME001]\nseverity = \"fatal\"\n").unwrap_err();
    assert!(err.contains("TIME001.severity"), "{err}");
}
