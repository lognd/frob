//! Fuzz the directive scanner and its wire codec: no panic, and records round-trip.
// frob:ticket 01M47QV3BRRZZSMJ5Q79N8G5S2
#![no_main]

use gob_directives::{ScanConfig, Scanner, decode_records, encode_records};
use gob_languages::Language;
use gob_symbols::extract_file;
use gob_text::FileInterner;
use gob_walk::{Digest, FileEntry, LanguageHint};
use libfuzzer_sys::fuzz_target;

const PATH: &str = "fuzz.rs";

fuzz_target!(|text: &str| {
    let entry = FileEntry {
        path: PATH.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(PATH),
    };
    let symbols = extract_file(&entry, text);
    let scanner = Scanner::new(&ScanConfig::default());
    let result = scanner.scan(Language::Rust, text, &symbols);

    let file = FileInterner::new().intern(PATH);
    if let Some(bytes) = encode_records(&result.directives) {
        let back = decode_records(&bytes, file).expect("encoded records must decode");
        assert_eq!(
            back.len(),
            result.directives.len(),
            "wire round trip keeps every record"
        );
    }
});
