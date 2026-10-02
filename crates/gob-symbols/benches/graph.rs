//! Benchmark: build the symbol graph over this workspace's `crates/` tree.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]

use std::path::Path;

use criterion::{Criterion, criterion_group, criterion_main};
use gob_cache::Cache;
use gob_symbols::build_graph;
use gob_walk::{WalkConfig, walk};

fn bench_build(c: &mut Criterion) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let walked = walk(&root, &WalkConfig::default()).expect("walk crates/");
    let cache = Cache::null();
    let mut group = c.benchmark_group("symbols");
    group.sample_size(10);
    group.bench_function("build_graph_crates", |b| {
        b.iter(|| build_graph(&root, &walked.files, &cache).node_count());
    });
    group.finish();
}

criterion_group!(benches, bench_build);
criterion_main!(benches);
