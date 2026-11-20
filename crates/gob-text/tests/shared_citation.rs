//! The citation parser lives only in gob-text: `frob doc remap` and DOC006 both call it, and no other crate
//! defines its own copy.

// frob:ticket 01M5NCNPRJE2AFXWKSNFKPR5G3

use std::fs;
use std::path::{Path, PathBuf};

/// The workspace `crates/` directory.
fn crates_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("crates dir")
        .to_path_buf()
}

/// The text of a source file under `crates/`.
fn source(rel: &str) -> String {
    fs::read_to_string(crates_dir().join(rel)).expect("source file")
}

/// Every `.rs` file under `dir`.
fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).expect("read dir").flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_files(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

// frob:tests crates/gob-text/src/citation.rs::scan_markdown
// frob:tests crates/gob-text/src/citation.rs::scan_line
#[test]
fn remap_and_doc006_call_the_shared_parser() {
    for rel in [
        "frob-doc/src/rewrite.rs",
        "frob-obligations/src/doc_citation.rs",
    ] {
        let text = source(rel);
        let uses = text
            .lines()
            .any(|l| l.starts_with("use gob_text::") && l.contains("scan_markdown"));
        assert!(uses, "{rel} must import the shared citation parser");
        assert!(text.contains("scan_line("), "{rel} must call scan_line");
    }
}

// frob:tests crates/gob-text/src/citation.rs::scan_markdown
// frob:tests crates/gob-text/src/citation.rs::scan_line
#[test]
fn no_crate_but_gob_text_defines_a_citation_scanner() {
    let mut files = Vec::new();
    rust_files(&crates_dir(), &mut files);
    for file in files {
        let in_gob_text = file.starts_with(crates_dir().join("gob-text"));
        let in_tests = file.components().any(|c| c.as_os_str() == "tests");
        if in_gob_text || in_tests {
            continue;
        }
        let text = fs::read_to_string(&file).expect("source file");
        let duplicate = text.lines().any(|l| {
            l.starts_with("fn scan_markdown")
                || l.starts_with("pub fn scan_markdown")
                || l.starts_with("fn scan_line")
                || l.starts_with("pub fn scan_line")
                || l.starts_with("pub struct Citation")
                || l.starts_with("struct Citation")
        });
        assert!(!duplicate, "{file:?} duplicates the shared citation parser");
    }
}
