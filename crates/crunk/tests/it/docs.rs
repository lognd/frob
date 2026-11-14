//! The crunk product docs stay true to the binary: every crunk verb is in the README table and the
//! migration guide, and the pages are ASCII with no absolute home paths.

// frob:ticket 01M43AVMAY5VB8K1885CDYEYV6
// frob:ticket 01M4H0XB30TVD3TW813XPA3A54

use std::path::PathBuf;

fn docs_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../docs")
}

/// The crunk pages: the user guide and the two migration pages.
const PAGES: [&str; 3] = [
    "guides/crunk.md",
    "guides/crunk-from-python.md",
    "guides/crunk-hullbreach.md",
];

fn page(name: &str) -> String {
    std::fs::read_to_string(docs_dir().join(name)).unwrap_or_else(|e| panic!("{name}: {e}"))
}

/// The verbs `crunk` registers itself, with the shared ones every goblin binary carries.
fn crunk_verbs() -> Vec<&'static str> {
    // Touch the library so its `register_commands!` inventory is linked into this test.
    std::hint::black_box(crunk::cli());
    gob_cli::all_commands()
        .filter(|m| m.product == "crunk" && m.deprecated_form().is_none())
        .map(|m| m.verb)
        .collect()
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn every_crunk_verb_is_in_the_readme_verb_table() {
    let readme = page("guides/crunk.md");
    let verbs = crunk_verbs();
    assert!(!verbs.is_empty(), "no crunk verbs registered");
    for verb in verbs {
        // `schema` and `serve` are shared built-ins described by the global flags, not the table.
        if matches!(verb, "schema" | "serve") {
            continue;
        }
        assert!(
            readme.contains(&format!("`crunk {verb}")),
            "guides/crunk.md has no row for `crunk {verb}`"
        );
    }
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn the_migration_guide_states_a_rust_verb_or_removal_for_every_python_verb() {
    let guide = page("guides/crunk-from-python.md");
    // The Python verbs recorded in tests/crunk-parity (PROVENANCE).
    for python in [
        "crunk check --report",
        "crunk check --contrast",
        "crunk check --config",
        "crunk tokens --format css",
        "crunk init",
        "crunk query",
        "crunk map",
        "crunk explain",
        "crunk preview",
        "crunk diff",
        "crunk fix",
        "crunk cache ls",
        "crunk cache prune",
    ] {
        let row = guide
            .lines()
            .find(|l| l.starts_with("| `") && l.contains(python))
            .unwrap_or_else(|| panic!("python-crunk.md has no row for `{python}`"));
        assert!(
            row.matches('|').count() >= 4,
            "row is not a full table row: {row}"
        );
    }
}

#[test]
fn the_crunk_pages_are_ascii_and_free_of_home_paths() {
    for name in PAGES {
        let text = page(name);
        assert!(text.is_ascii(), "{name} is not ASCII");
        assert!(!text.contains("/home/"), "{name} has a home path");
    }
}
