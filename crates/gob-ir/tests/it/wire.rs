//! Serialization round trips of terms and scope graphs (the folded-term cache payload).

// frob:ticket 01M4HB1ZAX0Q6QHK1DK3Y3EZ9E

use gob_ir::{
    AttrValue, DeclKind, Label, Location, MayDefine, NodeSpec, OpaqueHint, Operator, ScopeGraph,
    Status, Term, TermBuilder,
};
use gob_text::FileInterner;

#[allow(clippy::many_single_char_names)]
fn sample() -> (Term, ScopeGraph) {
    let mut files = FileInterner::new();
    let f = files.intern("a.rs");
    let mut b = TermBuilder::new("a.rs", "rust");
    let x = b
        .node(
            NodeSpec::new(Operator::reference("x"), Location::text(f, 4, 5)),
            &[],
        )
        .unwrap();
    let lit = b
        .node(
            NodeSpec::new(
                Operator::Universal(gob_ir::Universal::Lit {
                    kind: "str".into(),
                    lexeme: "\"\u{e9}\"".into(),
                }),
                Location::Pointer {
                    artifact: f,
                    json_pointer: "/a".into(),
                },
            )
            .lang("md")
            .attr("k", AttrValue::List(vec![true.into(), 7_i64.into()])),
            &[],
        )
        .unwrap();
    let anon = b
        .node(
            NodeSpec::new(Operator::anon("block"), Location::text(f, 3, 8)),
            &[x, lit],
        )
        .unwrap();
    let func = b
        .node(
            NodeSpec::new(Operator::unit("function", "impl"), Location::text(f, 0, 9))
                .named("id")
                .binders(&["x"])
                .lang_param("2021"),
            &[anon],
        )
        .unwrap();
    let term = b.finish(func).unwrap();
    let mut g = ScopeGraph::from_term(&term);
    let s = g.add_scope(None);
    let outer = g.add_scope(Some(term.root()));
    g.add_edge(s, Label::Custom("m".into()), outer, Status::May);
    let d = g.declare(
        outer,
        "z",
        Some("q"),
        DeclKind::Unit,
        Status::Must,
        Some(lit),
    );
    g.declare_alias(s, "zz", d);
    g.add_opaque(
        s,
        OpaqueHint {
            may_define: MayDefine::Names(["z".to_owned()].into_iter().collect()),
            may_read_scope: true,
            node: Some(x),
        },
    );
    g.reference(s, "zz", Some(lit));
    (term, g)
}

fn enc(t: &Term, g: &ScopeGraph) -> Vec<u8> {
    postcard::to_stdvec(&(t, g)).unwrap()
}

#[test]
// frob:tests crates/gob-ir/src/wire.rs::TERM_SCHEMA_VERSION
fn round_trip_is_equal_and_deterministic() {
    let (t, g) = sample();
    let bytes = enc(&t, &g);
    assert_eq!(bytes, enc(&t, &g), "encoding is deterministic");
    let (t2, g2): (Term, ScopeGraph) = postcard::from_bytes(&bytes).unwrap();
    assert_eq!(t, t2);
    assert_eq!(bytes, enc(&t2, &g2), "re-encoding is a fixed point");
    assert!(g2.nodes_within(t2.len()));
    let mut resolved = 0;
    for n in t.ids() {
        assert_eq!(g.ref_at(n), g2.ref_at(n));
        assert_eq!(g.decl_at(n), g2.decl_at(n));
        assert_eq!(g.scope_at(n), g2.scope_at(n));
        if let (Some(a), Some(b)) = (g.ref_at(n), g2.ref_at(n)) {
            assert_eq!(g.resolve(a), g2.resolve(b));
            resolved += 1;
        }
    }
    assert!(resolved > 0);
    assert_eq!(g.refs().len(), g2.refs().len());
    assert_eq!(g.decls(), g2.decls());
    assert!(!gob_ir::TERM_SCHEMA_VERSION.to_string().is_empty());
}

#[test]
fn truncated_payload_is_an_error() {
    let (t, g) = sample();
    let bytes = enc(&t, &g);
    for cut in [0, 1, bytes.len() / 2, bytes.len() - 1] {
        assert!(postcard::from_bytes::<(Term, ScopeGraph)>(&bytes[..cut]).is_err());
    }
}

#[test]
fn flipped_bytes_never_panic() {
    let (t, g) = sample();
    let bytes = enc(&t, &g);
    for i in 0..bytes.len() {
        let mut bad = bytes.clone();
        bad[i] ^= 0xff;
        let _ = postcard::from_bytes::<(Term, ScopeGraph)>(&bad);
    }
}

#[test]
// frob:tests crates/gob-ir/src/wire.rs::ScopeGraph.nodes_within
fn mismatched_graph_is_rejected_by_nodes_within() {
    let (t, g) = sample();
    assert!(g.nodes_within(t.len()));
    assert!(!g.nodes_within(1));
}
