#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! PACK001 over the embedded core-effects pack: `grimble.packs.lock` drift is a finding.

// frob:ticket 8K6G441

use std::path::Path;

use gob_packs::core_effects;
use gob_packs::lock::{Lock, write};
use grimble_check::pack_pass::{LOCK_FILE, analyze};
use grimble_check::packs::LoadedPacks;

// frob:tests crates/grimble-check/src/pack_pass.rs::analyze
#[test]
fn no_lock_file_means_no_pack001() {
    let dir = tempfile::tempdir().unwrap();
    let r = analyze(dir.path(), &LoadedPacks::default(), 0);
    assert!(r.findings.is_empty());
    assert!(!r.subjects.contains_key("PACK001"));
}

fn lock_with(dir: &Path, mutate: impl FnOnce(&mut Lock)) {
    let mut lock = Lock::new(vec![core_effects::locked().unwrap()]);
    mutate(&mut lock);
    write(&dir.join(LOCK_FILE), &lock).unwrap();
}

// frob:tests crates/grimble-check/src/pack_pass.rs::analyze
#[test]
fn a_matching_core_effects_lock_is_clean() {
    let dir = tempfile::tempdir().unwrap();
    lock_with(dir.path(), |_| {});
    let r = analyze(dir.path(), &LoadedPacks::default(), 0);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    assert_eq!(r.subjects.get("PACK001"), Some(&1));
}

// frob:tests crates/grimble-check/src/pack_pass.rs::analyze
#[test]
fn a_drifted_core_effects_lock_is_pack001() {
    let dir = tempfile::tempdir().unwrap();
    lock_with(dir.path(), |l| {
        l.pack[0]
            .items
            .insert("atom:bogus.extra".to_owned(), "blake3:00".to_owned());
    });
    let r = analyze(dir.path(), &LoadedPacks::default(), 0);
    assert!(!r.findings.is_empty());
    assert!(r.findings.iter().all(|f| f.rule.as_str() == "PACK001"));
}

// frob:tests crates/grimble-check/src/pack_pass.rs::analyze
#[test]
fn other_packs_in_the_lock_are_not_reported_stale() {
    let dir = tempfile::tempdir().unwrap();
    lock_with(dir.path(), |l| {
        let mut other = l.pack[0].clone();
        other.name = "other".to_owned();
        l.pack.push(other);
    });
    let r = analyze(dir.path(), &LoadedPacks::default(), 0);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
}
