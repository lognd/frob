//! Query tests on a term with nested explicit spans, registries and builder errors.
#![allow(clippy::many_single_char_names, reason = "terse fixtures")]

mod support;

use gob_ir::{
    Anchor, Answer, Digest, Facet, FacetDigest, Identity, IdentityDelta, Location, NodeSpec,
    OccurrenceKind, Operator, Sort, SymrefLookup, TermBuilder, TermError, registry,
};
use gob_text::FileInterner;

/// Spans: file [0,100), `outer` [0,60), `inner` [10,30), literal [12,14), second part of `outer` [60,80).
fn spans() -> (gob_ir::Term, gob_text::FileId, [gob_ir::NodeId; 5]) {
    let mut files = FileInterner::new();
    let f = files.intern("s.rs");
    let mut b = TermBuilder::new("s.rs", "rust");
    let lit = b
        .node(
            NodeSpec::new(Operator::lit("int", "7"), Location::text(f, 12, 14)),
            &[],
        )
        .unwrap();
    let inner = b
        .node(
            NodeSpec::new(
                Operator::unit("function", "impl"),
                Location::text(f, 10, 30),
            )
            .named("inner"),
            &[lit],
        )
        .unwrap();
    let outer = b
        .node(
            NodeSpec::new(
                Operator::unit("function", "signature"),
                Location::text(f, 0, 60),
            )
            .named("outer"),
            &[inner],
        )
        .unwrap();
    let lit2 = b
        .node(
            NodeSpec::new(Operator::lit("int", "8"), Location::text(f, 62, 63)),
            &[],
        )
        .unwrap();
    let outer2 = b
        .node(
            NodeSpec::new(
                Operator::unit("function", "equation"),
                Location::text(f, 60, 80),
            )
            .named("outer"),
            &[lit2],
        )
        .unwrap();
    let root = b
        .node(
            NodeSpec::new(Operator::unit("file", "impl"), Location::text(f, 0, 100)),
            &[outer, outer2],
        )
        .unwrap();
    (
        b.finish(root).unwrap(),
        f,
        [lit, inner, outer, outer2, root],
    )
}

#[test]
fn structure_queries() {
    let (t, _f, [lit, inner, outer, outer2, root]) = spans();
    assert_eq!(t.parent(lit), Some(inner));
    assert_eq!(t.parent(root), None);
    assert_eq!(t.children(root), [outer, outer2]);
    assert_eq!(t.siblings(outer), [outer2]);
    assert_eq!(t.ancestors(lit), [inner, outer, root]);
    assert_eq!(t.descendants(outer), [inner, lit]);
    assert!(t.is_ancestor(root, lit));
    assert!(!t.is_ancestor(lit, root));
    assert_eq!(t.sort(inner), Sort::Decl);
    assert_eq!(t.sort(lit), Sort::Exp);
    assert_eq!(t.operator(lit), &Operator::lit("int", "7"));
}

#[test]
fn location_queries() {
    let (t, f, [lit, inner, outer, _o2, root]) = spans();
    assert_eq!(t.node_at(&Location::text(f, 12, 13)), Some(lit));
    assert_eq!(t.node_at(&Location::text(f, 20, 25)), Some(inner));
    assert_eq!(t.node_at(&Location::text(f, 40, 41)), Some(outer));
    assert_eq!(t.node_at(&Location::text(f, 90, 91)), Some(root));
    assert_eq!(t.node_at(&Location::text(f, 99, 200)), None);
    assert_eq!(t.enclosing_unit_at(&Location::text(f, 12, 13)), Some(inner));
    let order = t.nodes_by_location();
    assert_eq!(
        order.first(),
        Some(&root),
        "wider range first at equal start"
    );
    assert!(Location::text(f, 0, 100).contains(&Location::text(f, 5, 6)));
    assert!(!Location::text(f, 5, 6).contains(&Location::text(f, 0, 100)));
}

#[test]
fn multi_part_units_are_one_identity_with_combined_facets() {
    let (t, _f, [_lit, _inner, outer, outer2, _root]) = spans();
    let sym = "s.rs::outer".parse().unwrap();
    assert_eq!(t.find_unit(&sym), SymrefLookup::One(vec![outer, outer2]));
    assert_eq!(
        t.resolve_symref("s.rs::nope").unwrap(),
        SymrefLookup::NotFound
    );
    assert!(t.resolve_symref("::").is_err());
    let d1 = t.facet_digest(outer, Facet::Body);
    let d2 = t.facet_digest(outer2, Facet::Body);
    let whole = t.identity_facet_digest(&sym, Facet::Body);
    assert!(matches!(whole, FacetDigest::Exact(_)));
    assert_ne!(whole, d1);
    assert_ne!(whole, d2);
    assert_eq!(
        t.identity_facet_digest(&"s.rs::outer.inner".parse().unwrap(), Facet::Body),
        t.facet_digest(inner_of(&t), Facet::Body)
    );
    assert_eq!(
        t.identity_facet_digest(&"s.rs::zzz".parse().unwrap(), Facet::Body),
        FacetDigest::Absent
    );
}

fn inner_of(t: &gob_ir::Term) -> gob_ir::NodeId {
    t.units()
        .into_iter()
        .find(|u| u.symref.to_string() == "s.rs::outer.inner")
        .unwrap()
        .node
}

#[test]
fn by_digest_finds_units_with_equal_facets() {
    let (t, _f, [_, inner, ..]) = spans();
    let FacetDigest::Exact(d) = t.facet_digest(inner, Facet::Body) else {
        panic!()
    };
    assert_eq!(t.by_digest(Facet::Body, &d), [inner]);
    assert!(
        t.by_digest(Facet::Body, &Digest::of("none", b""))
            .is_empty()
    );
}

#[test]
fn occurrences_literals_and_free_variables_of_subterms() {
    let (t, ..) = spans();
    let occ = t.occurrences("outer");
    assert_eq!(occ.len(), 2);
    assert!(occ.iter().all(|o| o.kind == OccurrenceKind::Decl));
    assert_eq!(t.literals(t.root()).len(), 2);
    assert!(t.free_vars(t.root()).is_empty());
    assert_eq!(t.binders_in_scope(t.root()), Answer::Exact(Vec::new()));
}

#[test]
fn identity_delta_distinguishes_change_from_rename() {
    let sym = |s: &str| Anchor::Symref(s.parse().unwrap());
    let d = |s: &str| Some(Digest::of("t", s.as_bytes()));
    let old = Identity::new(sym("a.rs::f"), d("body"));
    assert_eq!(
        old.compare(&Identity::new(sym("a.rs::f"), d("body"))),
        IdentityDelta::Unchanged
    );
    assert_eq!(
        old.compare(&Identity::new(sym("a.rs::f"), d("new"))),
        IdentityDelta::Modified
    );
    assert_eq!(
        old.compare(&Identity::new(sym("a.rs::g"), d("body"))),
        IdentityDelta::Renamed
    );
    assert_eq!(
        old.compare(&Identity::new(sym("a.rs::g"), d("other"))),
        IdentityDelta::Unrelated
    );
}

#[test]
fn symref_grammar_cases() {
    let s: gob_ir::Symref = "notes.md#intro".parse().unwrap();
    assert_eq!(s.locator(), "notes.md#intro");
    let cell: gob_ir::Symref = "nb.ipynb#cell=7".parse().unwrap();
    assert_eq!(cell.to_string(), "nb.ipynb#cell=7");
    let anon: gob_ir::Symref = "a.rs::f.{2}".parse().unwrap();
    assert_eq!(anon.qual().len(), 2);
    let bracket: gob_ir::Symref = "a.rs::Type[Trait<A.B>].m@rust".parse().unwrap();
    assert_eq!(bracket.lang(), Some("rust"));
    assert_eq!(bracket.qual().len(), 2);
    let tagged: gob_ir::Symref = "a.rs@rust".parse().unwrap();
    assert_eq!(tagged.lang(), Some("rust"));
    let scoped: gob_ir::Symref = "node_modules/@scope/pkg.js".parse().unwrap();
    assert_eq!(scoped.lang(), None);
    for bad in [
        "",
        "::x",
        "a.rs::",
        "a.rs::f..g",
        "a.rs::f[x",
        "a.rs::f@1bad",
        "a.rs::{x}",
    ] {
        assert!(bad.parse::<gob_ir::Symref>().is_err(), "{bad}");
    }
    let p = s.child(gob_ir::Segment::Anon(0));
    assert!(s.is_ancestor_of(&p));
    assert_eq!(p.parent(), Some(s));
}

#[test]
fn builder_rejects_malformed_terms() {
    let mut files = FileInterner::new();
    let f = files.intern("e.rs");
    let at = || Location::text(f, 0, 1);
    let mut b = TermBuilder::new("e.rs", "rust");
    let r = b
        .node(NodeSpec::new(Operator::reference("x"), at()), &[])
        .unwrap();
    assert!(matches!(
        b.node(NodeSpec::new(Operator::reference("y"), at()), &[r]),
        Err(TermError::Arity { .. })
    ));
    assert!(matches!(
        b.node(NodeSpec::new(Operator::apply("call"), at()), &[]),
        Err(TermError::Arity { .. })
    ));
    assert!(matches!(
        b.node(
            NodeSpec::new(Operator::lit("int", "1"), at()).binders(&["x"]),
            &[]
        ),
        Err(TermError::BindersNotAllowed(_))
    ));
    assert!(matches!(
        b.node(
            NodeSpec::new(Operator::anon("lambda"), at()).named("n"),
            &[r]
        ),
        Err(TermError::NameNotAllowed(_))
    ));
    let u = b
        .node(NodeSpec::new(Operator::unit("f", "impl"), at()), &[r])
        .unwrap();
    assert!(matches!(
        b.node(NodeSpec::new(Operator::unit("g", "impl"), at()), &[r]),
        Err(TermError::AlreadyParented(_))
    ));
    let stray = b
        .node(NodeSpec::new(Operator::lit("int", "2"), at()), &[])
        .unwrap();
    assert!(matches!(b.finish(u), Err(TermError::Orphan(n)) if n == stray));
}

#[test]
fn atom_registry_and_callee_vocabulary() {
    let net = registry::atom("net.connect").expect("seeded");
    assert!(net.detectors.iter().any(|d| d.lang == "rust"));
    assert!(registry::atoms().windows(2).all(|w| w[0].name <= w[1].name));
    assert!(matches!(
        registry::detectors("net.connect", "rust"),
        Answer::Exact(_)
    ));
    assert_eq!(
        registry::detectors("net.connect", "css"),
        Answer::NotApplicable
    );
    assert_eq!(registry::detectors("net.connect", "cobol"), Answer::Unknown);
    assert_eq!(registry::detectors("no.such.atom", "rust"), Answer::Unknown);
    let Answer::Exact(names) = registry::callee_vocab("rust", "net") else {
        panic!("vocab")
    };
    assert!(names.contains("TcpStream::connect"));
    assert_eq!(registry::callee_vocab("css", "net"), Answer::NotApplicable);
}

// A downstream pack extends the vocabulary by submitting its own entry.
inventory::submit! {
    gob_ir::VocabEntry { lang: "rust", kind: "net", names: &["reqwest::get"] }
}

#[test]
fn packs_extend_vocabularies_through_inventory() {
    let Answer::Exact(names) = registry::callee_vocab("rust", "net") else {
        panic!("vocab")
    };
    assert!(names.contains("reqwest::get") && names.contains("TcpStream::connect"));
}
