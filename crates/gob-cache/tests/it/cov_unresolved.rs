//! Direct calls to `Pruned::total` and `Cache::with_clock`.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::sync::Arc;

use gob_cache::{Cache, Pruned};
use gob_time::{FixedClock, Stamp};

// frob:tests crates/gob-cache/src/lib.rs::Pruned.total
#[test]
fn total_sums_the_three_tables() {
    let p = Pruned {
        artifacts: 1,
        findings: 2,
        repo_rule: 4,
    };
    assert_eq!(Pruned::total(&p), 7);
}

// frob:tests crates/gob-cache/src/lib.rs::Cache.with_clock
#[test]
fn with_clock_replaces_the_clock_and_keeps_the_cache_usable() {
    let dir = tempfile::tempdir().unwrap();
    let clock: Arc<dyn gob_time::Clock> = Arc::new(FixedClock::new(Stamp::from_unix(1_000)));
    let cache = Cache::with_clock(Cache::open(dir.path()), clock);
    assert_eq!(Pruned::total(&cache.prune(true)), 0);
}
