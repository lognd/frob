//! Snapshot tests over the inline parser cases extracted into `resources/inline/{ok,err}`.
//!
//! The cases are written as `test_ok NAME` / `test_err NAME` comment blocks in the parser source
//! and extracted by `cargo dev gen inline`; GEN001 keeps the extraction current.

#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

// frob:ticket 01M47QTW8CA2FD3BQTH2GG2KXR

use std::path::{Path, PathBuf};

/// Fewest cases each outcome must carry.
const MIN_CASES: usize = 5;

/// Every `(name, text)` under `resources/inline/<outcome>`, sorted by name.
fn cases(outcome: &str) -> Vec<(String, String)> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("resources/inline")
        .join(outcome);
    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("read {}: {e}", dir.to_string_lossy()))
        .map(|e| e.expect("dir entry").path())
        .collect();
    paths.sort();
    paths
        .into_iter()
        .map(|p| {
            let name = p
                .file_stem()
                .and_then(|s| s.to_str())
                .expect("stem")
                .to_owned();
            let text = std::fs::read_to_string(&p).expect("read case");
            (name, text)
        })
        .collect()
}

/// Scan `text` as a Rust file, returning the dump and whether it was clean.
fn run(text: &str) -> (String, bool) {
    let path = "src/a.rs";
    let entry = gob_walk::FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: gob_walk::Digest::of(text.as_bytes()),
        language: gob_walk::LanguageHint::from_path(path),
    };
    let syms = gob_symbols::extract_file(&entry, text);
    let lang = gob_languages::Language::detect(path).expect("rust");
    let cfg = gob_directives::ScanConfig::default();
    let result = gob_directives::Scanner::new(&cfg).scan(lang, text, &syms);
    (format!("{result:#?}"), result.findings.is_empty())
}

/// Every `ok` case parses cleanly and matches its snapshot.
// frob:tests run
#[test]
fn ok_cases_parse_cleanly() {
    let all = cases("ok");
    assert!(
        all.len() >= MIN_CASES,
        "need {MIN_CASES} ok cases, found {}",
        all.len()
    );
    for (name, text) in all {
        let (dump, clean) = run(&text);
        assert!(clean, "ok case {name} reported errors:\n{dump}");
        insta::assert_snapshot!(format!("ok_{name}"), dump);
    }
}

/// Every `err` case reports errors and matches its snapshot.
// frob:tests run
#[test]
fn err_cases_report_errors() {
    let all = cases("err");
    assert!(
        all.len() >= MIN_CASES,
        "need {MIN_CASES} err cases, found {}",
        all.len()
    );
    for (name, text) in all {
        let (dump, clean) = run(&text);
        assert!(!clean, "err case {name} parsed cleanly:\n{dump}");
        insta::assert_snapshot!(format!("err_{name}"), dump);
    }
}
