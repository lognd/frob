//! Scope graph tests: Must, May and Unknown resolution, shadowing, hints.
#![allow(clippy::many_single_char_names, reason = "terse graphs")]

use gob_ir::{
    DeclKind, Label, MayDefine, OpaqueHint, Resolution, ScopeGraph, ScopeId, Status, Truth,
};

fn nested() -> (ScopeGraph, ScopeId, ScopeId) {
    let mut g = ScopeGraph::new();
    let outer = g.add_scope(None);
    let inner = g.add_scope(None);
    g.add_edge(inner, Label::Lexical, outer, Status::Must);
    (g, outer, inner)
}

fn decl(g: &mut ScopeGraph, s: ScopeId, name: &str, st: Status) -> gob_ir::DeclId {
    g.declare(s, name, None, DeclKind::Other, st, None)
}

#[test]
fn must_through_lexical_nesting() {
    let (mut g, outer, inner) = nested();
    let f = decl(&mut g, outer, "f", Status::Must);
    let r = g.reference(inner, "f", None);
    assert_eq!(g.resolve(r), Resolution::Must(f));
    assert_eq!(g.resolve(r).status(), Status::Must);
}

#[test]
fn nearer_must_declaration_shadows() {
    let (mut g, outer, inner) = nested();
    let _far = decl(&mut g, outer, "x", Status::Must);
    let near = decl(&mut g, inner, "x", Status::Must);
    let r = g.reference(inner, "x", None);
    assert_eq!(g.resolve(r), Resolution::Must(near));
}

#[test]
fn nearer_may_declaration_does_not_shadow() {
    let (mut g, outer, inner) = nested();
    let far = decl(&mut g, outer, "x", Status::Must);
    let near = decl(&mut g, inner, "x", Status::May);
    let r = g.reference(inner, "x", None);
    assert_eq!(
        g.resolve(r),
        Resolution::May([far, near].into_iter().collect())
    );
}

#[test]
fn two_must_declarations_are_ambiguous_so_may() {
    let (mut g, _outer, inner) = nested();
    let a = g.declare(inner, "m", Some("A"), DeclKind::Other, Status::Must, None);
    let b = g.declare(inner, "m", Some("B"), DeclKind::Other, Status::Must, None);
    let r = g.reference(inner, "m", None);
    assert_eq!(g.resolve(r), Resolution::May([a, b].into_iter().collect()));
}

#[test]
fn multi_part_unit_is_one_declaration() {
    let (mut g, _outer, inner) = nested();
    let a = g.declare(inner, "p", None, DeclKind::Unit, Status::Must, None);
    let b = g.declare(inner, "p", None, DeclKind::Unit, Status::Must, None);
    assert_eq!(a, b);
    let r = g.reference(inner, "p", None);
    assert_eq!(g.resolve(r), Resolution::Must(a));
}

#[test]
fn undeclared_names_and_unknown_edges_are_unknown() {
    let (mut g, outer, inner) = nested();
    let r = g.reference(inner, "ghost", None);
    assert_eq!(g.resolve(r), Resolution::Unknown);
    let far = g.add_scope(None);
    decl(&mut g, far, "y", Status::Must);
    g.add_edge(
        outer,
        Label::Custom("dispatch".into()),
        far,
        Status::Unknown,
    );
    let y = g.reference(inner, "y", None);
    assert_eq!(g.resolve(y), Resolution::Unknown);
}

#[test]
fn unknown_status_declaration_is_unknown() {
    let (mut g, _outer, inner) = nested();
    decl(&mut g, inner, "z", Status::Unknown);
    let r = g.reference(inner, "z", None);
    assert_eq!(g.resolve(r), Resolution::Unknown);
}

#[test]
fn may_edge_downgrades_a_found_declaration() {
    let (mut g, _outer, inner) = nested();
    let other = g.add_scope(None);
    let d = decl(&mut g, other, "w", Status::Must);
    g.add_edge(inner, Label::Import, other, Status::May);
    let r = g.reference(inner, "w", None);
    assert_eq!(g.resolve(r), Resolution::May([d].into_iter().collect()));
}

#[test]
fn must_import_shadows_lexical_but_may_import_does_not() {
    let (mut g, outer, inner) = nested();
    let lex = decl(&mut g, outer, "n", Status::Must);
    let imported = g.add_scope(None);
    let imp = decl(&mut g, imported, "n", Status::Must);
    g.add_edge(inner, Label::Import, imported, Status::Must);
    let r = g.reference(inner, "n", None);
    assert_eq!(g.resolve(r), Resolution::Must(imp));
    let (mut g2, outer2, inner2) = nested();
    let lex2 = decl(&mut g2, outer2, "n", Status::Must);
    let imported2 = g2.add_scope(None);
    let imp2 = decl(&mut g2, imported2, "n", Status::Must);
    g2.add_edge(inner2, Label::Import, imported2, Status::May);
    let r2 = g2.reference(inner2, "n", None);
    assert_eq!(
        g2.resolve(r2),
        Resolution::May([lex2, imp2].into_iter().collect())
    );
    let _ = lex;
}

#[test]
fn opaque_may_define_downgrades_only_the_names_it_covers() {
    let (mut g, outer, inner) = nested();
    let a = decl(&mut g, outer, "a", Status::Must);
    let b = decl(&mut g, outer, "b", Status::Must);
    let hint = OpaqueHint {
        may_define: MayDefine::Names(["a".to_owned()].into_iter().collect()),
        may_read_scope: false,
        node: None,
    };
    g.add_opaque(inner, hint);
    let ra = g.reference(inner, "a", None);
    let rb = g.reference(inner, "b", None);
    assert_eq!(g.resolve(ra), Resolution::May([a].into_iter().collect()));
    assert_eq!(g.resolve(rb), Resolution::Must(b));
}

#[test]
fn opaque_may_define_any_makes_undeclared_names_unknown_and_declared_ones_may() {
    let (mut g, outer, inner) = nested();
    let a = decl(&mut g, outer, "a", Status::Must);
    g.add_opaque(
        inner,
        OpaqueHint {
            may_define: MayDefine::Any,
            may_read_scope: false,
            node: None,
        },
    );
    let ra = g.reference(inner, "a", None);
    let rz = g.reference(inner, "zzz", None);
    assert_eq!(g.resolve(ra), Resolution::May([a].into_iter().collect()));
    assert_eq!(g.resolve(rz), Resolution::Unknown);
}

#[test]
fn opaque_reader_makes_declarations_possibly_used() {
    let (mut g, outer, inner) = nested();
    let a = decl(&mut g, outer, "a", Status::Must);
    let lonely = g.add_scope(None);
    let b = decl(&mut g, lonely, "b", Status::Must);
    assert_eq!(g.may_be_read_by_opaque(a), Truth::No);
    g.add_opaque(
        inner,
        OpaqueHint {
            may_define: MayDefine::Nothing,
            may_read_scope: true,
            node: None,
        },
    );
    assert_eq!(g.may_be_read_by_opaque(a), Truth::Unknown);
    assert_eq!(g.may_be_read_by_opaque(b), Truth::No);
}

#[test]
fn scope_cycles_terminate() {
    let (mut g, outer, inner) = nested();
    g.add_edge(outer, Label::Import, inner, Status::Must);
    let r = g.reference(inner, "nothing", None);
    assert_eq!(g.resolve(r), Resolution::Unknown);
}

#[test]
fn status_is_ordered_and_meets_to_the_weaker() {
    assert!(Status::Unknown < Status::May && Status::May < Status::Must);
    assert_eq!(Status::Must.meet(Status::May), Status::May);
    assert_eq!(Status::Unknown.meet(Status::Must), Status::Unknown);
}
