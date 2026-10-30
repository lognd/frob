//! Direct tests of small public accessors, so each is reached by a test and bound with `frob:tests`.
// frob:ticket 01M61CD7157CJAPS9Q5MXY03HR

use crate::support::B;
use gob_ir::{
    Answer, Attributes, DeclKind, Digest, Identity, Location, MayCause, Model, OpaqueHint,
    Operator, PoisonReason, Relation, ScopeGraph, Sort, Status, StatusRelation, Symref, Truth,
};
use gob_text::FileInterner;

// frob:tests crates/gob-ir/src/answer.rs::Answer.exact
// frob:tests crates/gob-ir/src/answer.rs::Answer.map
#[test]
fn answer_exact_and_map() {
    assert_eq!(Answer::Exact(2_u32).exact(), Some(2));
    assert_eq!(Answer::<u32>::Unknown.exact(), None);
    assert_eq!(Answer::Exact(2_u32).map(|x| x + 1), Answer::Exact(3));
}

// frob:tests crates/gob-ir/src/answer.rs::Truth.and
// frob:tests crates/gob-ir/src/answer.rs::Truth.or
// frob:tests crates/gob-ir/src/answer.rs::Truth.is_unknown
#[test]
fn truth_connectives() {
    assert_eq!(Truth::Yes.and(Truth::Unknown), Truth::Unknown);
    assert_eq!(Truth::No.and(Truth::Unknown), Truth::No);
    assert_eq!(Truth::Yes.or(Truth::Unknown), Truth::Yes);
    assert_eq!(Truth::No.or(Truth::Unknown), Truth::Unknown);
    assert!(Truth::Unknown.is_unknown());
    assert!(!Truth::Yes.is_unknown());
}

// frob:tests crates/gob-ir/src/attrs.rs::Attributes.is_empty
#[test]
fn attributes_is_empty() {
    assert!(Attributes::default().is_empty());
}

// frob:tests crates/gob-ir/src/defuse.rs::MayCause.as_str
#[test]
fn may_cause_spelling() {
    assert_eq!(MayCause::Closure.as_str(), "closure");
    assert_eq!(MayCause::Mutation.as_str(), "mutation");
    assert_eq!(MayCause::Attribute.as_str(), "attribute");
    assert_eq!(MayCause::DynamicAttribute.as_str(), "dynamic-attribute");
    assert_eq!(MayCause::Kwargs.as_str(), "kwargs");
}

// frob:tests crates/gob-ir/src/digest.rs::Digest.as_bytes
#[test]
fn digest_bytes_match_hex() {
    let d = Digest::of("t", b"x");
    assert_eq!(d.as_bytes().len(), 32);
    assert_eq!(
        d.as_bytes()[0],
        u8::from_str_radix(&d.to_hex()[..2], 16).unwrap()
    );
}

// frob:tests crates/gob-ir/src/eval/ctx.rs::PoisonReason.code
#[test]
fn poison_reason_codes() {
    assert_eq!(PoisonReason::Opaque("macro".into()).code(), "macro");
    assert_eq!(PoisonReason::Hole.code(), "hole");
    assert_eq!(PoisonReason::Edge(Status::May).code(), "edge:may");
    assert_eq!(PoisonReason::Edge(Status::Unknown).code(), "edge:unknown");
}

// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.model
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.op_is
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.children
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.parent
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.loc_before
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.loc_contains
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.holds
// frob:tests crates/gob-ir/src/eval/ctx.rs::Ctx.rel_child
// frob:tests crates/gob-ir/src/eval/relation.rs::Relation.is_empty
#[test]
fn ctx_atoms_over_a_small_term() {
    let mut b = B::new("c.rs", "rust");
    let f = b.unit("function", "f", &[], &[]);
    let o = b.node(Operator::opaque("macro", b"m!()"), &[]);
    let root = b.file_unit(&[f, o]);
    let model = Model::lexical(b.finish(root));
    let ctx = gob_ir::Ctx::new(&model);

    assert!(std::ptr::eq(ctx.model(), &raw const model));
    assert_eq!(ctx.op_is(f, Operator::is_opaque), Truth::No);
    assert_eq!(ctx.op_is(o, Operator::is_opaque), Truth::Unknown);
    assert_eq!(ctx.children(root), Answer::Exact(vec![f, o]));
    assert_eq!(ctx.children(o), Answer::Unknown);
    assert_eq!(ctx.parent(f), Some(root));
    assert_eq!(ctx.parent(root), None);
    assert_eq!(ctx.loc_before(f, o), Truth::Yes);
    assert_eq!(ctx.loc_before(o, f), Truth::No);
    assert_eq!(
        ctx.loc_contains(root, f),
        Truth::from_bool(
            model
                .term()
                .node(root)
                .location()
                .contains(model.term().node(f).location())
        )
    );

    let child = ctx.rel_child();
    assert!(!child.is_empty());
    assert!(Relation::new().is_empty());
    assert_eq!(ctx.holds(&child, root, f), Truth::Yes);
    assert_eq!(ctx.holds(&child, f, root), Truth::No);
}

// frob:tests crates/gob-ir/src/location.rs::Location.artifact
// frob:tests crates/gob-ir/src/location.rs::Location.span
#[test]
fn location_artifact_and_span() {
    let mut files = FileInterner::new();
    let file = files.intern("l.rs");
    let loc = Location::text(file, 1, 4);
    assert_eq!(loc.artifact(), file);
    assert!(loc.span().is_some());
}

// frob:tests crates/gob-ir/src/operator.rs::Sort.name
// frob:tests crates/gob-ir/src/operator.rs::Operator.sort
// frob:tests crates/gob-ir/src/operator.rs::Operator.is_opaque
#[test]
fn operator_sort_and_opacity() {
    assert_eq!(Operator::comment("c").sort(), Sort::Trivia);
    assert_eq!(Sort::Trivia.name(), "trivia");
    assert_eq!(Sort::Decl.name(), "decl");
    assert_eq!(Sort::Use.name(), "use");
    assert_eq!(Sort::Exp.name(), "exp");
    assert_eq!(Sort::Any.name(), "any");
    assert!(Operator::opaque("r", b"p").is_opaque());
    assert!(!Operator::lit("int", "1").is_opaque());
}

// frob:tests crates/gob-ir/src/print.rs::Term.graph_digest
// frob:tests crates/gob-ir/src/term.rs::Node.name
// frob:tests crates/gob-ir/src/term.rs::Node.binders
// frob:tests crates/gob-ir/src/term.rs::Node.parent
// frob:tests crates/gob-ir/src/term.rs::Node.location
// frob:tests crates/gob-ir/src/term.rs::Node.lang_param
// frob:tests crates/gob-ir/src/term.rs::Term.locator
// frob:tests crates/gob-ir/src/term.rs::Term.is_empty
// frob:tests crates/gob-ir/src/term.rs::Term.ids
// frob:tests crates/gob-ir/src/query.rs::Term.attachments
// frob:tests crates/gob-ir/src/query.rs::Term.comments
// frob:tests crates/gob-ir/src/query.rs::Term.payload
#[test]
#[allow(clippy::many_single_char_names)]
fn term_accessors() {
    let mut b = B::new("t.rs", "rust");
    let c = b.node(Operator::comment("note"), &[]);
    let o = b.node(Operator::opaque("r", b"raw"), &[]);
    let f = b.unit("function", "f", &["x"], &[c]);
    let root = b.file_unit(&[f, o]);
    let term = b.finish(root);

    assert_eq!(term.locator(), "t.rs");
    assert!(!term.is_empty());
    assert_eq!(term.ids().count(), term.len());
    let n = term.node(f);
    assert_eq!(n.name(), Some("f"));
    assert_eq!(n.binders(), ["x".to_owned()]);
    assert_eq!(n.parent(), Some(root));
    assert_eq!(n.lang_param(), None);
    assert_eq!(n.location(), term.node(f).location());
    assert_eq!(term.attachments(f), vec![c]);
    assert_eq!(term.comments(f), vec![c]);
    assert_eq!(term.payload(o), Some(&b"raw"[..]));
    assert_eq!(term.payload(f), None);
    let scopes = ScopeGraph::from_term(&term);
    assert_eq!(term.graph_digest(&scopes), term.graph_digest(&scopes));
}

// frob:tests crates/gob-ir/src/scope.rs::ScopeGraph.scope_count
// frob:tests crates/gob-ir/src/scope.rs::ScopeGraph.reference_of
// frob:tests crates/gob-ir/src/scope.rs::ScopeGraph.hints
#[test]
fn scope_graph_counts_refs_and_hints() {
    let mut g = ScopeGraph::new();
    assert_eq!(g.scope_count(), 0);
    let s = g.add_scope(None);
    let _d = g.declare(s, "a", None, DeclKind::Other, Status::Must, None);
    let r = g.reference(s, "a", None);
    g.add_opaque(s, OpaqueHint::default());
    assert_eq!(g.scope_count(), 1);
    assert_eq!(g.reference_of(r).name, "a");
    assert_eq!(g.hints(s).len(), 1);
}

// frob:tests crates/gob-ir/src/status_relation.rs::StatusRelation.truth
// frob:tests crates/gob-ir/src/status_relation.rs::StatusRelation.answer
// frob:tests crates/gob-ir/src/status_relation.rs::StatusRelation.image
// frob:tests crates/gob-ir/src/status_relation.rs::StatusRelation.unknown_out
// frob:tests crates/gob-ir/src/status_relation.rs::StatusRelation.len
// frob:tests crates/gob-ir/src/status_relation.rs::StatusRelation.is_empty
#[test]
fn status_relation_bounds() {
    let mut r: StatusRelation<&str> = StatusRelation::new();
    assert!(r.is_empty());
    r.insert("a", "b", Status::Must);
    r.insert("a", "c", Status::May);
    r.mark_unknown_out("d");
    assert_eq!(r.len(), 2);
    assert!(!r.is_empty());
    assert_eq!(r.truth(&"a", &"b"), Truth::Yes);
    assert_eq!(r.truth(&"a", &"c"), Truth::Unknown);
    assert_eq!(r.truth(&"a", &"z"), Truth::No);
    assert_eq!(
        r.answer(&"a", &"c"),
        Answer::Bounds {
            lo: false,
            hi: true
        }
    );
    assert_eq!(r.image(&"a").count(), 2);
    assert_eq!(r.unknown_out().copied().collect::<Vec<_>>(), vec!["d"]);
}

// frob:tests crates/gob-ir/src/symref.rs::Identity.of_symref
#[test]
fn identity_of_symref() {
    let id = Identity::of_symref(Symref::locator_only("x.rs"), None);
    assert_eq!(id.content, None);
}
