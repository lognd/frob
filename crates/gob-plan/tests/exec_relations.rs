//! The executor's relation layer: edge verbs, bounded reaches, side relations, count and knobs.
#![allow(
    clippy::many_single_char_names,
    reason = "short names in table-style tests"
)]

mod support;

use gob_ir::{Model, NodeId, NodeSpec, Operator, Relation, Truth};
use gob_plan::catalog::{Column, FieldType};
use gob_plan::exec::relations::{Count, Knobs, Relations, SideData, SideError, SideTable};
use gob_plan::exec::{Doubt, ExecError, Input, Scalar, count, run, run_with};
use gob_plan::plan::{Certainty, CmpOp, Need, NeedSet, Op, Polarity, Quant};
use support::{Doc, PlanBuilder};

fn func(d: &mut Doc, name: &str, start: u32) -> NodeId {
    d.at_range(
        |loc| NodeSpec::new(Operator::unit("function", "impl"), loc).named(name),
        start,
        start + 5,
        &[],
    )
}

fn model(names: &[&str]) -> (Model, Vec<NodeId>) {
    let mut d = Doc::new("a.rs", "rust");
    let fs: Vec<NodeId> = names
        .iter()
        .enumerate()
        .map(|(i, n)| func(&mut d, n, 100 + 10 * u32::try_from(i).unwrap()))
        .collect();
    let (m, _) = d.root(&fs);
    (m, fs)
}

fn input(model: &Model) -> Input<'_> {
    Input {
        model,
        source: None,
    }
}

fn col(name: &str, ty: FieldType) -> Column {
    Column {
        name: name.to_owned(),
        ty,
    }
}

/// `find t: function`, `find f: function`, `t reaches f via calls within n`.
fn reach_plan(n: u16) -> (gob_plan::plan::Plan, u16, u16) {
    let mut b = PlanBuilder::new("REACH001", Polarity::Pplus);
    let t = b.find("function");
    let f = b.find("function");
    let via = b.s("calls");
    let op = b.op(Op::Reaches {
        from: t,
        to: f,
        via,
        within: n,
        certainty: Certainty::Default,
    });
    b.clause(op);
    b.report(None, f, "reaches");
    (b.build(), t, f)
}

// frob:tests crates/gob-plan/src/exec/relations/edges.rs::reaches
// frob:tests crates/gob-plan/src/exec/core/mod.rs::run_with
#[test]
fn reaches_across_a_may_edge_is_unknown_with_the_edge_on_the_frontier() {
    let (m, fs) = model(&["a", "b", "c"]);
    let mut calls = Relation::new();
    calls.insert(fs[0], fs[1], Truth::Yes);
    calls.insert(fs[1], fs[2], Truth::Unknown);
    let (plan, t, f) = reach_plan(2);
    let rels = Relations::new().with_edges("calls", calls);
    let out = run_with(&plan, &input(&m), &rels).unwrap();

    let find = |from: NodeId, to: NodeId| {
        out.rows
            .iter()
            .find(|r| r.node(t) == Some(from) && r.node(f) == Some(to))
    };
    let ac = find(fs[0], fs[2]).expect("a reaches c only through a May edge");
    assert_eq!(ac.verdict.truth, Truth::Unknown);
    assert_eq!(
        ac.verdict.doubts,
        vec![Doubt::MayEdge {
            from: fs[0],
            to: fs[2]
        }]
    );
    assert_eq!(find(fs[0], fs[1]).unwrap().verdict.truth, Truth::Yes);
    assert!(
        find(fs[2], fs[0]).is_none(),
        "no path even through May edges"
    );
}

// frob:tests crates/gob-plan/src/exec/relations/edges.rs::verb
#[test]
fn a_verb_reads_its_relation_and_peer_of_reads_the_term() {
    let (m, fs) = model(&["a", "b"]);
    let mut calls = Relation::new();
    calls.insert(fs[0], fs[1], Truth::Yes);
    let mut b = PlanBuilder::new("VERB001", Polarity::Pplus);
    let (x, y) = (b.find("function"), b.find("function"));
    let c = b.verb(x, "calls", y, Certainty::Default);
    let p = b.verb(x, "peer of", y, Certainty::Default);
    b.clause(c);
    b.clause(p);
    b.report(None, x, "m");
    let plan = b.build();
    let out = run_with(
        &plan,
        &input(&m),
        &Relations::new().with_edges("calls", calls),
    )
    .unwrap();
    let pairs: Vec<_> = out.rows.iter().map(|r| (r.node(x), r.node(y))).collect();
    assert_eq!(pairs, vec![(Some(fs[0]), Some(fs[1]))]);
}

#[test]
fn a_relation_the_plan_names_but_the_caller_lacks_is_refused() {
    let (m, _) = model(&["a"]);
    let (plan, ..) = reach_plan(2);
    let err = run(&plan, &input(&m)).unwrap_err();
    assert!(
        matches!(&err, ExecError::MissingRelation { name, .. } if name == "calls"),
        "{err}"
    );
}

fn side_plan() -> (gob_plan::plan::Plan, u16) {
    let mut b = PlanBuilder::new("SIDE001", Polarity::Pplus);
    b.needs(NeedSet::of(&[Need::Diff, Need::Lease]));
    let p = b.var();
    let table = b.s("diff.changed");
    let id = b.op(Op::FindSide {
        var: p,
        need: Need::Diff,
        table,
    });
    b.clause(id);
    let status = b.field(p, "status");
    let want = b.str_lit("modified");
    let c = b.cmp(status, CmpOp::Eq, want);
    b.clause(c);
    b.report(None, p, "changed");
    (b.build(), p)
}

// frob:tests crates/gob-plan/src/exec/relations/side.rs::SideData.insert
#[test]
fn find_over_a_side_relation_binds_the_typed_rows() {
    let (m, _) = model(&["a"]);
    let (plan, p) = side_plan();
    let mut side = SideData::new();
    let rows = [
        ("src/a.rs", "modified"),
        ("src/b.rs", "added"),
        ("c.md", "modified"),
    ]
    .iter()
    .map(|(path, st)| vec![Scalar::Str((*path).into()), Scalar::Str((*st).into())])
    .collect();
    let table = SideTable::new(
        vec![col("path", FieldType::Str), col("status", FieldType::Str)],
        rows,
    );
    side.insert("diff.changed", table).unwrap();
    let rels = Relations::new().with_side(side);
    let out = run_with(&plan, &input(&m), &rels).unwrap();
    let got: Vec<u32> = out
        .rows
        .iter()
        .map(|r| match r.vars[usize::from(p)] {
            Some(gob_plan::exec::Val::Row(row)) => row.index,
            other => panic!("unexpected {other:?}"),
        })
        .collect();
    assert_eq!(got, vec![0, 2]);
    assert!(out.rows.iter().all(|r| r.verdict.truth == Truth::Yes));
    // A plan that needs the table without it fails loudly.
    assert!(matches!(
        run(&plan, &input(&m)).unwrap_err(),
        ExecError::MissingRelation {
            what: "side table",
            ..
        }
    ));
}

// frob:tests crates/gob-plan/src/exec/relations/side.rs::SideTable.columns
// frob:tests crates/gob-plan/src/exec/relations/side.rs::SideTable.is_empty
#[test]
fn side_tables_report_their_shape() {
    let t = SideTable::new(vec![col("glob", FieldType::Str)], vec![]);
    assert!(t.is_empty());
    assert_eq!(t.len(), 0);
    assert_eq!(t.columns(), [col("glob", FieldType::Str)]);
}

#[test]
fn side_tables_are_typed_against_the_catalog() {
    let mut side = SideData::new();
    let wrong_cols = SideTable::new(vec![col("path", FieldType::Str)], vec![]);
    assert!(matches!(
        side.insert("diff.changed", wrong_cols),
        Err(SideError::WrongColumns { .. })
    ));
    let bad_row = SideTable::new(
        vec![col("glob", FieldType::Str)],
        vec![vec![Scalar::Int(3)]],
    );
    assert!(matches!(
        side.insert("lease.globs", bad_row),
        Err(SideError::BadRow { row: 0, .. })
    ));
    assert!(matches!(
        side.insert("nope.table", SideTable::new(vec![], vec![])),
        Err(SideError::UnknownRelation { .. })
    ));
    assert!(
        side.insert("config.invariants", SideTable::new(vec![], vec![]))
            .is_ok()
    );
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::count
// frob:tests crates/gob-plan/src/exec/relations/count.rs::Knobs.get
#[test]
fn a_knob_override_changes_a_count_threshold() {
    let (m, fs) = model(&["target", "x", "y", "z"]);
    let mut calls = Relation::new();
    calls.insert(fs[1], fs[0], Truth::Yes);
    calls.insert(fs[2], fs[0], Truth::Yes);
    calls.insert(fs[3], fs[0], Truth::Unknown);

    let mut b = PlanBuilder::new("FANIN001", Polarity::Pplus);
    let f = b.find("function");
    let q = b.quant(Quant::Some, "function", |b, c| {
        b.verb(c, "calls", f, Certainty::Default)
    });
    b.clause(q);
    b.report(None, f, "fan-in");
    let plan = b.build();
    let rels = Relations::new().with_edges("calls", calls);

    let out = run_with(&plan, &input(&m), &rels).unwrap();
    let row = out
        .rows
        .iter()
        .find(|r| r.node(f) == Some(fs[0]))
        .expect("target is called");
    let n = count(&plan, &input(&m), &rels, q, row).unwrap();
    assert_eq!(n, Count { lo: 2, hi: Some(3) });

    let default = rels.knobs().limit("max_fan_in", 5);
    assert_eq!(n.compare(CmpOp::Gt, &default), Truth::No);
    let rels = rels.with_knobs(Knobs::new().with("max_fan_in", 1));
    let tight = rels.knobs().limit("max_fan_in", 5);
    assert_eq!(n.compare(CmpOp::Gt, &tight), Truth::Yes);
    let edge = rels.knobs().limit("other", 2);
    assert_eq!(n.compare(CmpOp::Gt, &edge), Truth::Unknown);

    assert!(matches!(
        count(&plan, &input(&m), &rels, 0, row),
        Err(ExecError::NotCountable { .. })
    ));
}
