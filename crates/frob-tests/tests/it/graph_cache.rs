//! The touched-set graph reads the shared artifact cache on a second build of an unchanged tree.

// frob:ticket 01M4D6NFZGVDDT0GG78KVA1TA6

use frob_tests::build_repo_graph_with_stats;

#[test]
// frob:tests crates/frob-tests/src/touched.rs::build_repo_graph_with_stats
fn second_build_of_an_unchanged_tree_extracts_nothing() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("a.rs"), "pub fn a() -> u32 { 1 }\n").expect("write");
    std::fs::write(dir.path().join("b.rs"), "pub fn b() -> u32 { 2 }\n").expect("write");

    let (_, first) = build_repo_graph_with_stats(dir.path()).expect("first");
    assert_eq!(first.cached, 0, "cold build reads nothing from cache");
    assert!(first.extracted >= 2, "cold build extracts every file");

    let (_, second) = build_repo_graph_with_stats(dir.path()).expect("second");
    assert_eq!(second.extracted, 0, "warm build must not re-extract");
    assert_eq!(second.cached, first.extracted);
}
