//! The executor core: binding order, containment, position and the Kleene connectives.
#![allow(
    clippy::many_single_char_names,
    clippy::match_same_arms,
    reason = "short names in table-style tests"
)]

mod support;

use gob_ir::{Model, NodeId, NodeSpec, Operator, Truth};
use gob_plan::exec::{Input, Row, run};
use gob_plan::plan::{CmpOp, Op, OpId, Polarity, Position, Quant};
use gob_text::SourceText;
use proptest::prelude::*;
use proptest::test_runner::TestCaseError;
use support::{Doc, PlanBuilder};

fn rows(plan: &gob_plan::plan::Plan, model: &Model) -> Vec<Row> {
    run(
        plan,
        &Input {
            model,
            source: None,
        },
    )
    .unwrap()
    .rows
}

fn func(d: &mut Doc, name: &str, vis: &str, start: u32, end: u32, kids: &[NodeId]) -> NodeId {
    d.at_range(
        |loc| {
            NodeSpec::new(Operator::unit("function", "impl"), loc)
                .named(name)
                .attr("visibility", vis)
        },
        start,
        end,
        kids,
    )
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
#[test]
fn find_binds_the_public_functions_in_location_order() {
    let mut d = Doc::new("a.rs", "rust");
    // Built out of source order on purpose: ids and locations disagree.
    let late = func(&mut d, "late", "public", 300, 310, &[]);
    let hidden = func(&mut d, "hidden", "private", 200, 210, &[]);
    let early = func(&mut d, "early", "public", 100, 110, &[]);
    let (model, _) = d.root(&[late, hidden, early]);

    let mut b = PlanBuilder::new("PUB001", Polarity::Pplus);
    let f = b.find("function");
    let (public, yes) = (b.field(f, "public"), gob_plan::plan::Operand::Bool(true));
    let c = b.cmp(public, CmpOp::Eq, yes);
    b.clause(c);
    b.report(None, f, "public function");
    let out = rows(&b.build(), &model);

    let bound: Vec<NodeId> = out.iter().filter_map(|r| r.node(f)).collect();
    assert_eq!(bound, vec![early, late]);
    assert!(out.iter().all(|r| r.verdict.truth == Truth::Yes));
}

/// A function holding a statement holding a call: `call` is inside `fn` at depth 2.
fn nested() -> (Model, NodeId, NodeId, NodeId) {
    let mut d = Doc::new("a.rs", "rust");
    let head = d.at_range(|l| NodeSpec::new(Operator::reference("g"), l), 20, 21, &[]);
    let call = d.at_range(
        |l| NodeSpec::new(Operator::apply("call"), l),
        20,
        30,
        &[head],
    );
    let stmt = d.at_range(
        |l| NodeSpec::new(Operator::anon("block"), l),
        10,
        40,
        &[call],
    );
    let f = func(&mut d, "f", "public", 0, 50, &[stmt]);
    let (model, _) = d.root(&[f]);
    (model, f, stmt, call)
}

fn containment(direct: bool) -> (usize, Vec<NodeId>) {
    let (model, ..) = nested();
    let mut b = PlanBuilder::new("IN001", Polarity::Pplus);
    let c = b.find("call");
    let f = b.find("function");
    let inside = b.inside(c, f, direct);
    b.clause(inside);
    b.report(None, c, "call in function");
    let out = rows(&b.build(), &model);
    (out.len(), out.iter().filter_map(|r| r.node(c)).collect())
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
#[test]
fn inside_looks_through_any_depth_and_directly_inside_one_level() {
    let (n, _) = containment(false);
    assert_eq!(n, 1, "transitive: the call is inside the function");
    let (n, _) = containment(true);
    assert_eq!(n, 0, "direct: the call is two levels down");
}

#[test]
fn position_orders_whole_nodes_of_one_file() {
    let mut d = Doc::new("a.rs", "rust");
    let a = func(&mut d, "a", "public", 0, 10, &[]);
    let b_ = func(&mut d, "b", "public", 12, 20, &[]);
    let c = func(&mut d, "c", "public", 40, 50, &[]);
    let (model, _) = d.root(&[a, b_, c]);
    let text = "fn a() {}\n\nfn b() {}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n";
    let source = SourceText::new(text).unwrap();

    let count = |pos: Position, src: Option<&SourceText>| {
        let mut b = PlanBuilder::new("POS001", Polarity::Pplus);
        let x = b.find("function");
        let y = b.find("function");
        let o = b.order(x, y, pos);
        b.clause(o);
        b.report(None, x, "ordered");
        let plan = b.build();
        let out = run(
            &plan,
            &Input {
                model: &model,
                source: src,
            },
        )
        .unwrap();
        out.rows
            .iter()
            .map(|r| (r.node(x).unwrap(), r.node(y).unwrap(), r.verdict.truth))
            .collect::<Vec<_>>()
    };
    let before = count(Position::Before, None);
    assert_eq!(before.len(), 3, "a<b, a<c, b<c");
    assert!(before.contains(&(a, c, Truth::Yes)));
    let after = count(Position::After, None);
    assert!(after.contains(&(c, a, Truth::Yes)) && after.len() == 3);
    // Without the text `adjoins` cannot say; with it a(line 1) and b(line 3) are two apart.
    assert!(
        count(Position::Adjoins, None)
            .iter()
            .all(|r| r.2 == Truth::Unknown)
    );
    let adj = count(Position::Adjoins, Some(&source));
    assert!(
        adj.iter().all(|r| r.0 == r.1),
        "only a node with itself adjoins; a and b are two lines apart"
    );
}

#[test]
fn a_quantifier_over_a_model_with_an_unread_region_cannot_say_none() {
    let build = |hole: bool| {
        let mut d = Doc::new("a.rs", "rust");
        let f = func(&mut d, "f", "public", 0, 50, &[]);
        let mut kids = vec![f];
        if hole {
            kids.push(d.add(
                Operator::opaque("annotation-required:signature", b"?"),
                None,
                &[],
            ));
        }
        d.root(&kids).0
    };
    let mut b = PlanBuilder::new("HID001", Polarity::Pminus);
    let f = b.find("function");
    let none = b.quant(Quant::No, "test", |b, _| {
        let _ = &b;
        b.op(Op::And(Vec::new()))
    });
    b.clause(none);
    b.report(None, f, "no test");
    let plan = b.build();

    let closed = rows(&plan, &build(false));
    assert_eq!(
        closed[0].verdict.truth,
        Truth::Yes,
        "no tests anywhere is certain"
    );
    let open = run(
        &plan,
        &Input {
            model: &build(true),
            source: None,
        },
    )
    .unwrap();
    assert!(open.hidden);
    assert_eq!(
        open.rows[0].verdict.truth,
        Truth::Unknown,
        "a hidden region may hold a test"
    );
}

// A random boolean tree over three leaf values, lowered to plan ops and to a reference Truth.
#[derive(Debug, Clone)]
enum T {
    Leaf(Truth),
    Not(Box<T>),
    And(Vec<T>),
    Or(Vec<T>),
    Some_(Vec<T>),
    No_(Vec<T>),
}

fn reference(t: &T) -> Truth {
    match t {
        T::Leaf(v) => *v,
        T::Not(x) => !reference(x),
        T::And(xs) => Truth::all(xs.iter().map(reference)),
        T::Or(xs) => Truth::any(xs.iter().map(reference)),
        // `some x in a fixed domain of candidates`: the or over candidates (closed model).
        T::Some_(xs) => Truth::any(xs.iter().map(reference)),
        T::No_(xs) => !Truth::any(xs.iter().map(reference)),
    }
}

fn lower(b: &mut PlanBuilder, anchor: u16, t: &T) -> OpId {
    match t {
        T::Leaf(v) => {
            let (l, r) = match v {
                Truth::Yes => (
                    gob_plan::plan::Operand::Int(1),
                    gob_plan::plan::Operand::Int(1),
                ),
                Truth::No => (
                    gob_plan::plan::Operand::Int(1),
                    gob_plan::plan::Operand::Int(2),
                ),
                Truth::Unknown => (
                    b.field(anchor, "no-such-field"),
                    gob_plan::plan::Operand::Int(1),
                ),
            };
            b.cmp(l, CmpOp::Eq, r)
        }
        T::Not(x) => {
            let i = lower(b, anchor, x);
            b.op(Op::Not(i))
        }
        T::And(xs) => {
            let c = xs.iter().map(|x| lower(b, anchor, x)).collect();
            b.op(Op::And(c))
        }
        T::Or(xs) => {
            let c = xs.iter().map(|x| lower(b, anchor, x)).collect();
            b.op(Op::Or(c))
        }
        // A quantifier over `function`: the model has exactly one function, so `some` is the
        // body's value at that single candidate.
        T::Some_(xs) | T::No_(xs) => {
            let quant = if matches!(t, T::Some_(_)) {
                Quant::Some
            } else {
                Quant::No
            };
            let or = T::Or(xs.clone());
            b.quant(quant, "function", |b, v| lower(b, v, &or))
        }
    }
}

fn tree() -> impl Strategy<Value = T> {
    let leaf = prop_oneof![
        Just(T::Leaf(Truth::Yes)),
        Just(T::Leaf(Truth::No)),
        Just(T::Leaf(Truth::Unknown)),
    ];
    leaf.prop_recursive(4, 24, 3, |inner| {
        prop_oneof![
            inner.clone().prop_map(|x| T::Not(Box::new(x))),
            proptest::collection::vec(inner.clone(), 0..4).prop_map(T::And),
            proptest::collection::vec(inner.clone(), 0..4).prop_map(T::Or),
            proptest::collection::vec(inner.clone(), 1..3).prop_map(T::Some_),
            proptest::collection::vec(inner, 1..3).prop_map(T::No_),
        ]
    })
}

fn check_tree(t: &T) -> Result<(), TestCaseError> {
    let mut d = Doc::new("a.rs", "rust");
    let f = func(&mut d, "f", "public", 0, 50, &[]);
    let (model, _) = d.root(&[f]);
    let mut b = PlanBuilder::new("KLEENE001", Polarity::Pplus);
    let anchor = b.find("function");
    let c = lower(&mut b, anchor, t);
    b.clause(c);
    b.report(None, anchor, "x");
    let out = rows(&b.build(), &model);
    match reference(t) {
        Truth::No => prop_assert!(out.is_empty()),
        w => {
            prop_assert_eq!(out.len(), 1);
            prop_assert_eq!(out[0].verdict.truth, w);
        }
    }
    Ok(())
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
#[test]
fn executor_connectives_follow_the_kleene_tables() {
    let mut runner = proptest::test_runner::TestRunner::default();
    runner.run(&tree(), |t| check_tree(&t)).unwrap();
}
