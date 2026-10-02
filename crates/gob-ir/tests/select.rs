//! Unit-level selectors and owner over hand-built terms (grmb-spec 6.4 and 6.5).

// frob:ticket 01M3Z713RETBN30XBC6CK11FBF

use std::collections::BTreeSet;

use gob_ir::{
    HiddenReason, Label, Location, NodeId, NodeSpec, Operator, ScopeGraph, Status, Symref, Term,
    TermBuilder, owner_of_unit, select, select_units,
};
use gob_text::FileInterner;
use gob_walk::{Digest, EntityName, FileEntry, LanguageHint, Owner, Selector, WalkResult};

struct Fx {
    b: TermBuilder,
    f: gob_text::FileId,
    pos: u32,
}

impl Fx {
    fn new(locator: &str, lang: &str) -> Self {
        let mut files = FileInterner::new();
        let f = files.intern(locator);
        Self {
            b: TermBuilder::new(locator, lang),
            f,
            pos: 0,
        }
    }

    fn loc(&mut self) -> Location {
        self.pos += 2;
        Location::text(self.f, self.pos, self.pos + 1)
    }

    fn unit(&mut self, kind: &str, name: &str, vis: Option<&str>, kids: &[NodeId]) -> NodeId {
        let loc = self.loc();
        let mut spec = NodeSpec::new(Operator::unit(kind, "impl"), loc).named(name);
        if let Some(v) = vis {
            spec = spec.attr("visibility", v);
        }
        self.b.node(spec, kids).unwrap()
    }

    fn root(mut self, kids: &[NodeId], attrs_provided: Option<bool>) -> Term {
        let loc = self.loc();
        let mut spec = NodeSpec::new(Operator::unit("file", "impl"), loc);
        if let Some(p) = attrs_provided {
            spec = spec.attr("ir.attrs_provided", p);
        }
        let root = self.b.node(spec, kids).unwrap();
        self.b.finish(root).unwrap()
    }
}

const RS: &str = "crates/a/src/lib.rs";
const MD: &str = "docs/a.md";

fn rust_term(attrs_provided: Option<bool>) -> Term {
    let mut fx = Fx::new(RS, "rust");
    let run = fx.unit("function", "run", Some("public"), &[]);
    let helper = fx.unit("function", "helper", Some("private"), &[]);
    let new_t = fx.unit("method", "new", Some("public"), &[]);
    let t = fx.unit("type", "T", Some("public"), &[new_t]);
    let new_u = fx.unit("method", "new", Some("public"), &[]);
    let u = fx.unit("type", "U", Some("public"), &[new_u]);
    fx.root(&[run, helper, t, u], attrs_provided)
}

fn md_term() -> Term {
    let mut fx = Fx::new(MD, "markdown");
    let intro = fx.unit("section", "intro", None, &[]);
    let usage = fx.unit("section", "usage", None, &[]);
    fx.root(&[intro, usage], None)
}

fn walk() -> WalkResult {
    let f = |p: &str| FileEntry {
        path: p.to_owned(),
        size: 1,
        digest: Digest::of(p.as_bytes()),
        language: LanguageHint::from_path(p),
    };
    WalkResult {
        files: vec![f(RS), f(MD)],
        oversized: Vec::new(),
    }
}

fn sel(t: &str) -> Selector {
    Selector::parse(t).unwrap()
}

/// A scope graph with every unit under one root scope; `may` names units whose edge is May.
fn graph(term: &Term, may: &[&str]) -> ScopeGraph {
    let mut g = ScopeGraph::new();
    let root = g.add_scope(None);
    for u in term.units() {
        let s = g.add_scope(Some(u.node));
        let name = u.symref.to_string();
        let st = if may.iter().any(|m| name.ends_with(m)) {
            Status::May
        } else {
            Status::Must
        };
        g.add_edge(s, Label::Lexical, root, st);
    }
    g
}

fn names(m: &[gob_ir::UnitMatch]) -> Vec<(String, Status)> {
    m.iter()
        .map(|u| {
            (
                u.symref.to_string().rsplit("::").next().unwrap().to_owned(),
                u.status,
            )
        })
        .collect()
}

#[test]
fn acceptance_glob_lang_kind_gives_must_and_excludes_markdown() {
    let s = sel(r#""crates/*/src/**" & lang(rust) & kind(function)"#);
    let rs = rust_term(None);
    let got = select_units(&s, &rs, &ScopeGraph::from_term(&rs), &walk());
    assert_eq!(
        names(&got),
        [
            ("helper".into(), Status::Must),
            ("run".into(), Status::Must)
        ]
    );
    let md = md_term();
    let got = select_units(&s, &md, &ScopeGraph::from_term(&md), &walk());
    assert!(got.is_empty());
    // Even a path glob that covers the markdown file leaves it out through `lang`.
    let both = sel(r#""**" & lang(rust)"#);
    assert!(select_units(&both, &md, &ScopeGraph::from_term(&md), &walk()).is_empty());
}

#[test]
fn markdown_heading_is_selected_by_kind() {
    let md = md_term();
    let g = ScopeGraph::from_term(&md);
    let got = select_units(&sel(r#""docs/**" & kind(section)"#), &md, &g, &walk());
    assert_eq!(
        names(&got),
        [
            ("intro".into(), Status::Must),
            ("usage".into(), Status::Must)
        ]
    );
    let one = select_units(&sel(r#""docs/a.md::usage""#), &md, &g, &walk());
    assert_eq!(names(&one), [("usage".into(), Status::Must)]);
    assert!(select_units(&sel("kind(section) & lang(rust)"), &md, &g, &walk()).is_empty());
}

#[test]
fn file_selector_includes_the_module_unit_and_everything_inside() {
    let rs = rust_term(None);
    let got = select_units(
        &sel(&format!("\"{RS}\"")),
        &rs,
        &ScopeGraph::from_term(&rs),
        &walk(),
    );
    assert_eq!(got.len(), 7);
    assert!(got.iter().all(|u| u.status == Status::Must));
}

#[test]
fn literal_resolution_exact_then_unique_suffix_then_candidates() {
    let rs = rust_term(None);
    let g = ScopeGraph::from_term(&rs);
    let exact = select_units(&sel(&format!("\"{RS}::run\"")), &rs, &g, &walk());
    assert_eq!(names(&exact), [("run".into(), Status::Must)]);
    let suffix = select_units(&sel(&format!("\"{RS}::T.new\"")), &rs, &g, &walk());
    assert_eq!(suffix.len(), 1);
    assert_eq!(suffix[0].status, Status::Must);
    let by_suffix = select_units(&sel(&format!("\"{RS}::helper\"")), &rs, &g, &walk());
    assert_eq!(by_suffix.len(), 1);
    // `new` alone is no exact unit; two suffix candidates, both May.
    let amb = select_units(&sel(&format!("\"{RS}::new\"")), &rs, &g, &walk());
    assert_eq!(amb.len(), 2);
    assert!(amb.iter().all(|u| u.status == Status::May));
    let none = select_units(&sel(&format!("\"{RS}::absent\"")), &rs, &g, &walk());
    assert!(none.is_empty());
}

#[test]
fn may_edge_on_an_ancestor_degrades_its_descendants() {
    let rs = rust_term(None);
    let g = graph(&rs, &["::T"]);
    let got = select_units(&sel(r#""crates/**" & kind(method)"#), &rs, &g, &walk());
    let st: Vec<_> = got
        .iter()
        .map(|u| (u.symref.to_string(), u.status))
        .collect();
    assert_eq!(
        st,
        [
            (format!("{RS}::T.new"), Status::May),
            (format!("{RS}::U.new"), Status::Must)
        ]
    );
}

#[test]
fn unknown_edge_degrades_to_may_never_to_absent() {
    let rs = rust_term(None);
    let mut g = ScopeGraph::new();
    let root = g.add_scope(None);
    for u in rs.units() {
        let s = g.add_scope(Some(u.node));
        g.add_edge(s, Label::Lexical, root, Status::Unknown);
    }
    let got = select_units(&sel(r#""crates/**" & kind(function)"#), &rs, &g, &walk());
    assert_eq!(got.len(), 2);
    assert!(got.iter().all(|u| u.status == Status::May));
}

#[test]
fn attribute_predicates_are_exact_or_unknown_by_provision() {
    let s = sel(r#""crates/**" & kind(function) & attr(vis = pub)"#);
    let rs = rust_term(Some(true));
    let g = ScopeGraph::from_term(&rs);
    assert_eq!(
        names(&select_units(&s, &rs, &g, &walk())),
        [("run".into(), Status::Must)]
    );

    let unprovided = rust_term(Some(false));
    let g = ScopeGraph::from_term(&unprovided);
    let got = select_units(&s, &unprovided, &g, &walk());
    // `helper` has a private visibility attribute (provided, decided No); the rest of the
    // attribute lookups are decided by the attribute itself, so only absent ones are Unknown.
    assert_eq!(names(&got), [("run".into(), Status::Must)]);

    let absent = sel(r#""crates/**" & kind(function) & attr(deprecated)"#);
    assert!(select_units(&absent, &rs, &ScopeGraph::from_term(&rs), &walk()).is_empty());
    let got = select_units(
        &absent,
        &unprovided,
        &ScopeGraph::from_term(&unprovided),
        &walk(),
    );
    assert_eq!(got.len(), 2);
    assert!(got.iter().all(|u| u.status == Status::May));
}

#[test]
fn attribute_comparisons() {
    let mut fx = Fx::new(RS, "rust");
    let loc = fx.loc();
    let u =
        fx.b.node(
            NodeSpec::new(Operator::unit("function", "f"), loc)
                .named("f")
                .attr("age", "30 s")
                .attr("retries", 3_i64)
                .attr("name", "get_one"),
            &[],
        )
        .unwrap();
    let term = fx.root(&[u], None);
    let g = ScopeGraph::from_term(&term);
    let count = |expr: &str| {
        let s = sel(&format!("\"crates/**\" & kind(function) & {expr}"));
        select_units(&s, &term, &g, &walk()).len()
    };
    assert_eq!(count("attr(age <= 60 s)"), 1);
    assert_eq!(count("attr(age <= 10 s)"), 0);
    assert_eq!(count("attr(age <= 1 min)"), 1); // different unit: Unknown, kept as May
    assert_eq!(count("attr(retries = 3)"), 1);
    assert_eq!(count("attr(retries != 3)"), 0);
    assert_eq!(count("attr(retries <= 5)"), 1);
    assert_eq!(count(r#"attr(name ~ "get_*")"#), 1);
    assert_eq!(count(r#"attr(name ~ "set_*")"#), 0);
    assert_eq!(count("!attr(name = get_one)"), 0);
}

#[test]
fn hidden_placeholders_only_where_the_selector_may_reach() {
    let mut fx = Fx::new(RS, "rust");
    let loc = fx.loc();
    let opaque =
        fx.b.node(NodeSpec::new(Operator::opaque("macro", b"x"), loc), &[])
            .unwrap();
    let run = fx.unit("function", "run", Some("public"), &[]);
    let term = fx.root(&[opaque, run], None);
    let g = ScopeGraph::from_term(&term);
    let s = select(&sel(r#""crates/**" & kind(function)"#), &term, &g, &walk());
    assert_eq!(s.matches.len(), 1);
    assert_eq!(s.hidden.len(), 1);
    assert_eq!(s.hidden[0].reason, HiddenReason::Opaque);
    let other = select(&sel(r#""docs/**""#), &term, &g, &walk());
    assert!(other.hidden.is_empty());
}

#[test]
fn files_outside_the_walk_are_not_unknown_just_silent() {
    let rs = rust_term(None);
    let empty = WalkResult::default();
    let s = select(&sel(r#""**""#), &rs, &ScopeGraph::from_term(&rs), &empty);
    assert!(s.matches.is_empty() && s.hidden.is_empty());
}

fn entities(list: &[(&str, String)]) -> Vec<(EntityName, Selector)> {
    list.iter().map(|(n, s)| ((*n).into(), sel(s))).collect()
}

fn sym(name: &str) -> Symref {
    format!("{RS}::{name}").parse().unwrap()
}

#[test]
fn owner_of_a_unit_prefers_the_symbol_level_selector() {
    let rs = rust_term(None);
    let g = ScopeGraph::from_term(&rs);
    let es = entities(&[
        ("crate", "\"crates/a/**\"".into()),
        ("runner", format!("\"{RS}::run\"")),
    ]);
    let own = owner_of_unit(&es, &sym("run"), &rs, &g).unwrap();
    assert_eq!(own.owner, Owner::Must("runner".into()));
    let own = owner_of_unit(&es, &sym("helper"), &rs, &g).unwrap();
    assert_eq!(own.owner, Owner::Must("crate".into()));
    assert!(owner_of_unit(&es, &sym("absent"), &rs, &g).is_none());
}

#[test]
fn owner_ties_are_unknown_with_both_candidates_recorded() {
    let rs = rust_term(None);
    let g = ScopeGraph::from_term(&rs);
    let es = entities(&[
        ("a", "\"crates/a/**\"".into()),
        ("b", "\"crates/a/**\"".into()),
    ]);
    let own = owner_of_unit(&es, &sym("run"), &rs, &g).unwrap();
    let want: BTreeSet<EntityName> = ["a".into(), "b".into()].into_iter().collect();
    assert_eq!(own.owner, Owner::Unknown(want));
    assert_eq!(own.candidates.len(), 2);
}

#[test]
fn owner_through_a_may_edge_is_may() {
    let rs = rust_term(None);
    let g = graph(&rs, &["::helper"]);
    let es = entities(&[("crate", "\"crates/a/**\"".into())]);
    let own = owner_of_unit(&es, &sym("helper"), &rs, &g).unwrap();
    assert_eq!(
        own.owner,
        Owner::May(["crate".into()].into_iter().collect())
    );
    assert!(own.maybe_foreign);
    let own = owner_of_unit(&es, &sym("run"), &rs, &g).unwrap();
    assert_eq!(own.owner, Owner::Must("crate".into()));
}

#[test]
fn unknown_attribute_makes_the_narrower_candidate_may_and_the_owner_bounds() {
    let rs = rust_term(Some(false));
    let g = ScopeGraph::from_term(&rs);
    let es = entities(&[
        ("broad", "\"crates/a/**\"".into()),
        ("loaders", "\"crates/a/**\" & attr(deprecated)".into()),
    ]);
    let own = owner_of_unit(&es, &sym("run"), &rs, &g).unwrap();
    assert_eq!(
        own.owner,
        Owner::May(["broad".into(), "loaders".into()].into_iter().collect())
    );
    assert!(!own.maybe_foreign);
}

#[test]
fn a_hidden_remainder_blocks_foreign() {
    let mut fx = Fx::new(RS, "rust");
    let loc = fx.loc();
    let hole =
        fx.b.node(NodeSpec::new(Operator::hole("parse-error"), loc), &[])
            .unwrap();
    let run = fx.unit("function", "run", None, &[]);
    let term = fx.root(&[hole, run], None);
    let g = ScopeGraph::from_term(&term);
    let es = entities(&[("docs", "\"docs/**\"".into())]);
    let own = owner_of_unit(&es, &sym("run"), &term, &g).unwrap();
    assert_eq!(own.owner, Owner::Unknown(BTreeSet::new()));
    let clean = rust_term(None);
    let own = owner_of_unit(&es, &sym("run"), &clean, &ScopeGraph::from_term(&clean)).unwrap();
    assert_eq!(own.owner, Owner::Foreign);
}
