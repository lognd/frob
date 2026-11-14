//! Free helpers of `crunk-query`: kind words and close-match ranking.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use crunk_query::{close_matches, kind_word};
use crunk_tokens::TokenKind;

// frob:tests crates/crunk-query/src/lib.rs::kind_word
#[test]
fn kind_word_is_kebab_case() {
    assert_eq!(kind_word(TokenKind::Color), "color");
    assert_eq!(kind_word(TokenKind::FontSize), "font-size");
}

// frob:tests crates/crunk-query/src/lib.rs::close_matches
#[test]
fn close_matches_prefers_substrings_and_drops_far_names() {
    let names = ["color-ink", "color-accent", "space-4", "zzzzzzzzzz"];
    let got = close_matches("color-ink", names.iter().copied());
    assert_eq!(got.first().map(String::as_str), Some("color-ink"));
    assert!(!got.iter().any(|n| n == "zzzzzzzzzz"));
}
