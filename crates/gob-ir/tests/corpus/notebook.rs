//! A notebook-like term: cells under `group(order=user-history)`, definitions out of order.

use gob_ir::{
    GroupOrder, Label, Location, Model, NodeId, NodeSpec, Operator, Resolution, ScopeGraph, Status,
    Term, Universal,
};
use gob_text::FileInterner;

use crate::support::B;

pub struct Fx {
    pub model: Model,
    pub group: NodeId,
    pub cell1: NodeId,
    pub cell3: NodeId,
    pub use_x: NodeId,
    pub def_x: NodeId,
}

fn cell_loc(nb: gob_text::FileId, cell: u32) -> Location {
    Location::Notebook {
        nb,
        cell,
        range: gob_text::TextRange::new(0u32.into(), 10u32.into()),
    }
}

pub fn build() -> Fx {
    let mut files = FileInterner::new();
    let nb = files.intern("a.ipynb");
    let mut b = B::new("a.ipynb", "python");
    let use_x = b.add(
        NodeSpec::new(Operator::reference("x"), cell_loc(nb, 0)),
        &[],
    );
    let spec = NodeSpec::new(Operator::unit("cell", "impl"), cell_loc(nb, 0)).named("cell1");
    let cell1 = b.add(spec, &[use_x]);
    let two = b.add(
        NodeSpec::new(Operator::lit("int", "2"), cell_loc(nb, 1)),
        &[],
    );
    let spec = NodeSpec::new(Operator::unit("cell", "impl"), cell_loc(nb, 1)).named("cell2");
    let cell2 = b.add(spec, &[two]);
    let one = b.add(
        NodeSpec::new(Operator::lit("int", "1"), cell_loc(nb, 2)),
        &[],
    );
    let def_x = b.add(
        NodeSpec::new(Operator::unit("variable", "impl"), cell_loc(nb, 2)).named("x"),
        &[one],
    );
    let spec = NodeSpec::new(Operator::unit("cell", "impl"), cell_loc(nb, 2)).named("cell3");
    let cell3 = b.add(spec, &[def_x]);
    let spec = NodeSpec::new(Operator::group(GroupOrder::UserHistory), cell_loc(nb, 0));
    let group = b.add(spec, &[cell1, cell2, cell3]);
    let spec = NodeSpec::new(Operator::unit("notebook", "impl"), cell_loc(nb, 0));
    let root = b.add(spec, &[group]);
    let term: Term = b.finish(root);
    // The adapter promotes nothing: with user-driven history a later cell may define a name an
    // earlier cell reads, so the edge between cell scopes is May.
    let mut g = ScopeGraph::from_term(&term);
    let s1 = g.scope_at(cell1).unwrap();
    let s3 = g.scope_at(cell3).unwrap();
    g.add_edge(s1, Label::Custom("notebook".into()), s3, Status::May);
    Fx {
        model: Model::new(term, g),
        group,
        cell1,
        cell3,
        use_x,
        def_x,
    }
}

#[test]
fn group_carries_user_history_order() {
    let fx = build();
    let op = fx.model.term().operator(fx.group);
    assert!(matches!(
        op,
        Operator::Universal(Universal::Group {
            order: GroupOrder::UserHistory
        })
    ));
    assert_eq!(fx.model.term().children(fx.group).len(), 3);
}

#[test]
fn cross_cell_use_is_may_never_must() {
    let fx = build();
    let Resolution::May(set) = fx.model.resolve_node(fx.use_x) else {
        panic!("may")
    };
    let d = fx.model.scopes().decl_at(fx.def_x).unwrap();
    assert_eq!(set.into_iter().collect::<Vec<_>>(), [d]);
}

#[test]
fn notebook_locations_order_by_cell_then_range() {
    let fx = build();
    let t = fx.model.term();
    assert!(t.node(fx.cell1).location() < t.node(fx.cell3).location());
    assert_eq!(
        t.node(fx.cell3).location().to_string(),
        "file#0#cell2:0..10"
    );
}
