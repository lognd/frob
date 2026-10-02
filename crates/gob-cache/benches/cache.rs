//! Benchmark: 10k findings cache hits.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]

use criterion::{Criterion, criterion_group, criterion_main};
use gob_cache::{Cache, FindingsKey};

fn key(i: u32) -> FindingsKey {
    FindingsKey {
        file_digest: format!("digest{i}"),
        rule_id: "R1".into(),
        rule_version: 1,
        side_input_digest: "s".into(),
    }
}

fn bench_hits(c: &mut Criterion) {
    let dir = tempfile::tempdir().expect("tempdir");
    let cache = Cache::open(dir.path());
    for i in 0..10_000 {
        cache.put_findings(&key(i), b"payload");
    }
    let mut group = c.benchmark_group("cache");
    group.sample_size(10);
    group.bench_function("hit_10k", |b| {
        b.iter(|| {
            (0..10_000)
                .filter(|i| cache.get_findings(&key(*i)).is_some())
                .count()
        });
    });
    group.finish();
}

criterion_group!(benches, bench_hits);
criterion_main!(benches);
