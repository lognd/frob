//! Totality in practice (Theorem 1): a term one million levels deep is printed, digested, its
//! symrefs computed and queried on a default-sized (2 MiB) thread stack, deterministically.
//!
//! The term is built iteratively, because the test itself must not recurse either.

// frob:ticket 01M3Z8NVCBM9KXN5ZY97QWX8P1

mod support;

use std::collections::BTreeSet;
use std::thread;

use gob_ir::{Digest, Facet, FacetDigest, Model, NodeId, Operator, PrintOpts, Resolution};
use support::B;

const DEPTH: u32 = 1_000_000;
/// The default thread stack of `std::thread`, deliberately not raised.
const DEFAULT_STACK: usize = 2 * 1024 * 1024;

/// Everything the deep term reveals, for the determinism comparison.
#[derive(Debug, PartialEq, Eq)]
struct Report {
    alpha: Digest,
    full: Digest,
    graph: Digest,
    facets: Vec<FacetDigest>,
    units: usize,
    deepest_symref: String,
    free: BTreeSet<String>,
    ancestors: usize,
    descendants: usize,
    bound: Resolution,
    unbound: Resolution,
    unbound_again: Resolution,
}

fn build() -> (Model, NodeId) {
    let mut b = B::new("deep.rs", "rust");
    let x0 = b.reference("x0");
    let zz = b.reference("zz");
    let mut cur = b.node(Operator::group(gob_ir::GroupOrder::Sequence), &[x0, zz]);
    for k in 1..=DEPTH {
        cur = if k % 5000 == 0 {
            b.unit("function", &format!("u{k}"), &[], &[cur])
        } else if k % 1001 == 0 {
            b.node(Operator::anon("closure"), &[cur])
        } else if k % 399_989 == 0 {
            let head = b.reference("f");
            b.node(Operator::apply("call"), &[head, cur])
        } else {
            let binder = ["x0", "x1", "x2"][(k % 3) as usize];
            let spec = b.spec(Operator::bind("let", "val")).binders(&[binder]);
            b.add(spec, &[cur])
        };
    }
    let root = b.file_unit(&[cur]);
    (Model::lexical(b.finish(root)), x0)
}

fn report() -> Report {
    let (model, leaf) = build();
    let term = model.term();
    let root = term.root();
    let alpha = term.print_alpha(root);
    assert!(alpha.len() > DEPTH as usize);
    assert_eq!(
        alpha.bytes().filter(|&c| c == b'(').count(),
        alpha.bytes().filter(|&c| c == b')').count(),
        "parentheses balance"
    );
    let units = term.units();
    let deepest = units.iter().rev().find(|u| u.node != root).expect("units");
    let zz = NodeId::index(leaf) + 1;
    let zz = term.ids().nth(zz).expect("zz leaf");
    let facets = [root, deepest.node]
        .into_iter()
        .flat_map(|u| Facet::ALL.map(|f| term.facet_digest(u, f)))
        .collect();
    Report {
        alpha: Digest::of("alpha", alpha.as_bytes()),
        full: Digest::of("full", term.print_with(root, PrintOpts::FULL).as_bytes()),
        graph: model.graph_digest(),
        facets,
        units: units.len(),
        deepest_symref: deepest.symref.to_string(),
        free: term.free_vars(root),
        ancestors: term.ancestors(leaf).len(),
        descendants: term.descendants(root).len(),
        bound: model.resolve_node(leaf),
        unbound: model.resolve_node(zz),
        unbound_again: model.resolve_node(zz),
    }
}

#[test]
fn a_million_levels_deep_on_a_default_stack_is_total_and_deterministic() {
    let run = || {
        thread::Builder::new()
            .stack_size(DEFAULT_STACK)
            .spawn(report)
            .expect("spawn")
            .join()
            .expect("no stack overflow or panic")
    };
    let start = std::time::Instant::now();
    let first = run();
    eprintln!("one deep run took {:?}", start.elapsed());
    assert_eq!(first, run(), "deterministic across runs");
    assert!(matches!(first.bound, Resolution::Must(_)));
    assert_eq!(first.unbound, Resolution::Unknown);
    assert_eq!(first.unbound_again, Resolution::Unknown);
    assert_eq!(
        first.free,
        BTreeSet::from(["f".to_owned(), "zz".to_owned()])
    );
    let anons = (1..=DEPTH)
        .filter(|k| k % 5000 != 0 && k % 1001 == 0)
        .count();
    assert_eq!(first.units, 1 + 200 + anons);
    assert_eq!(first.ancestors, DEPTH as usize + 2);
    assert!(first.deepest_symref.starts_with("deep.rs::"));
}
