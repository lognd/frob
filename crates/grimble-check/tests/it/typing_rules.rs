#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! `grimble check` runs TYPING004 over the walk, and a second run reuses the cached report.

// frob:ticket 01M7E7HY77XT967FTS81EC8WTX

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// The `(rule, file)` of every TYPING finding in one run.
fn typing_hits(dir: &Path) -> Vec<(String, String)> {
    let r = run(dir, &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"].as_str().is_some_and(|r| r.starts_with("TYPING")))
        .map(|f| {
            (
                f["rule"].as_str().unwrap().to_owned(),
                f["file"].as_str().unwrap_or_default().to_owned(),
            )
        })
        .collect()
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn typing004_findings_from_the_cached_run_match_the_first_run() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/api.ts",
        "async function f(res: Response) {\n  return (await res.json()) as User;\n}\n",
    );
    let first = typing_hits(dir.path());
    assert_eq!(first.len(), 1, "{first:?}");
    assert_eq!(first[0].0, "TYPING004");
    let second = typing_hits(dir.path());
    assert_eq!(first, second);
}
