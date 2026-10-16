//! COH004 verdicts over disjoint-vocabulary and single-vocabulary fixtures.

// frob:ticket 01M4CXSTHZXVBMWSTRCBH9BHQ5

#![allow(unused_crate_dependencies)]

use gob_ir::{NodeId, Operator, Universal};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh004::{Coh004, Coh004Options, coh004, split_words};

fn verdict(path: &str, text: &str) -> Coh004 {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    let folded = fold_file(&entry, text).expect("fold");
    let unit: NodeId = folded
        .term
        .ids()
        .find(|&i| {
            matches!(folded.term.node(i).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
                && folded.term.node(i).name() == Some("f")
        })
        .expect("function f");
    coh004(&folded.term, unit, &Coh004Options::default())
}

fn assert_fire(v: Coh004) {
    let Coh004::Advisory { clusters } = v else {
        panic!("expected Advisory, got {v:?}")
    };
    assert_eq!(clusters.len(), 2, "{clusters:?}");
    let has = |w: &str| clusters.iter().position(|c| c.iter().any(|x| x == w));
    assert_ne!(has("invoice"), has("packet"));
    assert!(has("invoice").is_some() && has("packet").is_some());
}

// frob:tests crates/grimble-check/src/coh004.rs::coh004
#[test]
fn coh004_python_fire() {
    assert_fire(verdict("fire.py", include_str!("fixtures/coh004/fire.py")));
}

// frob:tests crates/grimble-check/src/coh004.rs::coh004
#[test]
fn coh004_python_clean() {
    assert_eq!(
        verdict("clean.py", include_str!("fixtures/coh004/clean.py")),
        Coh004::Clean
    );
}

// frob:tests crates/grimble-check/src/coh004.rs::coh004
#[test]
fn coh004_rust_fire() {
    assert_fire(verdict("fire.rs", include_str!("fixtures/coh004/fire.rs")));
}

// frob:tests crates/grimble-check/src/coh004.rs::coh004
#[test]
fn coh004_rust_clean() {
    assert_eq!(
        verdict("clean.rs", include_str!("fixtures/coh004/clean.rs")),
        Coh004::Clean
    );
}

// frob:tests crates/grimble-check/src/coh004.rs::split_words
#[test]
fn split_words_handles_snake_and_camel() {
    assert_eq!(
        split_words("read_packet_buffer"),
        ["read", "packet", "buffer"]
    );
    assert_eq!(split_words("invoiceTotal"), ["invoice", "total"]);
    assert_eq!(split_words("HTTPServer"), ["http", "server"]);
}
