//! The warm-run median of the cached repository graph build stays under the 15s target.

// frob:ticket 01M4P3HCCJG2YN2M39FXJAFC5D

use std::time::{Duration, Instant};

use frob_tests::build_repo_graph_with_stats;

/// The warm-run target from the speed-cache goal; deliberately generous so machine load cannot flake it.
const TARGET: Duration = Duration::from_secs(15);
const FILES: usize = 60;
const WARM_RUNS: usize = 5;

#[test]
// frob:tests crates/frob-tests/src/touched.rs::build_repo_graph_with_stats
fn warm_run_median_is_under_the_target() {
    let dir = tempfile::tempdir().expect("tempdir");
    for i in 0..FILES {
        let body =
            format!("pub fn f{i}() -> u32 {{ {i} }}\npub fn g{i}() -> u32 {{ f{i}() + 1 }}\n");
        std::fs::write(dir.path().join(format!("m{i}.rs")), body).expect("write");
    }

    let (_, cold) = build_repo_graph_with_stats(dir.path()).expect("cold");
    assert!(cold.extracted >= FILES, "cold build extracts every file");

    let mut times = Vec::with_capacity(WARM_RUNS);
    for _ in 0..WARM_RUNS {
        let start = Instant::now();
        let (_, warm) = build_repo_graph_with_stats(dir.path()).expect("warm");
        times.push(start.elapsed());
        // Deterministic half: a warm run must be served entirely from the cache.
        assert_eq!(warm.extracted, 0, "warm run must not re-extract");
        assert_eq!(
            warm.cached, cold.extracted,
            "warm run must hit the cache for every file"
        );
    }
    times.sort();
    let median = times[WARM_RUNS / 2];
    assert!(
        median <= TARGET,
        "warm median {median:?} exceeds {TARGET:?} (runs: {times:?})"
    );
}
