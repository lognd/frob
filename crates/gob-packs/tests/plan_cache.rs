//! Plan cache: second load is served from cache; a tampered entry is rebuilt.

// frob:ticket 01M3ZX7JE252WBVE5DKMJK3JME

use std::cell::Cell;

use gob_packs::{PlanCache, Source};
use gob_plan::lower::lower_source;
use gob_trust::MachineKey;

const GRL: &str = "rule TST001 \"t\" {\n  lang rust\n  find c: call\n  report c \"x\"\n  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n}\n";

fn compile(count: &Cell<u32>) -> Result<Vec<gob_plan::plan::Plan>, String> {
    count.set(count.get() + 1);
    lower_source("rules/T.grl", GRL).map_err(|e| e.to_string())
}

// frob:tests load_or_compile
#[test]
fn a_pack_loaded_twice_is_read_from_the_cache_not_recompiled() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("grimble").join("state");
    let cache = PlanCache::open_at(root.clone(), MachineKey::from_bytes([1; 32]), None).unwrap();
    let n = Cell::new(0);
    let first = cache
        .load_or_compile(&[9; 32], "eng", || compile(&n))
        .unwrap();
    assert_eq!(first.source, Source::Compiled);
    let second = cache
        .load_or_compile(&[9; 32], "eng", || compile(&n))
        .unwrap();
    assert_eq!(second.source, Source::Cache);
    assert_eq!(n.get(), 1);
    assert_eq!(first.plans, second.plans);
    assert!(root.join("plans").is_dir());
    // A different engine fingerprint is a different entry.
    let third = cache
        .load_or_compile(&[9; 32], "eng2", || compile(&n))
        .unwrap();
    assert_eq!(third.source, Source::Compiled);
}

// frob:tests load_or_compile
#[test]
fn an_entry_with_an_invalid_mac_is_discarded_and_rebuilt() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("state");
    let cache = PlanCache::open_at(root.clone(), MachineKey::from_bytes([1; 32]), None).unwrap();
    let n = Cell::new(0);
    cache
        .load_or_compile(&[3; 32], "eng", || compile(&n))
        .unwrap();
    let entry = std::fs::read_dir(root.join("plans"))
        .unwrap()
        .next()
        .unwrap()
        .unwrap()
        .path();
    let mut bytes = std::fs::read(&entry).unwrap();
    let last = bytes.len() - 1;
    bytes[last] ^= 0xff;
    std::fs::write(&entry, bytes).unwrap();
    let again = cache
        .load_or_compile(&[3; 32], "eng", || compile(&n))
        .unwrap();
    assert_eq!(again.source, Source::Compiled);
    assert_eq!(n.get(), 2);
    let healed = cache
        .load_or_compile(&[3; 32], "eng", || compile(&n))
        .unwrap();
    assert_eq!(healed.source, Source::Cache);
}
