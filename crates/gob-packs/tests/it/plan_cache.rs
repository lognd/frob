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

/// Load the plan entry keyed `[key; 32]` under engine `eng`, compiling (and counting) on a miss.
fn load(cache: &PlanCache, n: &Cell<u32>, key: u8, eng: &str) -> gob_packs::Loaded {
    cache
        .load_or_compile(&[key; 32], eng, || compile(n))
        .unwrap()
}

// frob:tests load_or_compile
#[test]
fn a_pack_loaded_twice_is_read_from_the_cache_not_recompiled() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("grimble").join("state");
    let cache = PlanCache::open_at(root.clone(), MachineKey::from_bytes([1; 32]), None).unwrap();
    let n = Cell::new(0);
    let first = load(&cache, &n, 9, "eng");
    assert_eq!(first.source, Source::Compiled);
    let second = load(&cache, &n, 9, "eng");
    assert_eq!(second.source, Source::Cache);
    assert_eq!(n.get(), 1);
    assert_eq!(first.plans, second.plans);
    assert!(root.join("plans").is_dir());
    // A different engine fingerprint is a different entry.
    let third = load(&cache, &n, 9, "eng2");
    assert_eq!(third.source, Source::Compiled);
}

// frob:tests load_or_compile
#[test]
fn an_entry_with_an_invalid_mac_is_discarded_and_rebuilt() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().join("state");
    let cache = PlanCache::open_at(root.clone(), MachineKey::from_bytes([1; 32]), None).unwrap();
    let n = Cell::new(0);
    load(&cache, &n, 3, "eng");
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
    let again = load(&cache, &n, 3, "eng");
    assert_eq!(again.source, Source::Compiled);
    assert_eq!(n.get(), 2);
    let healed = load(&cache, &n, 3, "eng");
    assert_eq!(healed.source, Source::Cache);
}

// frob:tests crates/gob-packs/src/plan_cache.rs::PlanCache.open_default
#[test]
fn the_default_cache_opens_in_the_per_user_state_directory() {
    let tree = tempfile::tempdir().unwrap();
    assert!(PlanCache::open_default(Some(tree.path())).is_ok());
}
