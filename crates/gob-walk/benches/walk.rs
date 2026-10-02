//! Benchmark: walk and hash a generated 10k-file tree.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]

use criterion::{Criterion, criterion_group, criterion_main};
use gob_walk::{WalkConfig, walk};

fn bench_walk(c: &mut Criterion) {
    let dir = tempfile::tempdir().expect("tempdir");
    for i in 0..10_000 {
        let sub = dir.path().join(format!("d{}", i % 100));
        std::fs::create_dir_all(&sub).expect("mkdir");
        std::fs::write(sub.join(format!("f{i}.rs")), format!("fn f{i}() {{}}\n")).expect("write");
    }
    let cfg = WalkConfig::default();
    let mut group = c.benchmark_group("walk");
    group.sample_size(10);
    group.bench_function("walk_10k", |b| {
        b.iter(|| walk(dir.path(), &cfg).expect("walk").files.len());
    });
    group.finish();
}

criterion_group!(benches, bench_walk);
criterion_main!(benches);
