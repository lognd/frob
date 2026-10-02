//! A Rust-like file: functions, a type with a qualified method, a lambda, docs and comments.

use gob_ir::{Answer, Facet, FacetDigest, Model, NodeId, Operator, Resolution, Symref, reserved};

use crate::support::B;

pub struct Fx {
    pub model: Model,
    pub add: NodeId,
    pub helper: NodeId,
    pub point_new: NodeId,
    pub lambda: NodeId,
    pub call: NodeId,
    pub head: NodeId,
    pub use_a: NodeId,
    pub use_i32: NodeId,
    pub doc: NodeId,
    pub comment: Option<NodeId>,
}

pub fn build(with_comment: bool, add_name: &str) -> Fx {
    let mut b = B::new("lib.rs", "rust");
    let use_i32 = b.sig(Operator::reference("i32"), &[]);
    let doc = b.doc("adds two numbers");
    let comment = with_comment.then(|| b.node(Operator::comment("// note"), &[]));
    let use_a = b.reference("a");
    let use_b = b.reference("b");
    let head = b.reference("helper");
    let call = b.node(Operator::apply("call"), &[head, use_a, use_b]);
    let use_y = b.reference("y");
    let lambda = b.node(Operator::anon("lambda"), &[use_y]);
    let mut kids = vec![use_i32, doc];
    kids.extend(comment);
    kids.extend([call, lambda]);
    let spec = b
        .spec(Operator::unit("function", "impl"))
        .named(add_name)
        .binders(&["a", "b"])
        .attr("visibility", "pub");
    let add = b.add(spec, &kids);
    let use_x = b.reference("x");
    let helper = b.unit("function", "helper", &["x"], &[use_x]);
    let body = b.lit("0");
    let spec = b
        .spec(Operator::unit("function", "impl"))
        .named("new")
        .attr(reserved::QUALIFIER, "Default");
    let point_new = b.add(spec, &[body]);
    let point = b.unit("type", "Point", &[], &[point_new]);
    let root = b.file_unit(&[add, helper, point]);
    let term = b.finish(root);
    Fx {
        model: Model::lexical(term),
        add,
        helper,
        point_new,
        lambda,
        call,
        head,
        use_a,
        use_i32,
        doc,
        comment,
    }
}

#[test]
fn units_and_symrefs_in_document_order() {
    let fx = build(true, "add");
    let got: Vec<String> = fx
        .model
        .term()
        .units()
        .iter()
        .map(|u| u.symref.to_string())
        .collect();
    assert_eq!(
        got,
        [
            "lib.rs",
            "lib.rs::add",
            "lib.rs::add.{0}",
            "lib.rs::helper",
            "lib.rs::Point",
            "lib.rs::Point.new[Default]",
        ]
    );
    assert_eq!(
        fx.model.term().symref_of(fx.lambda).unwrap().to_string(),
        "lib.rs::add.{0}"
    );
    assert_eq!(
        fx.model.term().symref_of(fx.point_new).unwrap().to_string(),
        "lib.rs::Point.new[Default]"
    );
}

#[test]
fn resolution_is_must_for_lexical_and_unknown_for_external() {
    let fx = build(true, "add");
    let scopes = fx.model.scopes();
    let Resolution::Must(d) = fx.model.resolve_node(fx.head) else {
        panic!("helper must resolve")
    };
    assert_eq!(scopes.decl(d).nodes, [fx.helper]);
    let Resolution::Must(a) = fx.model.resolve_node(fx.use_a) else {
        panic!("a must resolve")
    };
    assert_eq!(scopes.decl(a).name, "a");
    assert_eq!(fx.model.resolve_node(fx.use_i32), Resolution::Unknown);
}

#[test]
fn free_variables_binders_and_occurrences() {
    let fx = build(true, "add");
    let t = fx.model.term();
    let free = |n| t.free_vars(n).into_iter().collect::<Vec<_>>();
    assert_eq!(free(fx.add), ["helper", "i32", "y"]);
    assert_eq!(free(fx.lambda), ["y"]);
    assert_eq!(free(fx.call), ["a", "b", "helper"]);
    let Answer::Exact(bs) = t.binders_in_scope(fx.use_a) else {
        panic!("exact")
    };
    let names: Vec<&str> = bs.iter().map(|b| b.name.as_str()).collect();
    assert_eq!(names, ["b", "a"]);
    let occ = t.occurrences("helper");
    assert_eq!(occ.len(), 2);
}

#[test]
fn attachments_and_facets() {
    let fx = build(true, "add");
    let t = fx.model.term();
    let comment = fx.comment.unwrap();
    assert_eq!(t.attachments(fx.add), [fx.doc, comment]);
    assert_eq!(t.comments(fx.add), [comment]);
    for facet in Facet::ALL {
        assert!(
            matches!(t.facet_digest(fx.add, facet), FacetDigest::Exact(_)),
            "{facet:?}"
        );
    }
    assert_eq!(t.facet_digest(fx.helper, Facet::Doc), FacetDigest::Absent);
    assert_eq!(t.facet_digest(fx.helper, Facet::Attr), FacetDigest::Absent);
}

#[test]
fn trivia_never_changes_a_digest() {
    let with = build(true, "add");
    let without = build(false, "add");
    for facet in Facet::ALL {
        assert_eq!(
            with.model.term().facet_digest(with.add, facet),
            without.model.term().facet_digest(without.add, facet),
            "{facet:?}"
        );
    }
    assert_ne!(with.model.graph_digest(), without.model.graph_digest());
}

#[test]
fn contract_erases_names_but_sig_keeps_them() {
    let a = build(true, "add");
    let b = build(true, "plus");
    let (ta, tb) = (a.model.term(), b.model.term());
    assert_eq!(
        ta.facet_digest(a.add, Facet::Contract),
        tb.facet_digest(b.add, Facet::Contract)
    );
    assert_ne!(
        ta.facet_digest(a.add, Facet::Sig),
        tb.facet_digest(b.add, Facet::Sig)
    );
    assert_eq!(
        ta.facet_digest(a.add, Facet::Body),
        tb.facet_digest(b.add, Facet::Body)
    );
}

#[test]
fn identity_anchors_on_symref_with_body_as_content() {
    let fx = build(true, "add");
    let id = fx.model.identity(fx.add).unwrap();
    let sym: Symref = "lib.rs::add".parse().unwrap();
    assert_eq!(id.anchor, gob_ir::Anchor::Symref(sym));
    assert!(id.content.is_some());
}
