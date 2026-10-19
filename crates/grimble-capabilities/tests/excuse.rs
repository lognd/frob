//! Excuse, CAP004, output and census tests.

use std::collections::BTreeSet;

use grimble_capabilities::excuse::{Excuse, UseSite, cap004, derive_input};
use grimble_capabilities::output::{census, render};
use grimble_capabilities::{Cell, build};

fn site(atom: &str, file: &str, certain: bool) -> UseSite {
    UseSite {
        atom: atom.into(),
        file: file.into(),
        site: format!("{file}:1 call"),
        certain,
    }
}

fn excuse(atom: &str, file: &str) -> Excuse {
    Excuse {
        atom: atom.into(),
        files: BTreeSet::from([file.to_owned()]),
        because: "legacy".into(),
    }
}

// frob:tests crates/grimble-capabilities/src/excuse.rs::cap004
#[test]
fn excused_use_in_covered_code_is_cap004() {
    let hits = cap004(
        "core",
        &[
            site("net.connect", "a.rs", true),
            site("net.connect", "b.rs", true),
        ],
        &[excuse("net", "a.rs")],
    );
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0].sites, vec!["a.rs:1 call".to_owned()]);
    assert!(hits[0].certain);
}

// frob:tests crates/grimble-capabilities/src/excuse.rs::cap004
#[test]
fn may_use_in_excused_code_is_not_certain() {
    let hits = cap004(
        "core",
        &[site("fs.read", "a.rs", false)],
        &[excuse("fs", "a.rs")],
    );
    assert_eq!(hits.len(), 1);
    assert!(!hits[0].certain);
}

// frob:tests crates/grimble-capabilities/src/excuse.rs::derive_input
#[test]
fn excuse_without_use_is_excused_and_use_still_shows() {
    let files = BTreeSet::from(["a.rs".to_owned()]);
    let ex = [excuse("fs.write", "a.rs")];
    let n = derive_input("core", "rust", &BTreeSet::new(), &[], &ex, &files);
    let m = build(&[n], &["fs.write"]);
    assert_eq!(m.cells["core"]["fs.write"], Cell::Excused);
    let used = [site("fs.write", "a.rs", true)];
    let n = derive_input("core", "rust", &BTreeSet::new(), &used, &ex, &files);
    let m = build(&[n], &["fs.write"]);
    assert_eq!(m.cells["core"]["fs.write"], Cell::Undeclared);
}

// frob:tests crates/grimble-capabilities/src/output.rs::render
// frob:tests crates/grimble-capabilities/src/output.rs::census
#[test]
fn render_skips_denied_and_census_counts() {
    let files = BTreeSet::new();
    let used = [site("net.connect", "a.rs", true)];
    let n = derive_input("core", "rust", &BTreeSet::new(), &used, &[], &files);
    let m = build(&[n], &["net.connect", "fs.write"]);
    assert_eq!(render(&m), "core net.connect undeclared\n");
    let c = census(&m);
    assert_eq!(c[&Cell::Undeclared], 1);
    assert_eq!(c[&Cell::Denied], 1);
}
