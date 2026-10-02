//! Benchmark: the full check on this repository, second (warm) run reported.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]

use std::path::{Path, PathBuf};

use criterion::{Criterion, criterion_group, criterion_main};
use frob_check::{CheckOptions, run};

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root")
}

fn bench_full_check(c: &mut Criterion) {
    let root = repo_root();
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    // First run populates the cache; the measured runs are the warm case.
    run(&root, &opts).expect("cold run");
    let mut group = c.benchmark_group("full_check");
    group.sample_size(10);
    group.bench_function("warm", |b| {
        b.iter(|| run(&root, &opts).expect("warm run").findings.len());
    });
    group.finish();
}

criterion_group!(benches, bench_full_check);
criterion_main!(benches);
