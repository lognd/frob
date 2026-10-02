//! Property tests: alpha-invariance of printer and facet digests, determinism, symref round trip.
#![allow(clippy::many_single_char_names, reason = "terse generators")]

mod support;

use gob_ir::{Digest, Facet, FacetDigest, FacetStream, Model, NodeId, Operator, Symref, Term};
use proptest::prelude::*;
use support::B;

/// A generated tree; names are indices into small pools.
#[derive(Debug, Clone)]
enum T {
    Unit {
        name: String,
        binders: Vec<String>,
        kids: Vec<T>,
    },
    Bind {
        name: String,
        scope: Vec<T>,
        rhs: Option<Box<T>>,
    },
    Ref(String),
    Lit(String),
    Comment(String),
    Doc(String),
    Apply(Vec<T>),
    SigGroup(Vec<T>),
}

fn var() -> impl Strategy<Value = String> {
    prop::sample::select(vec!["v0", "v1", "v2", "v3"]).prop_map(str::to_owned)
}

fn any_ref() -> impl Strategy<Value = String> {
    prop_oneof![3 => var(), 1 => prop::sample::select(vec!["free0", "free1"]).prop_map(str::to_owned)]
}

fn tree() -> impl Strategy<Value = T> {
    let leaf = prop_oneof![
        any_ref().prop_map(T::Ref),
        "[a-z ]{0,6}".prop_map(T::Lit),
        "[a-z ]{0,6}".prop_map(T::Comment),
        "[a-z ]{0,6}".prop_map(T::Doc),
    ];
    leaf.prop_recursive(4, 40, 4, |inner| {
        prop_oneof![
            (
                "[a-z]{1,4}",
                prop::collection::vec(var(), 0..3),
                prop::collection::vec(inner.clone(), 0..4)
            )
                .prop_map(|(name, binders, kids)| T::Unit {
                    name,
                    binders,
                    kids
                }),
            (
                var(),
                prop::collection::vec(inner.clone(), 1..3),
                prop::option::of(inner.clone())
            )
                .prop_map(|(name, scope, rhs)| T::Bind {
                    name,
                    scope,
                    rhs: rhs.map(Box::new)
                }),
            prop::collection::vec(inner.clone(), 0..4).prop_map(T::Apply),
            prop::collection::vec(inner, 0..3).prop_map(T::SigGroup),
        ]
    })
}

/// Rename every binder consistently, leaving free references alone.
fn fresh(old: &str, env: &mut Vec<(String, String)>, counter: &mut u32) -> String {
    *counter += 1;
    let new = format!("renamed_{counter}_{old}");
    env.push((old.to_owned(), new.clone()));
    new
}

fn rename(t: &T, env: &mut Vec<(String, String)>, counter: &mut u32) -> T {
    match t {
        T::Unit {
            name,
            binders,
            kids,
        } => {
            let depth = env.len();
            let nb: Vec<String> = binders.iter().map(|b| fresh(b, env, counter)).collect();
            let nk = kids.iter().map(|k| rename(k, env, counter)).collect();
            env.truncate(depth);
            T::Unit {
                name: name.clone(),
                binders: nb,
                kids: nk,
            }
        }
        T::Bind { name, scope, rhs } => {
            let nrhs = rhs.as_ref().map(|r| Box::new(rename(r, env, counter)));
            let depth = env.len();
            let nn = fresh(name, env, counter);
            let ns = scope.iter().map(|k| rename(k, env, counter)).collect();
            env.truncate(depth);
            T::Bind {
                name: nn,
                scope: ns,
                rhs: nrhs,
            }
        }
        T::Ref(n) => {
            let hit = env
                .iter()
                .rev()
                .find(|(o, _)| o == n)
                .map(|(_, new)| new.clone());
            T::Ref(hit.unwrap_or_else(|| n.clone()))
        }
        T::Apply(k) => T::Apply(k.iter().map(|c| rename(c, env, counter)).collect()),
        T::SigGroup(k) => T::SigGroup(k.iter().map(|c| rename(c, env, counter)).collect()),
        other => other.clone(),
    }
}

fn strip_comments(t: &T) -> Option<T> {
    Some(match t {
        T::Comment(_) => return None,
        T::Unit {
            name,
            binders,
            kids,
        } => T::Unit {
            name: name.clone(),
            binders: binders.clone(),
            kids: kids.iter().filter_map(strip_comments).collect(),
        },
        T::Bind { name, scope, rhs } => T::Bind {
            name: name.clone(),
            scope: scope.iter().filter_map(strip_comments).collect(),
            rhs: rhs.as_ref().and_then(|r| strip_comments(r)).map(Box::new),
        },
        T::Apply(k) => T::Apply(k.iter().filter_map(strip_comments).collect()),
        T::SigGroup(k) => T::SigGroup(k.iter().filter_map(strip_comments).collect()),
        other => other.clone(),
    })
}

fn emit(b: &mut B, t: &T) -> NodeId {
    match t {
        T::Unit {
            name,
            binders,
            kids,
        } => {
            let ids: Vec<NodeId> = kids.iter().map(|k| emit(b, k)).collect();
            let bs: Vec<&str> = binders.iter().map(String::as_str).collect();
            b.unit("function", name, &bs, &ids)
        }
        T::Bind { name, scope, rhs } => {
            // scope children are wrapped in one group so `bind` has the (scope; rhs?) shape.
            let ids: Vec<NodeId> = scope.iter().map(|k| emit(b, k)).collect();
            let g = b.group(gob_ir::GroupOrder::Sequence, &ids);
            let mut kids = vec![g];
            if let Some(r) = rhs {
                kids.push(emit(b, r));
            }
            let spec = b
                .spec(Operator::bind("let", "once"))
                .binders(&[name.as_str()]);
            b.add(spec, &kids)
        }
        T::Ref(n) => b.reference(n),
        T::Lit(s) => b.lit(s),
        T::Comment(s) => b.node(Operator::comment(s), &[]),
        T::Doc(s) => b.doc(s),
        T::Apply(k) => {
            let mut ids = vec![b.reference("head")];
            ids.extend(k.iter().map(|c| emit(b, c)));
            b.node(Operator::apply("call"), &ids)
        }
        T::SigGroup(k) => {
            let ids: Vec<NodeId> = k.iter().map(|c| emit(b, c)).collect();
            b.sig(Operator::group(gob_ir::GroupOrder::Unordered), &ids)
        }
    }
}

fn build(forest: &[T]) -> Model {
    let mut b = B::new("p.rs", "rust");
    let ids: Vec<NodeId> = forest.iter().map(|t| emit(&mut b, t)).collect();
    let root = b.file_unit(&ids);
    Model::lexical(b.finish(root))
}

fn all_digests(term: &Term) -> Vec<String> {
    term.units()
        .iter()
        .flat_map(|u| {
            Facet::ALL.map(|f| format!("{}:{:?}", u.symref, term.facet_digest(u.node, f)))
        })
        .collect()
}

proptest! {
    #![proptest_config(ProptestConfig { failure_persistence: None, ..ProptestConfig::default() })]
    #[test]
    fn alpha_equivalent_terms_print_and_digest_identically(forest in prop::collection::vec(tree(), 0..4)) {
        let mut counter = 0;
        let renamed: Vec<T> = forest.iter().map(|t| rename(t, &mut Vec::new(), &mut counter)).collect();
        let (a, b) = (build(&forest), build(&renamed));
        prop_assert_eq!(a.term().print_alpha(a.term().root()), b.term().print_alpha(b.term().root()));
        prop_assert_eq!(all_digests(a.term()), all_digests(b.term()));
        prop_assert_eq!(a.graph_digest(), b.graph_digest());
    }

    #[test]
    fn building_twice_is_deterministic(forest in prop::collection::vec(tree(), 0..4)) {
        let (a, b) = (build(&forest), build(&forest));
        prop_assert_eq!(a.term().print_alpha(a.term().root()), b.term().print_alpha(b.term().root()));
        prop_assert_eq!(a.graph_digest(), b.graph_digest());
        prop_assert_eq!(all_digests(a.term()), all_digests(b.term()));
    }

    #[test]
    fn trivia_is_outside_every_facet_digest(forest in prop::collection::vec(tree(), 0..4)) {
        let stripped: Vec<T> = forest.iter().filter_map(strip_comments).collect();
        let (a, b) = (build(&forest), build(&stripped));
        prop_assert_eq!(all_digests(a.term()), all_digests(b.term()));
    }

    #[test]
    fn symref_display_parse_round_trip(
        loc in "[a-z]{1,5}(/[a-z]{1,5}){0,2}\\.rs(#[a-z]{1,4})?",
        segs in prop::collection::vec(
            prop_oneof![
                ("[a-zA-Z_][a-zA-Z0-9_]{0,5}", prop::option::of("[A-Za-z0-9_:<>, ]{1,6}"))
                    .prop_map(|(name, qualifier)| gob_ir::Segment::Name { name, qualifier }),
                (0u32..50).prop_map(gob_ir::Segment::Anon),
            ],
            0..4,
        ),
        lang in prop::option::of("[a-z]{2,6}"),
    ) {
        let s = Symref::new(loc, segs, lang);
        let parsed: Symref = s.to_string().parse().unwrap();
        prop_assert_eq!(parsed, s);
    }
}

#[test]
fn a_token_change_always_changes_the_body_digest() {
    let mk = |lit: &str| {
        let mut b = B::new("p.rs", "rust");
        let l = b.lit(lit);
        let u = b.unit("function", "f", &[], &[l]);
        let root = b.file_unit(&[u]);
        (Model::lexical(b.finish(root)), u)
    };
    let (m1, u1) = mk("1");
    let (m2, u2) = mk("2");
    assert_ne!(
        m1.term().facet_digest(u1, Facet::Body),
        m2.term().facet_digest(u2, Facet::Body)
    );
}

#[test]
fn golden_digest_is_stable_across_runs() {
    let mut b = B::new("g.rs", "rust");
    let x = b.reference("x");
    let u = b.unit("function", "id", &["x"], &[x]);
    let root = b.file_unit(&[u]);
    let m = Model::lexical(b.finish(root));
    assert_eq!(
        m.term().print_alpha(u),
        r#"(unit "function" "impl" @rust name="id" \1 (ref #0))"#
    );
    assert_eq!(
        m.term().print_alpha(m.term().root()),
        r#"(unit "file" "impl" @rust (unit "function" "impl" name="id" \1 (ref #0)))"#
    );
    let d = m.term().facet_digest(u, Facet::Body);
    assert_eq!(
        d,
        FacetDigest::Exact(Digest::of("gob-ir/2/body", br#"(body (ref #0))"#))
    );
    assert_eq!(
        m.term().facet_stream(u, Facet::Body),
        FacetStream::Stream(r#"(body (ref #0))"#.to_owned())
    );
    assert_eq!(format!("{d:?}"), "Exact(Digest(de4d74a833fd))");
}
