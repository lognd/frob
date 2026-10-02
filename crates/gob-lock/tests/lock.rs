//! Round trip, atomic save, missing file and diff behavior of `gob-lock`.

use gob_lock::{Facet, LockEntry, LockFile, LockTarget, diff, file_name};

fn entry(sig: &str) -> LockEntry {
    LockEntry::new(sig, "b", "d", "Me <me@example.com>", "2026-10-02T00:00:00Z")
}

#[test]
fn file_name_is_product_dot_lock() {
    assert_eq!(file_name("frob"), "frob.lock");
    assert_eq!(file_name("grimble"), "grimble.lock");
}

#[test]
fn save_load_round_trips_and_is_sorted_and_stable() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("frob.lock");
    let mut lock = LockFile::default();
    lock.entries.insert("z.rs::z".to_owned(), entry("1"));
    let mut a = entry("2");
    a.reason = Some("reviewed the contract".to_owned());
    a.targets.push(LockTarget {
        target: "docs/a.md#intro".to_owned(),
        digest: "ff".to_owned(),
    });
    lock.entries.insert("a.rs::a".to_owned(), a);
    lock.save(&path).unwrap();
    let first = std::fs::read_to_string(&path).unwrap();
    assert!(first.find("a.rs::a").unwrap() < first.find("z.rs::z").unwrap());
    assert!(first.ends_with('\n'));
    let back = LockFile::load(&path).unwrap();
    assert_eq!(back, lock);
    back.save(&path).unwrap();
    assert_eq!(std::fs::read_to_string(&path).unwrap(), first);
    assert!(!dir.path().join("frob.lock.tmp").exists());
}

#[test]
fn missing_file_is_empty_and_garbage_is_an_error() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("frob.lock");
    assert!(LockFile::load(&path).unwrap().entries.is_empty());
    std::fs::write(&path, "not = [toml").unwrap();
    assert!(LockFile::load(&path).is_err());
    std::fs::write(&path, "version = 99\n").unwrap();
    assert!(LockFile::load(&path).is_err());
}

#[test]
fn diff_reports_added_removed_and_changed_facets() {
    let mut old = LockFile::default();
    old.entries.insert("a".to_owned(), entry("1"));
    old.entries.insert("gone".to_owned(), entry("1"));
    let mut new = old.clone();
    new.entries.remove("gone");
    new.entries.insert("new".to_owned(), entry("1"));
    new.entries.get_mut("a").unwrap().sig = "2".to_owned();
    let d = diff(&old, &new);
    assert_eq!(d.added, ["new"]);
    assert_eq!(d.removed, ["gone"]);
    assert_eq!(d.changed, [("a".to_owned(), vec![Facet::Sig])]);
    assert!(diff(&new, &new).is_empty());
}
