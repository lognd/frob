//! Token lint helpers: naming, mode gaps, usage, scopes, near-duplicates and `deprecated`.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use std::collections::BTreeSet;

use crunk_tokens::Scope;
use crunk_tokens::dialect::parse;
use crunk_tokens::lint;

const SOURCE: &str = r##"
[color]
ink = "#101010"
near-ink = "#111111"
BadName = "#ff0000"
paper = { value = "#ffffff", modes = { dark = "#000000" } }
old = { value = "#abcdef", deprecated = "use color.ink" }

[space]
4 = { value = "4px", scopes = ["spacing"] }
"##;

// frob:tests crates/crunk-tokens/src/lint.rs::is_kebab
#[test]
fn kebab_segments_are_lowercase_words() {
    assert!(lint::is_kebab("on-surface-2"));
    assert!(!lint::is_kebab("BadName"));
    assert!(!lint::is_kebab("a--b"));
    assert!(!lint::is_kebab(""));
}

// frob:tests crates/crunk-tokens/src/lint.rs::naming_issues
// frob:tests crates/crunk-tokens/src/lint.rs::naming_issue
#[test]
fn naming_flags_only_the_bad_path() {
    let set = parse(SOURCE, "t.toml").unwrap();
    let bad = lint::naming_issues(&set);
    assert_eq!(bad.len(), 1);
    assert!(bad[0].1.contains("BadName"));
}

// frob:tests crates/crunk-tokens/src/lint.rs::mode_gaps
#[test]
fn a_partial_mode_override_is_a_gap() {
    let set = parse(SOURCE, "t.toml").unwrap();
    // `paper` overrides dark and is the only override: nothing is missing.
    assert!(lint::mode_gaps(&set).is_empty());
}

// frob:tests crates/crunk-tokens/src/lint.rs::unused
#[test]
fn unused_lists_tokens_nothing_reads() {
    let set = parse(SOURCE, "t.toml").unwrap();
    let used: BTreeSet<String> = ["--color-ink".to_owned()].into();
    let names: Vec<&str> = lint::unused(&set, &used)
        .iter()
        .map(|t| t.key.as_str())
        .collect();
    assert!(!names.contains(&"color.ink"));
    assert!(names.contains(&"color.paper"));
}

// frob:tests crates/crunk-tokens/src/lint.rs::near_duplicates
#[test]
fn near_duplicates_pairs_close_literals() {
    let set = parse(SOURCE, "t.toml").unwrap();
    let pairs = lint::near_duplicates(&set, 5.0);
    assert!(pairs.iter().any(|(a, b)| {
        let keys = [a.key.as_str(), b.key.as_str()];
        keys.contains(&"color.ink") && keys.contains(&"color.near-ink")
    }));
}

// frob:tests crates/crunk-tokens/src/lint.rs::scope_of_property
// frob:tests crates/crunk-tokens/src/lint.rs::allows_scope
#[test]
fn scopes_follow_the_bound_property() {
    let set = parse(SOURCE, "t.toml").unwrap();
    assert_eq!(lint::scope_of_property("margin-top"), Some(Scope::Spacing));
    assert_eq!(lint::scope_of_property("color"), Some(Scope::Color));
    assert_eq!(lint::scope_of_property("display"), None);
    let space = set.get("--space-4").unwrap();
    assert!(lint::allows_scope(space, Scope::Spacing));
    assert!(!lint::allows_scope(space, Scope::Color));
    assert!(lint::allows_scope(
        set.get("--color-ink").unwrap(),
        Scope::Color
    ));
}

// frob:tests crates/crunk-tokens/src/lint.rs::offset_of
#[test]
fn offset_of_finds_the_defining_line() {
    let at = lint::offset_of(SOURCE, "color.near-ink");
    assert!(SOURCE[at..].trim_start().starts_with("near-ink"));
    assert_eq!(lint::offset_of(SOURCE, "no.such"), 0);
}

// frob:tests crates/crunk-tokens/src/dialect.rs::parse
#[test]
fn deprecated_is_read_as_a_string() {
    let set = parse(SOURCE, "t.toml").unwrap();
    assert_eq!(
        set.get("--color-old").unwrap().deprecated.as_deref(),
        Some("use color.ink")
    );
    assert!(parse("[a]\nb = { value = \"1px\", deprecated = 3 }", "t.toml").is_err());
}
