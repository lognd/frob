//! DOC007: a document under `docs/` that no link chain from a root page reaches.

// frob:ticket 01M67VEKBESFK2C23JMXV82RW9

mod common;

use frob_obligations::InvariantsConfig;
use gob_rules::Finding;

/// Evaluate a tree holding `files`; return the DOC007 findings.
fn doc007(files: &[(&str, &str)]) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("frob.toml", "")]);
    common::write_tree(dir.path(), files);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let eval = common::evaluate_tree(dir.path(), None, &config, None);
    eval.findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "DOC007")
        .collect()
}

// frob:tests doc007
#[test]
fn page_nothing_links_to_is_named_with_the_heuristic() {
    let found = doc007(&[
        ("docs/README.md", "# Index\n\n[a](a.md)\n"),
        ("docs/a.md", "# A\n"),
        ("docs/lost.md", "# Lost\n"),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("frob:waive"),
        "{}",
        found[0].message
    );
}

// frob:tests doc007
#[test]
fn pages_reached_from_the_index_or_a_root_page_are_clean() {
    let found = doc007(&[
        ("README.md", "# Root\n\n[g](docs/guide/)\n"),
        ("docs/README.md", "# Index\n\n[a](a.md)\n"),
        ("docs/a.md", "# A\n"),
        ("docs/guide/README.md", "# Guide\n"),
    ]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests doc007
#[test]
fn historical_pages_are_exempt() {
    let found = doc007(&[
        ("docs/README.md", "# Index\n"),
        ("docs/old.md", "# Old\n\nStatus: historical\n"),
    ]);
    assert!(found.is_empty(), "{found:?}");
}
