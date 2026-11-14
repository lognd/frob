//! Refreshing the offline advisory snapshot from an advisory-db checkout.

// frob:ticket 01M5A63T80Z6H00NE32WQ6SCFF

use std::fs;
use std::path::Path;

use grimble_vet::{Snapshot, refresh, stamp_as_of};
use semver::Version;

/// Advisory text for `id` against `pkg`, fixed from 2.0.0.
fn adv(id: &str, pkg: &str) -> String {
    format!(
        "[advisory]\nid = \"{id}\"\npackage = \"{pkg}\"\ntitle = \"t\"\n[versions]\npatched = [\">=2.0.0\"]\n"
    )
}

/// Write `text` at `root/rel`, creating parents.
fn put(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    fs::create_dir_all(p.parent().unwrap()).unwrap();
    fs::write(p, text).unwrap();
}

#[test]
fn refresh_copies_prunes_and_stamps() {
    // frob:tests crates/grimble-vet/src/advisory.rs::refresh
    // frob:tests crates/grimble-vet/src/advisory.rs::stamp_as_of
    let src = tempfile::tempdir().unwrap();
    let dst = tempfile::tempdir().unwrap();
    put(
        src.path(),
        "crates/a/RUSTSEC-2099-0001.toml",
        &adv("RUSTSEC-2099-0001", "a"),
    );
    put(src.path(), "README.md", "ignored");
    put(
        dst.path(),
        "crates/gone/RUSTSEC-2000-0001.toml",
        &adv("RUSTSEC-2000-0001", "gone"),
    );
    let rep = refresh(src.path(), dst.path(), "2026-11-06").unwrap();
    assert_eq!((rep.copied, rep.removed), (1, 1));
    assert_eq!(stamp_as_of(dst.path()).as_deref(), Some("2026-11-06"));
    let snap = Snapshot::load(dst.path()).unwrap();
    assert_eq!(snap.affecting("a", &Version::new(1, 0, 0)).len(), 1);
    assert!(snap.affecting("gone", &Version::new(1, 0, 0)).is_empty());
}

#[test]
fn refresh_ignores_non_advisory_files() {
    // frob:tests crates/grimble-vet/src/advisory.rs::refresh
    let src = tempfile::tempdir().unwrap();
    let dst = tempfile::tempdir().unwrap();
    put(src.path(), "README.md", "ignored");
    refresh(src.path(), dst.path(), "2026-11-06").unwrap();
    assert!(!dst.path().join("README.md").exists());
}

#[test]
fn refresh_with_a_bad_advisory_leaves_dest_untouched() {
    // frob:tests crates/grimble-vet/src/advisory.rs::refresh
    let src = tempfile::tempdir().unwrap();
    let dst = tempfile::tempdir().unwrap();
    put(src.path(), "crates/a/RUSTSEC-2099-0001.toml", "not toml [");
    put(
        dst.path(),
        "crates/keep/RUSTSEC-2000-0001.toml",
        &adv("RUSTSEC-2000-0001", "keep"),
    );
    let outcome = (
        refresh(src.path(), dst.path(), "2026-11-06").is_err(),
        dst.path()
            .join("crates/keep/RUSTSEC-2000-0001.toml")
            .exists(),
    );
    assert_eq!(outcome, (true, true));
}
