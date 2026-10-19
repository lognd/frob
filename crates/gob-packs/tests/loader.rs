//! Repository pack loader: tiers 1 and 2 load with provenance and a verified lock; tier 3 is refused.

// frob:ticket 01M3ZX7K7BN0CEADJFMCTGEA64

use std::path::{Path, PathBuf};

use gob_packs::loader::{LoadOptions, inspect_pack, load_pack};
use gob_packs::lock::Lock;

const GRL: &str = "rule LDR001 \"t\" {\n  lang rust\n  find c: call\n  report c \"x\"\n  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n}\n";

fn pack(root: &Path, name: &str, manifest_extra: &str, atom: &str) -> PathBuf {
    let dir = root.join("packs").join(name);
    std::fs::create_dir_all(dir.join("rules")).unwrap();
    std::fs::write(
        dir.join("pack.toml"),
        format!(
            "[pack]\nname = \"{name}\"\nversion = \"1.0.0\"\nfamilies = [\"LDR\"]\n\n[provides]\natoms = \"atoms.toml\"\nrules = [\"rules/*.grl\"]\n{manifest_extra}\n[effects]\n"
        ),
    )
    .unwrap();
    std::fs::write(
        dir.join("atoms.toml"),
        format!("format = 1\n[[atom]]\nname = \"{atom}\"\ndoc = \"d\"\n"),
    )
    .unwrap();
    std::fs::write(dir.join("rules/a.grl"), GRL).unwrap();
    dir
}

// frob:tests crates/gob-packs/src/loader/mod.rs::load_pack
#[test]
fn tier1_and_tier2_load_with_repo_provenance_and_a_verified_lock() {
    let d = tempfile::tempdir().unwrap();
    let dir = pack(d.path(), "ldr-safety", "", "ldrsafety.send");
    let probe = inspect_pack(&dir, &LoadOptions::default()).unwrap();
    assert!(!probe.lock_verified);
    assert!(
        gob_ir::registry::atom("ldrsafety.send").is_none(),
        "inspect registers nothing"
    );
    let lock = Lock::new(vec![probe.locked]);
    let opts = LoadOptions {
        lock: Some(&lock),
        cache: None,
    };
    let l = load_pack(&dir, &opts).unwrap();
    assert_eq!(l.provenance, "repo:packs/ldr-safety");
    assert!(l.lock_verified, "{:?}", l.findings);
    assert_eq!(l.plans.len(), 1);
    assert_eq!(l.plans[0].rule(), "LDR001");
    assert!(l.unavailable.is_empty());
    assert_eq!(
        gob_ir::registry::atom_owner("ldrsafety.send").as_deref(),
        Some("ldr-safety")
    );
}

// frob:tests crates/gob-packs/src/loader/mod.rs::inspect_pack
#[test]
fn a_changed_rule_file_or_an_unlocked_pack_fails_verification() {
    let d = tempfile::tempdir().unwrap();
    let dir = pack(d.path(), "ldr-locked", "", "ldrlocked.send");
    let probe = inspect_pack(&dir, &LoadOptions::default()).unwrap();
    let lock = Lock::new(vec![probe.locked]);
    let opts = LoadOptions {
        lock: Some(&lock),
        cache: None,
    };
    assert!(inspect_pack(&dir, &opts).unwrap().lock_verified);
    std::fs::write(dir.join("rules/a.grl"), format!("{GRL}\n")).unwrap();
    let changed = inspect_pack(&dir, &opts).unwrap();
    assert!(!changed.lock_verified);
    assert_eq!(changed.findings[0].code(), "PACK001");

    let other = pack(d.path(), "ldr-other", "", "ldrother.send");
    let missing = inspect_pack(&other, &opts).unwrap();
    assert!(!missing.lock_verified);
    assert_eq!(missing.findings.len(), 1);
}

// frob:tests crates/gob-packs/src/loader/mod.rs::load_pack
#[test]
fn tier3_wasm_is_unresolved_pack_unavailable_with_the_reason() {
    let d = tempfile::tempdir().unwrap();
    let dir = pack(
        d.path(),
        "ldr-wasm",
        "wasm = [\"x.wasm\"]\n",
        "ldrwasm.send",
    );
    std::fs::write(dir.join("x.wasm"), b"\0asm").unwrap();
    let l = load_pack(&dir, &LoadOptions::default()).unwrap();
    assert_eq!(l.unavailable.len(), 1);
    let u = &l.unavailable[0];
    assert_eq!(u.code(), "PACK006");
    assert_eq!(u.reason_code(), "pack-unavailable");
    assert_eq!(u.components, ["x.wasm"]);
    assert_eq!(u.families, ["LDR"]);
    assert!(u.reason.contains("trust"), "{}", u.reason);
}

// frob:tests crates/gob-packs/src/loader/mod.rs::load_pack
// frob:tests crates/gob-packs/src/loader/mod.rs::LoadError.code
#[test]
fn a_failure_registers_nothing_and_a_missing_rule_file_is_pack005() {
    let d = tempfile::tempdir().unwrap();
    let dir = pack(d.path(), "ldr-bad", "", "ldrbad.send");
    std::fs::remove_file(dir.join("rules/a.grl")).unwrap();
    let e = load_pack(&dir, &LoadOptions::default()).unwrap_err();
    assert_eq!(e.code().as_str(), "PACK005");
    assert!(gob_ir::registry::atom("ldrbad.send").is_none());

    let d = tempfile::tempdir().unwrap();
    let dir = pack(d.path(), "ldr-name", "", "ldrname.send");
    let moved = dir.with_file_name("other-dir");
    std::fs::rename(&dir, &moved).unwrap();
    let e = load_pack(&moved, &LoadOptions::default()).unwrap_err();
    assert!(e.to_string().contains("directory name"), "{e}");
    assert_eq!(e.code().as_str(), "PACK005");
}
