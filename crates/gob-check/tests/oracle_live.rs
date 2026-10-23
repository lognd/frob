//! The committed `observed` column equals what the real adapters answer now (testing.md section 8).

#![allow(
    clippy::disallowed_methods,
    reason = "a test reads and blesses a committed fixture, not a walked snapshot"
)]

use std::path::PathBuf;

use gob_check::incompleteness::parse_corpus;
use gob_check::incompleteness_live::{diff_column, live_column, rewrite_observed};

fn corpus_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/incompleteness")
        .join("oracle-corpus.toml")
}

// frob:tests crates/gob-check/src/incompleteness_live.rs::live_column
// frob:tests crates/gob-check/src/incompleteness_live.rs::live_verdict
#[test]
fn the_real_adapters_answer_every_corpus_case() {
    let cases = parse_corpus(&std::fs::read_to_string(corpus_path()).expect("read corpus"))
        .expect("corpus parses");
    let live = live_column(&cases).expect("every case has a probe an adapter can read");
    assert_eq!(live.len(), cases.len());
    let ids: Vec<&str> = live.iter().map(|(i, _)| i.as_str()).collect();
    let want: Vec<&str> = cases.iter().map(|c| c.id.as_str()).collect();
    assert_eq!(ids, want, "live answers keep corpus order");
}

// frob:tests crates/gob-check/src/incompleteness_live.rs::diff_column
// frob:tests crates/gob-check/src/incompleteness_live.rs::rewrite_observed
#[test]
fn committed_observed_column_matches_the_live_adapter_answers() {
    let path = corpus_path();
    let text = std::fs::read_to_string(&path).expect("read corpus");
    let cases = parse_corpus(&text).expect("corpus parses");
    let live = live_column(&cases).expect("live column");
    if std::env::var_os("FROB_BLESS_ORACLE").is_some() {
        std::fs::write(&path, rewrite_observed(&text, &live)).expect("bless corpus");
        return;
    }
    let diff = diff_column(&cases, &live);
    assert!(
        diff.is_empty(),
        "committed observed differs from live adapter answers (FROB_BLESS_ORACLE=1 rewrites the column; then refresh baseline.toml deliberately): {diff:#?}"
    );
}
