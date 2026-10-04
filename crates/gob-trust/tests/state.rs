//! Acceptance tests for the authenticated state store (~TX6YZZE).

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use gob_trust::{
    Discard, Lookup, MachineKey, StateError, StateStore, TrustError, ci_active, resolve_cache_dir,
};

fn store(dir: &Path, k: u8) -> StateStore {
    StateStore::open_at(dir.join("state"), MachineKey::from_bytes([k; 32]), None).unwrap()
}

fn entry_file(dir: &Path, kind: &str) -> PathBuf {
    fs::read_dir(dir.join("state").join(kind))
        .unwrap()
        .map(|e| e.unwrap().path())
        .find(|p| !p.file_name().unwrap().to_string_lossy().starts_with('.'))
        .unwrap()
}

#[test]
fn round_trip_and_miss() {
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    assert_eq!(s.get("plan", "abc").unwrap(), Lookup::Miss);
    s.put("plan", "abc", b"payload").unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Hit(b"payload".to_vec())
    );
    s.put("plan", "abc", b"").unwrap();
    assert_eq!(s.get("plan", "abc").unwrap(), Lookup::Hit(vec![]));
}

// Acceptance 1: an entry with an invalid MAC is discarded, then rebuilt.
#[test]
fn tampered_payload_is_discarded_and_rebuilt() {
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    s.put("plan", "abc", b"payload").unwrap();
    let f = entry_file(d.path(), "plan");
    let mut b = fs::read(&f).unwrap();
    *b.last_mut().unwrap() ^= 1;
    fs::write(&f, b).unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Discarded(Discard::BadMac)
    );
    assert!(!f.exists(), "discarded entry is deleted");
    assert_eq!(s.get("plan", "abc").unwrap(), Lookup::Miss);
    s.put("plan", "abc", b"rebuilt").unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Hit(b"rebuilt".to_vec())
    );
}

#[test]
fn tampered_tag_and_forged_entry_are_discarded() {
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    s.put("plan", "abc", b"payload").unwrap();
    let f = entry_file(d.path(), "plan");
    let mut b = fs::read(&f).unwrap();
    b[9] ^= 1;
    fs::write(&f, &b).unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Discarded(Discard::BadMac)
    );
    // A planted entry: right shape, zero tag.
    let mut forged = b"GOBSTAT1".to_vec();
    forged.extend_from_slice(&[0; 32]);
    forged.extend_from_slice(&3u64.to_le_bytes());
    forged.extend_from_slice(b"evil");
    forged.pop();
    fs::write(&f, forged).unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Discarded(Discard::BadMac)
    );
}

#[test]
fn truncation_at_every_length_is_discarded() {
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    s.put("plan", "abc", b"payload").unwrap();
    let f = entry_file(d.path(), "plan");
    let full = fs::read(&f).unwrap();
    for n in 0..full.len() {
        fs::write(&f, &full[..n]).unwrap();
        assert_eq!(
            s.get("plan", "abc").unwrap(),
            Lookup::Discarded(Discard::Truncated),
            "len {n}"
        );
    }
    let mut extra = full;
    extra.push(0);
    fs::write(&f, extra).unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Discarded(Discard::Malformed)
    );
}

#[test]
fn entry_moved_to_another_slot_is_discarded() {
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    s.put("plan", "a", b"x").unwrap();
    s.put("plan", "b", b"y").unwrap();
    let a = fs::read(entry_for(&s, d.path(), "a")).unwrap();
    let bpath = entry_for(&s, d.path(), "b");
    fs::write(&bpath, a).unwrap();
    assert_eq!(
        s.get("plan", "b").unwrap(),
        Lookup::Discarded(Discard::BadMac)
    );
}

fn entry_for(_s: &StateStore, dir: &Path, id: &str) -> PathBuf {
    let name = blake3::hash(id.as_bytes()).to_hex().to_string();
    dir.join("state").join("plan").join(name)
}

// A missing or replaced key never makes old state trusted.
#[test]
fn different_key_discards_and_missing_key_is_an_error() {
    let d = tempfile::tempdir().unwrap();
    store(d.path(), 1).put("plan", "abc", b"payload").unwrap();
    assert_eq!(
        store(d.path(), 2).get("plan", "abc").unwrap(),
        Lookup::Discarded(Discard::BadMac)
    );

    // No derivable directory: no key, no store.
    let none = resolve_cache_dir(|_| None, "frob");
    assert!(matches!(none, Err(TrustError::NoConfigDir)));
}

#[test]
fn missing_key_file_regenerates_and_invalidates_old_entries() {
    let d = tempfile::tempdir().unwrap();
    let keyp = d.path().join("cfg").join("machine.key");
    let k1 = MachineKey::load_or_create_at(&keyp).unwrap();
    StateStore::open_at(d.path().join("state"), k1, None)
        .unwrap()
        .put("plan", "abc", b"payload")
        .unwrap();
    fs::remove_file(&keyp).unwrap();
    let k2 = MachineKey::load_or_create_at(&keyp).unwrap();
    let s = StateStore::open_at(d.path().join("state"), k2, None).unwrap();
    assert_eq!(
        s.get("plan", "abc").unwrap(),
        Lookup::Discarded(Discard::BadMac)
    );
}

#[test]
fn concurrent_writers_never_expose_a_torn_entry() {
    let d = tempfile::tempdir().unwrap();
    let s = Arc::new(store(d.path(), 1));
    let payloads: Vec<Vec<u8>> = (0..4u8).map(|i| vec![i; 64 * 1024]).collect();
    let mut handles = Vec::new();
    for p in payloads.clone() {
        let s = Arc::clone(&s);
        handles.push(std::thread::spawn(move || {
            for _ in 0..50 {
                s.put("plan", "abc", &p).unwrap();
            }
        }));
    }
    let reader = {
        let s = Arc::clone(&s);
        let payloads = payloads.clone();
        std::thread::spawn(move || {
            for _ in 0..300 {
                match s.get("plan", "abc").unwrap() {
                    Lookup::Hit(p) => assert!(payloads.contains(&p)),
                    Lookup::Miss => {}
                    Lookup::Discarded(w) => panic!("torn read: {w:?}"),
                }
            }
        })
    };
    for h in handles {
        h.join().unwrap();
    }
    reader.join().unwrap();
    assert!(matches!(s.get("plan", "abc").unwrap(), Lookup::Hit(p) if payloads.contains(&p)));
    let leftovers = fs::read_dir(d.path().join("state/plan")).unwrap().count();
    assert_eq!(leftovers, 1, "no temp files left behind");
}

// Acceptance 2: CI mode ignores an in-tree cache; a root inside the tree is refused.
#[test]
fn ci_ignores_in_tree_cache_and_tree_root_is_refused() {
    let d = tempfile::tempdir().unwrap();
    let tree = d.path().join("repo");
    fs::create_dir_all(tree.join(".frob/state/plan")).unwrap();
    assert!(ci_active(|k| (k == "CI").then(|| "true".into())));
    assert!(!ci_active(|k| (k == "CI").then(|| "false".into())));
    assert!(!ci_active(|_| None));

    let env = |k: &str| match k {
        "XDG_CACHE_HOME" => Some(d.path().join("cache").into_os_string()),
        _ => None,
    };
    let root = resolve_cache_dir(env, "frob").unwrap();
    assert!(!root.starts_with(&tree));
    StateStore::open_at(root, MachineKey::from_bytes([1; 32]), Some(&tree)).unwrap();

    let err = StateStore::open_at(
        tree.join(".frob/state"),
        MachineKey::from_bytes([1; 32]),
        Some(&tree),
    )
    .unwrap_err();
    assert!(matches!(err, StateError::InsideWorkTree { .. }));
}

#[test]
fn bad_kind_is_rejected() {
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    assert!(matches!(
        s.put("../x", "a", b""),
        Err(StateError::BadName(_))
    ));
    assert!(matches!(s.get("", "a"), Err(StateError::BadName(_))));
}

#[cfg(unix)]
#[test]
fn files_and_dirs_are_owner_only() {
    use std::os::unix::fs::PermissionsExt;
    let d = tempfile::tempdir().unwrap();
    let s = store(d.path(), 1);
    s.put("plan", "abc", b"p").unwrap();
    let f = entry_file(d.path(), "plan");
    assert_eq!(
        fs::metadata(&f).unwrap().permissions().mode() & 0o777,
        0o600
    );
    assert_eq!(
        fs::metadata(f.parent().unwrap())
            .unwrap()
            .permissions()
            .mode()
            & 0o777,
        0o700
    );
}
