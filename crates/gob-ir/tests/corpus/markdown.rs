//! A markdown-like document: nested sections, prose, a link by anchor, a trivia comment.

use gob_ir::{Facet, FacetDigest, Model, NodeId, Operator, Resolution};

use crate::support::B;

pub struct Fx {
    pub model: Model,
    pub intro: NodeId,
    pub setup: NodeId,
    pub usage: NodeId,
    pub link_ref: NodeId,
}

pub fn build() -> Fx {
    let mut b = B::new("docs/guide.md", "markdown");
    let prose = b.node(Operator::lit("prose", "Welcome."), &[]);
    let setup_prose = b.node(Operator::lit("prose", "Install it."), &[]);
    let setup = b.unit("section", "setup", &[], &[setup_prose]);
    let intro = b.unit("section", "intro", &[], &[prose, setup]);
    let link_ref = b.reference("intro");
    let link = b.node(Operator::apply("link"), &[link_ref]);
    let html_comment = b.node(Operator::comment("<!-- frob:todo -->"), &[]);
    let usage = b.unit("section", "usage", &[], &[link, html_comment]);
    let root = b.file_unit(&[intro, usage]);
    let term = b.finish(root);
    Fx {
        model: Model::lexical(term),
        intro,
        setup,
        usage,
        link_ref,
    }
}

#[test]
fn sections_are_units_with_anchor_symrefs() {
    let fx = build();
    let syms: Vec<String> = fx
        .model
        .term()
        .units()
        .iter()
        .map(|u| u.symref.to_string())
        .collect();
    assert_eq!(
        syms,
        [
            "docs/guide.md",
            "docs/guide.md::intro",
            "docs/guide.md::intro.setup",
            "docs/guide.md::usage"
        ]
    );
}

#[test]
fn link_by_anchor_resolves_must() {
    let fx = build();
    let Resolution::Must(d) = fx.model.resolve_node(fx.link_ref) else {
        panic!("must")
    };
    assert_eq!(fx.model.scopes().decl(d).nodes, [fx.intro]);
}

#[test]
fn nested_section_edit_changes_ancestor_body_today() {
    // Open question 5 (G9): the Body facet is subtree-inclusive until the owner decides.
    let fx = build();
    let t = fx.model.term();
    assert!(matches!(
        t.facet_digest(fx.intro, Facet::Body),
        FacetDigest::Exact(_)
    ));
    assert_ne!(
        t.facet_digest(fx.intro, Facet::Body),
        t.facet_digest(fx.setup, Facet::Body)
    );
    assert_eq!(t.literals(fx.intro).len(), 2);
    assert_eq!(t.comments(fx.usage).len(), 1);
}
