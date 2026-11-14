//! Snapshot tests over the inline parser cases extracted into `resources/inline/{ok,err}`.
//!
//! The cases are written as `test_ok NAME` / `test_err NAME` comment blocks in the parser source
//! and extracted by `cargo dev gen inline`; GEN001 keeps the extraction current.

// frob:ticket 01M47QTW8CA2FD3BQTH2GG2KXR

use std::path::Path;

/// Fewest cases each outcome must carry.
const MIN_CASES: usize = 5;

/// Every `(name, text)` under `resources/inline/<outcome>`, sorted by name.
fn cases(outcome: &str) -> Vec<(String, String)> {
    gob_testsupport::inline_cases(env!("CARGO_MANIFEST_DIR"), outcome)
}

/// Parse `text` as a `crunk.toml`, returning the dump and whether it was valid.
fn run(text: &str) -> (String, bool) {
    let result = crunk_spec::parse_spec(text, Path::new("crunk.toml"), Path::new("/proj"));
    (format!("{result:#?}"), result.is_ok())
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
