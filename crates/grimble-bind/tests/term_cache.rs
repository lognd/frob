//! A warm cache spares the parse of the term too: units come from cached terms, never a refold.

// frob:ticket 01M4HB1ZAX0Q6QHK1DK3Y3EZ9E

use std::sync::{Arc, Mutex};

use gob_cache::{ArtifactKey, Cache};
use gob_walk::{FileEntry, WalkConfig, walk};
use grimble_bind::code::{Code, adapter_folds};

/// The fold counter is process-wide, so the tests take turns.
static SERIAL: Mutex<()> = Mutex::new(());

fn repo() -> (
    tempfile::TempDir,
    std::path::PathBuf,
    Arc<Cache>,
    Vec<FileEntry>,
) {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().join("repo");
    std::fs::create_dir_all(&root).expect("mkdir");
    std::fs::write(root.join("a.rs"), "pub fn a() -> u32 { 1 }\n").expect("write");
    std::fs::write(
        root.join("b.rs"),
        "// grimble:binds a\npub struct S;\nimpl S { pub fn b(&self) {} }\n",
    )
    .expect("write");
    let cache = Arc::new(Cache::open(&dir.path().join("cache")));
    let entries = walk(&root, &WalkConfig::default()).expect("walk").files;
    (dir, root, cache, entries)
}

#[test]
// frob:tests crates/grimble-bind/src/code.rs::CodeFile.folded
// frob:tests crates/grimble-bind/src/code.rs::adapter_folds
fn warm_build_reads_terms_from_cache_without_parsing() {
    let _turn = SERIAL
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let (_dir, root, cache, entries) = repo();
    let cold = Code::build_with(&root, &entries, &cache);
    let cold_units: Vec<_> = cold.files.iter().map(|f| f.units().len()).collect();
    assert!(cold_units.iter().any(|n| *n > 0));
    let (warm, folds) = build_warm(&root, &entries, &cache);
    let warm_units: Vec<_> = warm.files.iter().map(|f| f.units().len()).collect();
    assert_eq!(folds, 0, "no adapter parse on a warm cache");
    assert_eq!(cold_units, warm_units);
    assert_terms_equal(&cold, &warm);
}

/// Builds and prefolds from a warm cache, returning the build and how many adapter parses it cost.
fn build_warm(root: &std::path::Path, entries: &[FileEntry], cache: &Arc<Cache>) -> (Code, usize) {
    let before = adapter_folds();
    let warm = Code::build_with(root, entries, cache);
    warm.prefold(warm.files.iter().map(|f| f.path.clone()));
    (warm, adapter_folds() - before)
}

/// Every file of both builds is folded and carries the same term and scopes.
fn assert_terms_equal(cold: &Code, warm: &Code) {
    for f in &warm.files {
        assert!(f.folded().is_some());
    }
    for (c, w) in cold.files.iter().zip(&warm.files) {
        let (c, w) = (c.folded().unwrap(), w.folded().unwrap());
        assert_eq!(c.term, w.term);
        assert_eq!(
            postcard::to_stdvec(&c.scopes).unwrap(),
            postcard::to_stdvec(&w.scopes).unwrap()
        );
    }
}

#[test]
// frob:tests crates/grimble-bind/src/code.rs::CodeFile.folded
fn corrupt_term_entry_falls_back_to_a_refold() {
    let _turn = SERIAL
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let (_dir, root, cache, entries) = repo();
    let cold = Code::build_with(&root, &entries, &cache);
    let adapter = gob_symbols::adapter_for(&entries[0].language).expect("rust adapter");
    for e in &entries {
        cache.put_artifact(
            &ArtifactKey {
                content_digest: format!("{}@{}", e.digest, e.path),
                producer_identity: format!(
                    "grimble-bind/term-v{}/{}",
                    gob_ir::TERM_SCHEMA_VERSION,
                    adapter.identity()
                ),
            },
            b"\xff not a term",
        );
    }
    let before = adapter_folds();
    let warm = Code::build_with(&root, &entries, &cache);
    for (c, w) in cold.files.iter().zip(&warm.files) {
        assert_eq!(c.units().len(), w.units().len());
    }
    assert!(adapter_folds() > before, "corrupt entries refold");
}

#[test]
// frob:ticket 01M6CR6YQ1EXHRNQTQ034J6GAE
// frob:tests crates/grimble-bind/src/code.rs::CodeFile.folded
fn identical_files_keep_their_own_unit_symrefs() {
    let _turn = SERIAL
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().join("repo");
    for sub in ["x", "y"] {
        std::fs::create_dir_all(root.join(sub)).expect("mkdir");
        std::fs::write(
            root.join(sub).join("same.rs"),
            "pub fn same() -> u32 { 1 }\n",
        )
        .expect("write");
    }
    let cache = Arc::new(Cache::open(&dir.path().join("cache")));
    let entries = walk(&root, &WalkConfig::default()).expect("walk").files;
    // Cold then warm: the warm build reads terms from the cache.
    for _ in 0..2 {
        let code = Code::build_with(&root, &entries, &cache);
        for f in &code.files {
            let units = f.units();
            assert!(!units.is_empty(), "{} has units", f.path);
            assert!(
                units.iter().all(|u| u.symref.starts_with(&f.path)),
                "{} units carry its own path: {units:?}",
                f.path
            );
        }
    }
}
