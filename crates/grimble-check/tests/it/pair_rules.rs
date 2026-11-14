//! `grimble check` runs PAIR001 over the walk and reports an effect that never releases.

// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn pair_hits(dir: &Path) -> (usize, serde_json::Value) {
    let r = run(dir, &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let n = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "PAIR001")
        .count();
    (n, doc)
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn an_interval_without_cleanup_reports_pair001_through_the_pipeline() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/App.tsx",
        "export function App() {\n  useEffect(() => {\n    setInterval(tick, 1000);\n  }, []);\n  return null;\n}\n",
    );
    let (n, doc) = pair_hits(dir.path());
    assert_eq!(n, 1, "{doc}");
    assert!(
        doc["rules"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["rule"] == "PAIR001")
    );
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn an_interval_with_cleanup_reports_nothing() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/App.tsx",
        "export function App() {\n  useEffect(() => {\n    const id = setInterval(tick, 1000);\n    return () => clearInterval(id);\n  }, []);\n  return null;\n}\n",
    );
    let (n, doc) = pair_hits(dir.path());
    assert_eq!(n, 0, "{doc}");
}
