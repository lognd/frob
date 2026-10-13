//! The repository-shared cache: location from any checkout, and two processes writing at once (~TSK0M4Y).

use std::path::Path;
use std::process::Command;

use gob_cache::{Cache, FindingsKey, Seeded, git_common_dir, seed_shared, shared_dir};

const CHILD_ENV: &str = "GOB_CACHE_SHARED_TEST_DIR";
const ROWS: u32 = 300;

fn key(tag: &str, i: u32) -> FindingsKey {
    FindingsKey {
        file_digest: format!("{tag}-{i}"),
        rule_id: "R1".into(),
        rule_version: 1,
        side_input_digest: "s".into(),
    }
}

/// Fake a primary checkout and a linked worktree sharing one git common dir.
fn fake_repo(dir: &Path) -> (std::path::PathBuf, std::path::PathBuf) {
    let primary = dir.join("primary");
    std::fs::create_dir_all(primary.join(".git/worktrees/wt")).unwrap();
    std::fs::write(primary.join(".git/worktrees/wt/commondir"), "../..\n").unwrap();
    let linked = dir.join("linked");
    std::fs::create_dir_all(&linked).unwrap();
    let private = primary.join(".git/worktrees/wt");
    std::fs::write(
        linked.join(".git"),
        format!("gitdir: {}\n", private.display()),
    )
    .unwrap();
    (primary, linked)
}

// frob:tests crates/gob-cache/src/lib.rs::shared_dir
#[test]
fn primary_and_linked_worktree_share_one_cache_dir() {
    let tmp = tempfile::tempdir().unwrap();
    let (primary, linked) = fake_repo(tmp.path());
    let a = shared_dir(&primary, ".frob").unwrap();
    let b = shared_dir(&linked, ".frob").unwrap();
    assert_eq!(a, b);
    assert!(a.ends_with(".git/frob/cache/frob"), "{}", a.display());
    assert_eq!(
        git_common_dir(&linked).unwrap(),
        gob_fs::canonical(&primary.join(".git")).unwrap()
    );
    let plain = tmp.path().join("plain");
    std::fs::create_dir_all(&plain).unwrap();
    assert!(shared_dir(&plain, ".frob").is_none());
}

// frob:tests crates/gob-cache/src/lib.rs::shared_dir
#[test]
fn a_row_written_from_one_checkout_hits_from_the_other() {
    let tmp = tempfile::tempdir().unwrap();
    let (primary, linked) = fake_repo(tmp.path());
    Cache::open_shared(&primary, ".frob").put_findings(&key("x", 1), b"p");
    let hit = Cache::open_shared(&linked, ".frob").get_findings(&key("x", 1));
    assert_eq!(hit.as_deref(), Some(&b"p"[..]));
    assert!(!primary.join(".frob").exists());
}

fn child(dir: &Path, tag: &str) {
    let cache = Cache::open(dir);
    assert!(!cache.is_null(), "{tag} got a null cache");
    for i in 0..ROWS {
        cache.put_findings(&key(tag, i), tag.as_bytes());
        // Interleave reads of the peer's rows to exercise readers beside a writer.
        let _ = cache.get_findings(&key("a", i));
    }
}

// frob:tests crates/gob-cache/src/lib.rs::migrate
#[test]
fn two_processes_open_and_write_one_fresh_cache_without_loss() {
    if let Ok(dir) = std::env::var(CHILD_ENV) {
        let tag = std::env::var("GOB_CACHE_SHARED_TEST_TAG").unwrap();
        child(Path::new(&dir), &tag);
        return;
    }
    let tmp = tempfile::tempdir().unwrap();
    let exe = std::env::current_exe().unwrap();
    let spawn = |tag: &str| {
        Command::new(&exe)
            .args([
                "two_processes_open_and_write_one_fresh_cache_without_loss",
                "--exact",
                "--nocapture",
            ])
            .arg("--test-threads=1")
            .env(CHILD_ENV, tmp.path())
            .env("GOB_CACHE_SHARED_TEST_TAG", tag)
            .spawn()
            .unwrap()
    };
    let (mut a, mut b) = (spawn("a"), spawn("b"));
    assert!(a.wait().unwrap().success());
    assert!(b.wait().unwrap().success());
    let cache = Cache::open(tmp.path());
    for i in 0..ROWS {
        assert_eq!(cache.get_findings(&key("a", i)).as_deref(), Some(&b"a"[..]));
        assert_eq!(cache.get_findings(&key("b", i)).as_deref(), Some(&b"b"[..]));
    }
}

// frob:ticket 01M4M52WKHGXADHPQ08J1AS8BJ
// frob:tests crates/gob-fs/src/gitdir.rs::git_common_dir
#[test]
fn gob_cache_does_not_depend_on_gob_exec() {
    let manifest = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/Cargo.toml"))
        .expect("gob-cache manifest");
    let named: Vec<&str> = manifest
        .lines()
        .map(str::trim)
        .filter(|l| !l.starts_with('#') && l.starts_with("gob-exec"))
        .collect();
    assert!(
        named.is_empty(),
        "gob-cache must not name gob-exec (path handling lives in gob-fs): {named:?}"
    );
    let (primary, linked) = fake_repo(tempfile::tempdir().unwrap().keep().as_path());
    assert_eq!(git_common_dir(&primary), git_common_dir(&linked));
}

// frob:ticket 01M4DPJJW8D3KXZVTEN5D4WN5G
// frob:tests crates/gob-cache/src/lib.rs::seed_shared
#[test]
fn a_warm_primary_cache_seeds_the_shared_one_once() {
    let tmp = tempfile::tempdir().unwrap();
    let (primary, linked) = fake_repo(tmp.path());
    assert_eq!(seed_shared(&primary, ".frob"), Seeded::NothingToSeed);
    Cache::open(&primary.join(".frob")).put_findings(&key("w", 1), b"warm");
    assert_eq!(seed_shared(&primary, ".frob"), Seeded::Copied);
    let hit = Cache::open_shared(&linked, ".frob").get_findings(&key("w", 1));
    assert_eq!(hit.as_deref(), Some(&b"warm"[..]));
    // The shared cache now exists and wins over later primary rows.
    Cache::open(&primary.join(".frob")).put_findings(&key("w", 2), b"late");
    assert_eq!(seed_shared(&primary, ".frob"), Seeded::AlreadyShared);
    assert!(
        Cache::open_shared(&linked, ".frob")
            .get_findings(&key("w", 2))
            .is_none()
    );
}
