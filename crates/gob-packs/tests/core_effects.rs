//! The core-effects pack as versioned data: its version is in `grimble.packs.lock` and a
//! vocabulary change without a version bump is a PACK001 lock drift finding.

// frob:ticket 01M5XNNHV9M8HCP76TD867GGVJ

use std::path::PathBuf;

use gob_ir::core_pack::{ATOMS_TOML, OWNER};
use gob_packs::core_effects::{self, ATOMS_FILE};
use gob_packs::lock::{ItemChange, Lock, LockFinding, read, snapshot, verify, write};
use gob_packs::tier1;

fn lock_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../grimble.packs.lock")
}

/// Rewrites the repo lock from the embedded pack: `GOB_REGEN_CORE_LOCK=1 cargo test ...`.
#[test]
fn regenerate_lock_when_asked() {
    if std::env::var_os("GOB_REGEN_CORE_LOCK").is_none() {
        return;
    }
    let lock = Lock::new(vec![core_effects::locked().unwrap()]);
    write(&lock_path(), &lock).unwrap();
}

// frob:tests locked
#[test]
fn the_version_is_recorded_in_the_repo_lock_and_the_lock_holds() {
    let lock = read(&lock_path()).unwrap();
    let live = core_effects::locked().unwrap();
    assert_eq!(live.name, OWNER);
    assert_eq!(live.version, "1.0.0");
    let entry = lock.pack.iter().find(|p| p.name == OWNER).expect("locked");
    assert_eq!(entry.version, "1.0.0");
    assert_eq!(verify(&lock, &[live]), vec![]);
}

// frob:tests locked
#[test]
fn every_atom_and_vocab_row_is_a_lock_item() {
    let live = core_effects::locked().unwrap();
    assert!(live.items.keys().any(|k| k.contains("process.spawn")));
    assert!(live.items.keys().any(|k| k.contains("net.connect")));
    assert!(live.items.len() >= 20 + 28, "items: {}", live.items.len());
}

// frob:tests verify
#[test]
fn a_vocab_change_without_a_version_bump_is_a_lock_drift_finding() {
    let lock = Lock::new(vec![core_effects::locked().unwrap()]);
    let edited = ATOMS_TOML.replacen(
        "\"requests.get\"",
        "\"requests.get\", \"requests.extra\"",
        1,
    );
    assert_ne!(edited, ATOMS_TOML, "the edit must change the vocabulary");
    let content = tier1::parse(OWNER, ATOMS_FILE, &edited, None).unwrap();
    let manifest = core_effects::manifest().unwrap();
    let drifted = snapshot(&manifest, Some(&content), &core_effects::digest());
    let findings = verify(&lock, &[drifted]);
    assert!(
        findings.iter().any(|f| matches!(
            f,
            LockFinding::Item {
                change: ItemChange::Changed,
                without_version_bump: true,
                ..
            }
        )),
        "{findings:?}"
    );
    assert!(findings.iter().all(|f| f.code() == "PACK001"));
}

// frob:tests verify
#[test]
fn a_vocab_change_with_a_version_bump_names_the_version() {
    let lock = Lock::new(vec![core_effects::locked().unwrap()]);
    let edited = ATOMS_TOML.replacen(
        "\"requests.get\"",
        "\"requests.get\", \"requests.extra\"",
        1,
    );
    let content = tier1::parse(OWNER, ATOMS_FILE, &edited, None).unwrap();
    let mut manifest = core_effects::manifest().unwrap();
    manifest.pack.version = "1.1.0".to_owned();
    let drifted = snapshot(&manifest, Some(&content), &core_effects::digest());
    let findings = verify(&lock, &[drifted]);
    assert!(
        findings
            .iter()
            .any(|f| matches!(f, LockFinding::Version { .. }))
    );
    assert!(findings.iter().all(|f| !matches!(
        f,
        LockFinding::Item {
            without_version_bump: true,
            ..
        }
    )));
}
