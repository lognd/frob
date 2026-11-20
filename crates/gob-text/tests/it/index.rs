//! `LineIndex::text_len` and `SourceText::utf16_col` on text with multi-byte characters.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use gob_text::{LineIndex, SourceText, TextSize};

// frob:tests crates/gob-text/src/line_index.rs::LineIndex.text_len
#[test]
fn text_len_is_the_byte_length() {
    let idx = LineIndex::new("ab\ncd\n").expect("index");
    assert_eq!(idx.text_len(), TextSize::new(6));
}

// frob:tests crates/gob-text/src/source.rs::SourceText.utf16_col
#[test]
fn utf16_col_counts_code_units() {
    let src = SourceText::new("a\u{1F680}b\n").expect("text");
    // 'b' sits after 1 + 4 bytes and 1 + 2 UTF-16 units: column 4 (1-based).
    assert_eq!(src.utf16_col(TextSize::new(5)), Some(4));
    assert_eq!(src.utf16_col(TextSize::new(0)), Some(1));
}

// frob:tests crates/gob-text/src/source.rs::SourceText.len
// frob:tests crates/gob-text/src/source.rs::SourceText.is_empty
#[test]
fn source_text_len_and_emptiness() {
    let s = SourceText::new("abc").expect("text");
    assert_eq!(s.len(), TextSize::new(3));
    assert!(!s.is_empty());
    assert!(SourceText::new("").expect("empty").is_empty());
}

// frob:tests crates/gob-text/src/file.rs::FileInterner.is_empty
#[test]
fn interner_is_empty_until_a_file_is_interned() {
    let mut files = gob_text::FileInterner::new();
    assert!(files.is_empty());
    files.intern("a.rs");
    assert!(!files.is_empty());
}

// frob:tests crates/gob-text/src/size.rs::TextRange.contains
#[test]
fn range_contains_is_half_open() {
    let r = gob_text::TextRange::new(TextSize::new(2), TextSize::new(5));
    assert!(r.contains(TextSize::new(2)));
    assert!(r.contains(TextSize::new(4)));
    assert!(!r.contains(TextSize::new(5)));
    assert!(!r.contains(TextSize::new(1)));
}
