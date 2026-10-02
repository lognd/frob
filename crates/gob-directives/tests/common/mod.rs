//! Shared helpers: real symbol extraction plus the scanner.
#![allow(dead_code, reason = "each test binary uses a subset")]

use gob_directives::{ScanConfig, ScanResult, Scanner};
use gob_languages::Language;
use gob_symbols::{FileSymbols, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// Language of `path` by extension.
pub fn language_of(path: &str) -> Language {
    Language::detect(path).expect("test paths have known extensions")
}

/// Extract symbols for `text` as if it lived at `path`.
pub fn symbols(path: &str, text: &str) -> FileSymbols {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    extract_file(&entry, text)
}

/// Scan `text` at `path` with the default (`frob`) scanner.
pub fn scan(path: &str, text: &str) -> ScanResult {
    scan_with(&ScanConfig::default(), path, text)
}

/// Scan `text` at `path` with `config`.
pub fn scan_with(config: &ScanConfig, path: &str, text: &str) -> ScanResult {
    let syms = symbols(path, text);
    Scanner::new(config).scan(language_of(path), text, &syms)
}
