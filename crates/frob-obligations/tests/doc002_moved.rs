//! DOC002 on a link into a moved document or heading names the new location from
//! `docs/MOVED.toml`.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

mod common;

use frob_obligations::InvariantsConfig;

/// Evaluate a tree holding `files`; return the DOC002 messages.
fn doc002(files: &[(&str, &str)]) -> Vec<String> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("frob.toml", "")]);
    common::write_tree(dir.path(), files);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let eval = common::evaluate_tree(dir.path(), None, &config, None);
    eval.findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "DOC002")
        .map(|f| f.message)
        .collect()
}

// frob:tests doc002
#[test]
fn link_to_a_moved_file_names_the_new_location() {
    let found = doc002(&[
        ("docs/new.md", "# New\n"),
        (
            "docs/MOVED.toml",
            "[moved]\n\"docs/old.md\" = \"docs/new.md\"\n",
        ),
        ("docs/a.md", "# A\n\nSee [old](old.md).\n"),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("it moved to `docs/new.md`"), "{found:?}");
}

// frob:tests doc002
#[test]
fn link_to_a_moved_heading_names_the_new_location() {
    let found = doc002(&[
        ("docs/b.md", "# B\n\n## Fresh\n"),
        (
            "docs/MOVED.toml",
            "[moved]\n\"docs/b.md#stale\" = \"docs/b.md#fresh\"\n",
        ),
        ("docs/a.md", "# A\n\nSee [b](b.md#stale).\n"),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].contains("it moved to `docs/b.md#fresh`"),
        "{found:?}"
    );
}
