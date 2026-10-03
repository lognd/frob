//! Benchmark: build and query a 10k-node term.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]
#![allow(clippy::many_single_char_names, reason = "short builder bindings")]

use std::hint::black_box;

use criterion::{Criterion, criterion_group, criterion_main};
use gob_ir::{
    Facet, GroupOrder, Location, Model, NodeId, NodeSpec, Operator, RefId, ScopeGraph, Term,
    TermBuilder,
};
use gob_text::FileInterner;

/// `count` functions of ten nodes each (a unit, literals, a binder use and a call).
fn build(count: u32) -> Term {
    let mut files = FileInterner::new();
    let file = files.intern("big.rs");
    let mut tb = TermBuilder::new("big.rs", "rust");
    let mut units: Vec<NodeId> = Vec::new();
    for i in 0..count {
        let base = i * 100;
        let at = |from: u32, to: u32| Location::text(file, base + from, base + to);
        let mut kids = Vec::new();
        for j in 0..7 {
            let lit = Operator::lit("int", &j.to_string());
            kids.push(tb.node(NodeSpec::new(lit, at(j, j + 1)), &[]).unwrap());
        }
        let arg = tb
            .node(NodeSpec::new(Operator::reference("x"), at(8, 9)), &[])
            .unwrap();
        let head = tb
            .node(NodeSpec::new(Operator::reference("helper"), at(9, 10)), &[])
            .unwrap();
        kids.push(
            tb.node(
                NodeSpec::new(Operator::apply("call"), at(8, 11)),
                &[head, arg],
            )
            .unwrap(),
        );
        let spec = NodeSpec::new(Operator::unit("function", "impl"), at(0, 99))
            .named(&format!("f{i}"))
            .binders(&["x"]);
        units.push(tb.node(spec, &kids).unwrap());
    }
    let module = NodeSpec::new(
        Operator::unit("module", "impl"),
        Location::text(file, 0, count * 100),
    );
    let root = tb.node(module, &units).unwrap();
    tb.finish(root).unwrap()
}

/// A chain of `depth` nested binds over one leaf, built iteratively.
fn deep(depth: u32) -> Term {
    let mut files = FileInterner::new();
    let file = files.intern("deep.rs");
    let mut tb = TermBuilder::new("deep.rs", "rust");
    let at = |i: u32| Location::text(file, i, i + 1);
    let leaf = tb
        .node(NodeSpec::new(Operator::reference("x0"), at(0)), &[])
        .unwrap();
    let mut cur = leaf;
    for k in 1..=depth {
        let binder = ["x0", "x1", "x2"][(k % 3) as usize];
        let spec = NodeSpec::new(Operator::bind("let", "val"), at(k)).binders(&[binder]);
        cur = tb.node(spec, &[cur]).unwrap();
    }
    tb.finish(cur).unwrap()
}

/// `depth` nested binds with `refs` leaf references to a name that is never bound.
fn many_refs(depth: u32, refs: u32) -> Term {
    let mut files = FileInterner::new();
    let file = files.intern("refs.rs");
    let mut tb = TermBuilder::new("refs.rs", "rust");
    let at = |i: u32| Location::text(file, i, i + 1);
    let leaves: Vec<NodeId> = (0..refs)
        .map(|i| {
            tb.node(NodeSpec::new(Operator::reference("free"), at(i)), &[])
                .unwrap()
        })
        .collect();
    let mut cur = tb
        .node(
            NodeSpec::new(Operator::group(GroupOrder::Sequence), at(0)),
            &leaves,
        )
        .unwrap();
    for k in 0..depth {
        let spec = NodeSpec::new(Operator::bind("let", "val"), at(k)).binders(&["x"]);
        cur = tb.node(spec, &[cur]).unwrap();
    }
    tb.finish(cur).unwrap()
}

fn bench_deep(c: &mut Criterion) {
    let mut g = c.benchmark_group("deep_1e6");
    g.sample_size(10);
    g.bench_function("build_and_seal", |b| b.iter(|| black_box(deep(1_000_000))));
    let model = Model::lexical(deep(1_000_000));
    let term = model.term();
    g.bench_function("print_alpha", |b| {
        b.iter(|| black_box(term.print_alpha(term.root())));
    });
    g.bench_function("graph_digest", |b| {
        b.iter(|| black_box(model.graph_digest()));
    });
    g.bench_function("free_vars", |b| {
        b.iter(|| black_box(term.free_vars(term.root())));
    });
    g.bench_function("scope_graph_from_term", |b| {
        b.iter(|| black_box(ScopeGraph::from_term(term)));
    });
    g.finish();
}

/// Every reference id of `graph`, in node order.
fn ref_ids(graph: &ScopeGraph, term: &Term) -> Vec<RefId> {
    term.ids().filter_map(|n| graph.ref_at(n)).collect()
}

fn bench_resolution(c: &mut Criterion) {
    for depth in [200, 10_000] {
        let term = many_refs(depth, 20_000);
        let mut g = c.benchmark_group(format!("resolution_20k_refs_depth_{depth}"));
        g.sample_size(10);
        g.bench_function("cold", |b| {
            b.iter_batched(
                || ScopeGraph::from_term(&term),
                |graph| {
                    for r in ref_ids(&graph, &term) {
                        black_box(graph.resolve(r));
                    }
                },
                criterion::BatchSize::LargeInput,
            );
        });
        let warm = ScopeGraph::from_term(&term);
        let warm_refs = ref_ids(&warm, &term);
        g.bench_function("memoized", |b| {
            b.iter(|| {
                for &r in &warm_refs {
                    black_box(warm.resolve(r));
                }
            });
        });
        g.finish();
    }
}

fn bench(c: &mut Criterion) {
    c.bench_function("build_10k", |b| b.iter(|| black_box(build(1000))));
    let model = Model::lexical(build(1000));
    c.bench_function("digest_all_units", |b| {
        b.iter(|| {
            let term = model.term();
            for u in term.units() {
                black_box(term.facet_digest(u.node, Facet::Body));
            }
        });
    });
    c.bench_function("graph_digest_10k", |b| {
        b.iter(|| black_box(model.graph_digest()));
    });
    c.bench_function("free_vars_root", |b| {
        b.iter(|| black_box(model.term().free_vars(model.term().root())));
    });
}

criterion_group!(benches, bench, bench_deep, bench_resolution);
criterion_main!(benches);
