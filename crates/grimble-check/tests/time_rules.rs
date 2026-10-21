//! `grimble check` runs the TIME rules over the walk and reports their findings.

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_stored_naive_now_read_reports_time001_through_the_pipeline() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "app/stamp.py",
        "import datetime\n\n\ndef stamp(record):\n    record.created = datetime.datetime.now()\n    return record\n",
    );
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let hits: Vec<&serde_json::Value> = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "TIME001")
        .collect();
    assert_eq!(hits.len(), 1, "{doc}");
    assert!(
        doc["rules"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["rule"] == "TIME002")
    );
}
