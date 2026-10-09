//! The web-engine rules (`element`, `attribute`) run on the general plan executor over a
//! hand-built U term (grl-spec.md section 6, language-engines.md section 5).
//!
//! The GRL compiler does not lower to plans yet, so the plans are built by hand with the shape
//! the compiler will emit; GRL001 (unknown kind or field) is the checker's, tested in
//! `check_names.rs`.

mod support;

use gob_ir::markup::{self, ELEMENT, TAG};
use gob_ir::{NodeId, Operator, Truth};
use gob_plan::catalog;
use gob_plan::exec::{Input, run};
use gob_plan::plan::{CmpOp, Polarity, Quant};
use support::{Doc, PlanBuilder};

fn img(d: &mut Doc, attrs: &[(&str, &str)], spread: bool) -> NodeId {
    let head = d.add(Operator::lit(TAG, "img"), None, &[]);
    let mut kids = vec![head];
    for (n, v) in attrs {
        let val = d.add(Operator::lit("str", v), None, &[]);
        kids.push(d.add(markup::attribute_op(), Some(n), &[val]));
    }
    if spread {
        let e = d.add(Operator::reference("props"), None, &[]);
        kids.push(d.add(markup::spread_op(), None, &[e]));
    }
    d.add(Operator::apply(ELEMENT), None, &kids)
}

/// `find e: element where e.tag == "img" where not e has attribute(name = "alt")`.
fn alt_plan() -> gob_plan::plan::Plan {
    let mut b = PlanBuilder::new("ALT001", Polarity::Pplus);
    let e = b.find("element");
    let (tag, img) = (b.field(e, "tag"), b.str_lit("img"));
    let is_img = b.cmp(tag, CmpOp::Eq, img);
    b.clause(is_img);
    let has_alt = b.quant(Quant::Some, "attribute", |b, a| {
        let inside = b.inside(a, e, true);
        let (name, alt) = (b.field(a, "name"), b.str_lit("alt"));
        let named = b.cmp(name, CmpOp::Eq, alt);
        b.op(gob_plan::plan::Op::And(vec![inside, named]))
    });
    let none = b.op(gob_plan::plan::Op::Not(has_alt));
    b.clause(none);
    b.report(None, e, "img needs an alt attribute");
    b.build()
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
#[test]
fn element_attribute_rule_runs_on_a_hand_built_term() {
    let mut d = Doc::new("a.tsx", "tsx");
    let bad = img(&mut d, &[("src", "x.png")], false);
    let good = img(&mut d, &[("src", "x.png"), ("alt", "logo")], false);
    let maybe = img(&mut d, &[("src", "y.png")], true);
    let (model, _) = d.root(&[bad, good, maybe]);

    let out = run(
        &alt_plan(),
        &Input {
            model: &model,
            source: None,
        },
    )
    .unwrap();
    let truth = |n: NodeId| {
        out.rows
            .iter()
            .find(|r| r.node(0) == Some(n))
            .map(|r| r.verdict.truth)
    };
    assert_eq!(truth(bad), Some(Truth::Yes));
    assert_eq!(truth(good), None, "an alt attribute rules the element out");
    assert_eq!(
        truth(maybe),
        Some(Truth::Unknown),
        "a spread may supply alt"
    );
}

#[test]
fn attribute_rule_reads_const_values() {
    let mut b = PlanBuilder::new("ALT001", Polarity::Pplus);
    let a = b.find("attribute");
    let (name, role) = (b.field(a, "name"), b.str_lit("role"));
    let named = b.cmp(name, CmpOp::Eq, role);
    b.clause(named);
    let (value, pres) = (b.field(a, "value"), b.str_lit("presentation"));
    let hit = b.cmp(value, CmpOp::Eq, pres);
    b.clause(hit);
    b.report(None, a, "presentational role");
    let plan = b.build();

    let mut d = Doc::new("a.tsx", "tsx");
    let hit = img(&mut d, &[("role", "presentation")], false);
    let miss = img(&mut d, &[("role", "img")], false);
    let (model, _) = d.root(&[hit, miss]);
    let out = run(
        &plan,
        &Input {
            model: &model,
            source: None,
        },
    )
    .unwrap();
    assert_eq!(out.rows.len(), 1);
    let els = markup::elements(&model);
    assert_eq!(out.rows[0].node(0), Some(els[0].attributes[0].node));
    assert_eq!(out.rows[0].verdict.truth, Truth::Yes);
}

#[test]
fn catalog_names_query_and_languages_for_each_web_kind() {
    for (word, query, lang) in [
        ("element", "Q48 markup", "tsx"),
        ("attribute", "Q48 markup", "html"),
        ("style_rule", "Q49 style", "css"),
        ("declaration", "Q49 style", "jsx"),
        ("custom_property", "Q49 style", "scss"),
    ] {
        let k = catalog::kind(word).unwrap();
        assert_eq!(k.query, query, "{word}");
        assert!(k.answered_in(lang), "{word} in {lang}");
    }
}
