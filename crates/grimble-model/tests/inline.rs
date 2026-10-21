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

/// Parse `text` as a .grmb file, returning the dump and whether it was clean.
fn run(text: &str) -> (String, bool) {
    let parsed = grimble_model::parse::parse_file("x.grmb", text.as_bytes());
    (format!("{parsed:#?}"), parsed.diags.is_empty())
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
