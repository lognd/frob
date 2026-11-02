//! The keyword table of `keywords.rs` equals the table of grmb-spec 2.6.

// frob:ticket 01M6BYJWDYKT5B9DCXFA1W814E

use std::collections::BTreeSet;
use std::path::Path;

use grimble_model::keywords::{KEYWORDS, PLANNING_BODY_WORDS, PLANNING_ITEM_WORDS, is_table_word};

/// The backticked words of the 2.6 table row whose first cell starts with `class`.
fn row_words(spec: &str, class: &str) -> BTreeSet<String> {
    let prefix = format!("| {class} |");
    let line = spec
        .lines()
        .find(|l| l.starts_with(&prefix))
        .unwrap_or_else(|| panic!("no 2.6 row `{class}`"));
    let cell = line.split('|').nth(2).expect("words cell");
    let first = cell.split('`').nth(1).expect("backticked word list");
    first.split_whitespace().map(str::to_owned).collect()
}

fn spec() -> String {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/design/grimble/grmb-spec.md");
    std::fs::read_to_string(p).expect("grmb-spec.md")
}

// frob:tests crates/grimble-model/src/keywords.rs::KEYWORDS
#[test]
fn reserved_words_equal_the_spec_row() {
    let ours: Vec<&str> = KEYWORDS.to_vec();
    let set: BTreeSet<String> = ours.iter().map(|s| (*s).to_owned()).collect();
    assert_eq!(ours.len(), set.len(), "KEYWORDS has a duplicate");
    assert_eq!(set, row_words(&spec(), "reserved"));
}

// frob:tests crates/grimble-model/src/keywords.rs::PLANNING_BODY_WORDS
#[test]
fn planning_words_equal_the_spec_row() {
    let ours: BTreeSet<String> = PLANNING_BODY_WORDS
        .iter()
        .map(|s| (*s).to_owned())
        .collect();
    assert_eq!(
        ours.len(),
        PLANNING_BODY_WORDS.len(),
        "duplicate planning word"
    );
    assert_eq!(ours, row_words(&spec(), "planning word"));
}

// frob:tests crates/grimble-model/src/keywords.rs::PLANNING_ITEM_WORDS
#[test]
fn item_heads_equal_the_spec_row() {
    let spec = spec();
    let line = spec
        .lines()
        .find(|l| l.starts_with("| item head |"))
        .expect("item head row");
    let cell = line.split('|').nth(2).expect("words cell");
    let want: BTreeSet<String> = cell
        .split('`')
        .nth(1)
        .expect("word list")
        .split_whitespace()
        .map(str::to_owned)
        .collect();
    let ours: BTreeSet<String> = PLANNING_ITEM_WORDS
        .iter()
        .map(|s| (*s).to_owned())
        .collect();
    assert_eq!(ours, want);
}

// frob:tests crates/grimble-model/src/keywords.rs::is_table_word
#[test]
fn title_is_deprecated_not_a_table_word_and_chain_is() {
    assert!(!is_table_word("title"));
    assert!(is_table_word("chain"));
    assert!(is_table_word("attests"));
    assert!(!is_table_word("widget"));
}
