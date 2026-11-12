//! Warm runs of the cached repository graph build are served entirely from the cache (no wall-clock target, which only flakes under load).

// frob:ticket 01M4P3HCCJG2YN2M39FXJAFC5D

use frob_tests::build_repo_graph_with_stats;

const FILES: usize = 60;
const WARM_RUNS: usize = 5;

#[test]
// frob:tests crates/frob-tests/src/touched.rs::build_repo_graph_with_stats
fn warm_runs_are_served_entirely_from_the_cache() {
    let dir = tempfile::tempdir().expect("tempdir");
    for i in 0..FILES {
        let body =
            format!("pub fn f{i}() -> u32 {{ {i} }}\npub fn g{i}() -> u32 {{ f{i}() + 1 }}\n");
        std::fs::write(dir.path().join(format!("m{i}.rs")), body).expect("write");
    }

    let (_, cold) = build_repo_graph_with_stats(dir.path()).expect("cold");
    assert!(cold.extracted >= FILES, "cold build extracts every file");

    for _ in 0..WARM_RUNS {
        let (_, warm) = build_repo_graph_with_stats(dir.path()).expect("warm");
        // A warm run must be served entirely from the cache.
        assert_eq!(warm.extracted, 0, "warm run must not re-extract");
        assert_eq!(
            warm.cached, cold.extracted,
            "warm run must hit the cache for every file"
        );
    }
}
