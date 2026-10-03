//! The warm full check on this repository produces its timing breakdown.
//!
//! The 2 s budget is not asserted here (wall-clock is load-sensitive); it is
//! reported by the `full_check` bench and enforced by `PERF001` under `[perf] enforce`.

use std::path::Path;

use frob_check::{CheckOptions, run};

// frob:ticket 01M3ZFT5KZBX5H4FBJTCX0T4TP
#[test]
fn warm_run_on_this_repository_produces_a_timing_breakdown() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root");
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    run(&root, &opts).expect("cold run populates the cache");
    let warm = run(&root, &opts).expect("warm run");
    for s in &warm.timing.stages {
        eprintln!("stage {:<18} {:>6} ms", s.name, s.ms);
    }
    assert!(!warm.timing.stages.is_empty(), "stages are timed");
    assert!(warm.stats.cached_hits() > 0, "warm run uses the cache");
}
