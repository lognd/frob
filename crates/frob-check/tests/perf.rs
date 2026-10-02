//! The warm full check on this repository stays inside the 2 s budget.

use std::path::Path;

use frob_check::{CheckOptions, run};

#[test]
fn warm_run_on_this_repository_is_under_two_seconds() {
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
    eprintln!(
        "budgeted total {} ms, cached hits {}",
        warm.timing.budget_ms(),
        warm.stats.cached_hits()
    );
    assert!(warm.stats.cached_hits() > 0, "warm run uses the cache");
    assert!(warm.timing.budget_ms() < 2000, "warm run over 2 s");
}
