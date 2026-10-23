//! DOC006: a prose citation of a markdown section or anchor must resolve, directly or through
//! `docs/MOVED.toml`.

// frob:ticket 01M4H0RE1Q9A1M47ZT7Q1ZG43K

mod common;

use frob_obligations::InvariantsConfig;
use gob_rules::Finding;

/// A tickets document with sections 1 and 2 and a `Life cycle` heading.
const TICKETS: &str = "# Tickets\n\n## 1. Intro\n\n## 2. Life cycle (v2)\n\n## Same\n\n## Same\n";

/// Evaluate a tree holding `files`; return the DOC006 findings.
fn doc006(files: &[(&str, &str)]) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("frob.toml", "")]);
    common::write_tree(dir.path(), files);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let eval = common::evaluate_tree(dir.path(), None, &config, None);
    eval.findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "DOC006")
        .collect()
}

// frob:tests doc006
#[test]
fn missing_section_names_the_citation_and_the_target() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        ("docs/a.md", "# A\n\nSee tickets.md section 6 here.\n"),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    let m = &found[0].message;
    assert!(
        m.contains("tickets.md section 6") && m.contains("no section 6"),
        "{m}"
    );
}

// frob:tests doc006
#[test]
fn crate_comment_citation_is_checked() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        (
            "crates/x/src/lib.rs",
            "// per tickets.md section 6\nfn f() { let _ = \"tickets.md section 9\"; }\n",
        ),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
}

// frob:tests doc006
#[test]
fn existing_sections_and_anchors_are_clean() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        (
            "docs/a.md",
            "# A\n\ntickets.md section 2, tickets.md#2-life-cycle-v2, tickets.md#SAME-1 and docs/tickets.md section 1.\n",
        ),
    ]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests doc006
#[test]
fn missing_anchor_and_missing_file_are_named() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        (
            "docs/a.md",
            "# A\n\ntickets.md#nope and gone.md section 1 and tickets.md#same-2.\n",
        ),
    ]);
    assert_eq!(found.len(), 3, "{found:?}");
    assert!(
        found
            .iter()
            .any(|f| f.message.contains("no file `gone.md`"))
    );
}

// frob:tests doc006
#[test]
fn fences_urls_links_and_bare_mentions_are_clean() {
    let text = "# A\n\n```\ntickets.md section 6\n```\nhttps://x.io/tickets.md#nope [l](tickets.md#nope) see tickets.md.\n";
    let found = doc006(&[("docs/tickets.md", TICKETS), ("docs/a.md", text)]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests doc006
#[test]
fn generated_and_historical_pages_are_not_checked() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        (
            "docs/old.md",
            "# Old\n\nStatus: historical\n\ntickets.md section 6\n",
        ),
    ]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests doc006
#[test]
fn citation_moved_through_the_map_is_followed() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        (
            "docs/MOVED.toml",
            "[moved]\n\"old.md\" = \"tickets.md\"\n\"tickets.md section 6\" = \"tickets.md section 2\"\n\"gone.md\" = \"removed:superseded\"\n",
        ),
        (
            "docs/a.md",
            "# A\n\nold.md section 1, tickets.md section 6, gone.md#x.\n",
        ),
    ]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests doc006
#[test]
fn map_row_with_a_missing_target_is_reported() {
    let found = doc006(&[
        ("docs/tickets.md", TICKETS),
        ("docs/MOVED.toml", "[moved]\n\"old.md\" = \"nowhere.md\"\n"),
        ("docs/a.md", "# A\n\nold.md section 1.\n"),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("nowhere.md section 1"),
        "{}",
        found[0].message
    );
}

// frob:tests doc006
#[test]
fn unparsable_map_is_one_finding_and_missing_map_is_fine() {
    let found = doc006(&[("docs/MOVED.toml", "[moved\n")]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(doc006(&[("docs/a.md", "# A\n")]).is_empty());
}
