//! A warm cache: the second `crunk check` reuses the cached ingest and reports the same findings.

// frob:ticket 01M43ATCF5GGK59S96K1ZF0G9C

use std::path::Path;

use crunk_check::{CheckOptions, run};
use gob_cache::Cache;

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn the_second_run_reuses_cached_ingest_and_reports_the_same_findings() {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec_text = crunk_spec::presets::preset("default")
        .expect("default preset")
        .replace("[lint]", "[lint]\nTOKENS001 = \"off\"\nORG001 = \"off\"");
    write(dir.path(), "crunk.toml", &spec_text);
    write(dir.path(), "styles/a.css", ".a { color: #ff0000; }\n");
    write(
        dir.path(),
        "styles/b.css",
        ".b { color: #00ff00; margin: 0; }\n",
    );

    let ids = |run: &crunk_check::CrunkRun| -> Vec<String> {
        run.report
            .findings
            .iter()
            .map(|f| format!("{} {}", f.rule.as_str(), f.message))
            .collect()
    };
    let first = run(dir.path(), &CheckOptions::default()).expect("first run");
    let second = run(dir.path(), &CheckOptions::default()).expect("second run");
    assert!(!ids(&first).is_empty());
    assert_eq!(ids(&first), ids(&second));

    // The product's own cache directory: a third ingest finds every sheet already cached.
    let spec = crunk_spec::load_spec(dir.path()).expect("spec");
    let cache = Cache::open_shared(dir.path(), ".crunk");
    let ingested = crunk_ingest::ingest_tree(&spec, &cache).expect("ingest");
    assert_eq!(ingested.stats.parsed, 0, "{:?}", ingested.stats);
    assert!(ingested.stats.cached >= 2, "{:?}", ingested.stats);
}
