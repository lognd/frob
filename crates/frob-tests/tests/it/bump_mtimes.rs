//! `frob test --base` bumps changed files' mtimes so later cargo builds recompile them (~PSDN1CC).

use frob_tests::bump_mtimes;

// frob:ticket 01M4VN38GBQAPJWK0FZPSDN1CC
// frob:tests crates/frob-tests/src/touched.rs::bump_mtimes
#[test]
fn bump_mtimes_makes_changed_files_newer_than_a_prior_build() {
    let dir = tempfile::tempdir().expect("tmp");
    let file = dir.path().join("a.rs");
    std::fs::write(&file, "fn a() {}").expect("write");
    let old = std::time::UNIX_EPOCH + std::time::Duration::from_secs(1_000_000);
    std::fs::File::options()
        .write(true)
        .open(&file)
        .and_then(|f| f.set_modified(old))
        .expect("age");
    let n = bump_mtimes(dir.path(), &["a.rs".to_owned(), "gone.rs".to_owned()]);
    assert_eq!(n, 1);
    let m = std::fs::metadata(&file)
        .and_then(|m| m.modified())
        .expect("mtime");
    assert!(m > old + std::time::Duration::from_secs(60));
}
