//! Pack lock: pin, round-trip and verify (ticket BHQH7ET).

// frob:ticket 01M3ZX7FTSKACE9TE7MBHQH7ET

use std::fs;

use gob_packs::lock::{self, ItemChange, Lock, LockFinding, LockedPack};
use gob_packs::{Manifest, tier1, tree_digest};

const MANIFEST: &str = "[pack]\nname = \"lk\"\nversion = \"1.0.0\"\nfamilies = [\"LKX\"]\n\n[provides]\natoms = \"atoms.toml\"\n\n[effects]\n";
const ATOMS: &str = "format = 1\n[[atom]]\nname = \"lkpack.go\"\ndoc = \"go\"\n[[vocab]]\nlang = \"rust\"\nclass = \"lkpack\"\nnames = [\"B\", \"A\"]\n";

fn live(dir: &std::path::Path) -> LockedPack {
    let m = Manifest::parse("pack.toml", MANIFEST).unwrap();
    let text = fs::read_to_string(dir.join("atoms.toml")).unwrap();
    let c = tier1::parse("lk", "atoms.toml", &text, None).unwrap();
    let t = tree_digest(dir, &[]).unwrap();
    lock::snapshot(&m, Some(&c), &t)
}

fn pack_dir() -> tempfile::TempDir {
    let d = tempfile::tempdir().unwrap();
    fs::write(d.path().join("pack.toml"), MANIFEST).unwrap();
    fs::write(d.path().join("atoms.toml"), ATOMS).unwrap();
    fs::write(d.path().join("README.md"), "docs v1").unwrap();
    d
}

// frob:tests verify
#[test]
fn doc_only_edit_changes_tree_not_items() {
    let d = pack_dir();
    let before = live(d.path());
    let l = Lock::new(vec![before.clone()]);
    assert!(lock::verify(&l, std::slice::from_ref(&before)).is_empty());
    fs::write(d.path().join("README.md"), "docs v2").unwrap();
    let after = live(d.path());
    assert_eq!(before.items, after.items);
    assert_ne!(before.tree, after.tree);
    let f = lock::verify(&l, &[after]);
    assert_eq!(f.len(), 1);
    assert!(matches!(f[0], LockFinding::TreeOnly { .. }));
}

// frob:tests verify
#[test]
fn missing_and_stale_are_typed_pack001() {
    let d = pack_dir();
    let p = live(d.path());
    let empty = Lock::new(vec![]);
    let f = lock::verify(&empty, std::slice::from_ref(&p));
    assert_eq!(f, vec![LockFinding::LockMissing { name: "lk".into() }]);
    assert_eq!(f[0].code(), "PACK001");
    let f = lock::verify(&Lock::new(vec![p]), &[]);
    assert_eq!(f, vec![LockFinding::LockStale { name: "lk".into() }]);
}

// frob:tests verify
#[test]
fn semantic_change_reports_item_and_scheme() {
    let d = pack_dir();
    let p = live(d.path());
    let mut changed = p.clone();
    changed
        .items
        .insert("atom:lkpack.go".into(), "blake3:00".into());
    changed.items.insert("atom:new".into(), "blake3:01".into());
    let f = lock::verify(&Lock::new(vec![p.clone()]), &[changed]);
    assert!(f.iter().any(|x| matches!(
        x,
        LockFinding::Item {
            change: ItemChange::Changed,
            without_version_bump: true,
            ..
        }
    )));
    assert!(f.iter().any(|x| matches!(
        x,
        LockFinding::Item {
            change: ItemChange::Added,
            ..
        }
    )));
    let mut l = Lock::new(vec![p]);
    l.digest_scheme = 99;
    assert!(matches!(
        lock::verify(&l, &[])[0],
        LockFinding::Scheme { .. }
    ));
}

// frob:tests write
// frob:tests read
#[test]
fn write_read_round_trip() {
    let d = pack_dir();
    let l = Lock::new(vec![live(d.path())]);
    let out = d.path().join("x.lock");
    lock::write(&out, &l).unwrap();
    assert_eq!(lock::read(&out).unwrap(), l);
    fs::write(&out, "bogus = 1").unwrap();
    assert!(lock::read(&out).is_err());
}

// frob:tests snapshot
#[test]
fn vocab_names_are_a_set() {
    let d = pack_dir();
    let a = live(d.path());
    fs::write(
        d.path().join("atoms.toml"),
        ATOMS.replace("[\"B\", \"A\"]", "[\"A\", \"B\", \"A\"]"),
    )
    .unwrap();
    assert_eq!(a.items, live(d.path()).items);
}
