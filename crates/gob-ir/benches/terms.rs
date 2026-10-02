//! Benchmark: build and query a 10k-node term.
#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]
#![allow(clippy::many_single_char_names, reason = "short builder bindings")]

use std::hint::black_box;

use criterion::{Criterion, criterion_group, criterion_main};
use gob_ir::{Facet, Location, Model, NodeId, NodeSpec, Operator, Term, TermBuilder};
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
        b.iter(|| black_box(model.graph_digest()))
    });
    c.bench_function("free_vars_root", |b| {
        b.iter(|| black_box(model.term().free_vars(model.term().root())));
    });
}

criterion_group!(benches, bench);
criterion_main!(benches);
