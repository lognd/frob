//! A spreadsheet-like grid term: cells as units at grid locations, formulas as applies.

use gob_ir::{
    Answer, GroupOrder, Location, Model, NodeId, NodeSpec, Operator, Resolution, Truth, reserved,
};
use gob_text::FileInterner;

use crate::support::B;

pub struct Fx {
    pub model: Model,
    pub a1: NodeId,
    pub b2: NodeId,
    pub sum_arg: NodeId,
    pub indirect: NodeId,
    pub sheet: gob_text::FileId,
}

pub fn build() -> Fx {
    let mut files = FileInterner::new();
    let sheet = files.intern("book.xlsx#Sheet1");
    let mut b = B::new("book.xlsx#Sheet1", "xlsx");
    let grid = |row, col| Location::Grid { sheet, row, col };
    let one = b.lit("1");
    let spec = NodeSpec::new(Operator::unit("cell", "impl"), grid(0, 0)).named("A1");
    let a1 = b.add(spec, &[one]);
    let sum_arg = b.add(NodeSpec::new(Operator::reference("A1"), grid(1, 1)), &[]);
    let head = b.add(NodeSpec::new(Operator::reference("SUM"), grid(1, 1)), &[]);
    let sum = b.add(
        NodeSpec::new(Operator::apply("call"), grid(1, 1)),
        &[head, sum_arg],
    );
    let spec = NodeSpec::new(Operator::unit("cell", "impl"), grid(1, 1)).named("B2");
    let b2 = b.add(spec, &[sum]);
    let spec = NodeSpec::new(
        Operator::opaque("dynamic:indirect", b"INDIRECT(C1)"),
        grid(2, 2),
    )
    .attr(reserved::MAY_READ_SCOPE, true);
    let indirect = b.add(spec, &[]);
    let cells = b.add(
        NodeSpec::new(Operator::group(GroupOrder::Unordered), grid(0, 0)),
        &[a1, b2, indirect],
    );
    let spec = NodeSpec::new(Operator::unit("sheet", "impl"), grid(0, 0)).named("Sheet1");
    let root = b.add(spec, &[cells]);
    let term = b.finish(root);
    Fx {
        model: Model::lexical(term),
        a1,
        b2,
        sum_arg,
        indirect,
        sheet,
    }
}

#[test]
fn cell_symrefs_and_must_references() {
    let fx = build();
    let t = fx.model.term();
    assert_eq!(
        t.symref_of(fx.a1).unwrap().to_string(),
        "book.xlsx#Sheet1::Sheet1.A1"
    );
    let Resolution::Must(d) = fx.model.resolve_node(fx.sum_arg) else {
        panic!("must")
    };
    assert_eq!(fx.model.scopes().decl(d).nodes, [fx.a1]);
}

#[test]
fn grid_locations_order_row_major_and_contain_only_themselves() {
    let fx = build();
    let t = fx.model.term();
    let (l1, l2) = (
        t.node(fx.a1).location().clone(),
        t.node(fx.b2).location().clone(),
    );
    assert!(l1 < l2);
    assert!(l1.contains(&l1));
    assert!(!l1.contains(&l2));
    assert_eq!(l1.artifact(), fx.sheet);
    let by_loc = t.nodes_by_location();
    assert!(
        by_loc
            .windows(2)
            .all(|w| t.node(w[0]).location() <= t.node(w[1]).location())
    );
}

#[test]
fn opaque_indirect_reads_scope_lexically_and_payload_is_exact() {
    let fx = build();
    let t = fx.model.term();
    assert_eq!(t.payload(fx.indirect), Some(&b"INDIRECT(C1)"[..]));
    assert_eq!(t.opaque_regions(t.root()), [fx.indirect]);
    let decl = fx.model.scopes().decl_at(fx.a1).unwrap();
    assert_eq!(
        fx.model.scopes().may_be_read_by_opaque(decl),
        Truth::Unknown
    );
    assert_eq!(t.binders_in_scope(fx.indirect), Answer::Unknown);
}
