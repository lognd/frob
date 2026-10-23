#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! `grimble check` runs ERR001 to ERR003 over the walk: Certain sites warn, Unknown sites are Unresolved.

// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// The `(rule, severity)` of every ERR finding, and the whole document for failure messages.
fn err_hits(dir: &Path) -> (Vec<(String, String)>, serde_json::Value) {
    let r = run(dir, &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let hits = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"].as_str().is_some_and(|r| r.starts_with("ERR")))
        .map(|f| {
            (
                f["rule"].as_str().unwrap().to_owned(),
                f["severity"].as_str().unwrap_or_default().to_owned(),
            )
        })
        .collect();
    (hits, doc)
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn certain_error_handling_defects_warn() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/job.py",
        "def run(f):\n    try:\n        f()\n    except Exception:\n        pass\n\ndef go(f):\n    try:\n        f()\n    except Exception:\n        x = 1\n",
    );
    write(
        dir.path(),
        "src/lib.rs",
        "fn save() -> Result<(), String> {\n    Ok(())\n}\n\nfn f() {\n    let _ = save();\n}\n",
    );
    let (hits, doc) = err_hits(dir.path());
    let mut rules: Vec<&str> = hits.iter().map(|(r, _)| r.as_str()).collect();
    rules.sort_unstable();
    assert_eq!(rules, ["ERR001", "ERR002", "ERR003"], "{doc}");
    assert!(hits.iter().all(|(_, s)| s == "warning"), "{hits:?}");
    for id in ["ERR001", "ERR002", "ERR003"] {
        assert!(
            doc["rules"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r["rule"] == id),
            "{id} missing from {doc}"
        );
    }
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn an_unknown_callee_is_unresolved_not_warn() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/lib.rs",
        "fn f() {\n    let _ = mystery();\n}\n",
    );
    let (hits, doc) = err_hits(dir.path());
    assert_eq!(hits.len(), 1, "{doc}");
    assert_eq!(hits[0].0, "ERR002");
    assert_eq!(hits[0].1, "unresolved", "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn clean_handlers_report_nothing() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/job.py",
        "def run(f):\n    try:\n        f()\n    except Exception:\n        logger.exception('failed')\n",
    );
    let (hits, doc) = err_hits(dir.path());
    assert!(hits.is_empty(), "{doc}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_walk_without_qualifying_files_is_not_applicable() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(dir.path(), "README.md", "# hi\n");
    let (hits, doc) = err_hits(dir.path());
    assert!(hits.is_empty(), "{doc}");
}

// frob:tests crates/grimble-lints/src/rules/err001.rs::Err001
// frob:tests crates/grimble-lints/src/rules/err002.rs::Err002
// frob:tests crates/grimble-lints/src/rules/err003.rs::Err003
#[test]
fn each_err_rule_has_a_page_with_a_fire_and_a_clean_case() {
    let rules = Path::new(env!("CARGO_MANIFEST_DIR")).join("../grimble-lints/src/rules");
    for id in ["err001", "err002", "err003"] {
        let page = std::fs::read_to_string(rules.join(format!("{id}.md"))).unwrap();
        assert!(page.contains("expect=fire"), "{id}: no fire case");
        assert!(page.contains("expect=clean"), "{id}: no clean case");
    }
}
