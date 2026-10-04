//! Benchmark: the full check on this repository, cold then warm, each against its recorded budget.
//!
//! This is where the real-repository measurement lives (build-test-ci.md section 4, "bench
//! (scheduled)"); the `perf` test covers the same contract on a fixture. Run in release:
//! `cargo bench -p frob-check --bench full_check`.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]

use std::path::{Path, PathBuf};

use criterion::{Criterion, criterion_group, criterion_main};
use frob_check::{CheckOptions, run};

/// Warm-run budget in milliseconds (D30).
const WARM_BUDGET_MS: u64 = 2000;
/// Cold-run budget in milliseconds on this repository in release: a regression guard at about
/// twice the 20-30 s measured on the loaded 12-core host (recorded in build-test-ci.md).
const COLD_BUDGET_MS: u64 = 60_000;

fn repo_root() -> PathBuf {
    gob_exec::canonical(&Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."))
        .expect("repository root")
}

fn bench_full_check(c: &mut Criterion) {
    let root = repo_root();
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    // Drop the derived cache so the first run is genuinely cold (it is rebuilt by that run).
    for suffix in ["", "-shm", "-wal"] {
        let _ = std::fs::remove_file(root.join(format!(".frob/cache.sqlite{suffix}")));
    }
    let cold = run(&root, &opts).expect("cold run");
    let cold_ms = cold.timing.budget_ms();
    for st in &cold.timing.stages {
        eprintln!("cold stage {:<18} {:>6} ms", st.name, st.ms);
    }
    eprintln!("cold budgeted total {cold_ms} ms (budget {COLD_BUDGET_MS} ms)");
    assert!(
        cold_ms < COLD_BUDGET_MS,
        "cold run over the {COLD_BUDGET_MS} ms budget: {cold_ms} ms"
    );
    // frob:ticket 01M3ZFT5KZBX5H4FBJTCX0T4TP
    let warm = run(&root, &opts).expect("warm run");
    let ms = warm.timing.budget_ms();
    eprintln!("warm budgeted total {ms} ms (budget {WARM_BUDGET_MS} ms)");
    assert!(ms < WARM_BUDGET_MS, "warm run over the 2 s budget: {ms} ms");
    let mut group = c.benchmark_group("full_check");
    group.sample_size(10);
    group.bench_function("warm", |b| {
        b.iter(|| run(&root, &opts).expect("warm run").findings.len());
    });
    group.finish();
}

criterion_group!(benches, bench_full_check);
criterion_main!(benches);
