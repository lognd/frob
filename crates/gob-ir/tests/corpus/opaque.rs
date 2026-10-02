//! A term with opaque and hole nodes: every claim through them is Unknown or downgraded.

use gob_ir::{
    Answer, AttrValue, Facet, FacetDigest, Model, NodeId, Operator, Resolution, reserved,
};

use crate::support::B;

pub struct Fx {
    pub model: Model,
    pub f: NodeId,
    pub opaque: NodeId,
    pub hole: NodeId,
    pub use_g: NodeId,
    pub use_h: NodeId,
}

pub fn build() -> Fx {
    let mut b = B::new("m.py", "python");
    let g = b.unit("function", "g", &[], &[]);
    let spec = b
        .spec(Operator::opaque(
            "annotation-required:signature",
            b"def f(x): eval(s)",
        ))
        .attr(
            reserved::MAY_DEFINE,
            AttrValue::List(vec![AttrValue::Str("g".into())]),
        );
    let opaque = b.add(spec, &[]);
    let hole = b.node(Operator::hole("parse-error"), &[]);
    let use_g = b.reference("g");
    let use_h = b.reference("h");
    let f = b.unit("function", "f", &[], &[opaque, hole, use_g, use_h]);
    let root = b.file_unit(&[g, f]);
    let term = b.finish(root);
    Fx {
        model: Model::lexical(term),
        f,
        opaque,
        hole,
        use_g,
        use_h,
    }
}

#[test]
fn opaque_may_define_downgrades_must_to_may_and_unknown_stays_unknown() {
    let fx = build();
    assert!(matches!(fx.model.resolve_node(fx.use_g), Resolution::May(s) if s.len() == 1));
    assert_eq!(fx.model.resolve_node(fx.use_h), Resolution::Unknown);
}

#[test]
fn hole_makes_facets_unknown_and_binders_unknown() {
    let fx = build();
    let t = fx.model.term();
    assert_eq!(t.facet_digest(fx.f, Facet::Body), FacetDigest::Unknown);
    assert!(matches!(
        t.facet_digest(fx.f, Facet::Sig),
        FacetDigest::Exact(_)
    ));
    assert_eq!(t.binders_in_scope(fx.hole), Answer::Unknown);
    assert_eq!(t.binders_in_scope(fx.opaque), Answer::Unknown);
}

#[test]
fn lexical_queries_read_the_opaque_payload() {
    let fx = build();
    let t = fx.model.term();
    assert_eq!(t.payload(fx.opaque), Some(&b"def f(x): eval(s)"[..]));
    assert_eq!(t.opaque_regions(fx.f), [fx.opaque]);
}
