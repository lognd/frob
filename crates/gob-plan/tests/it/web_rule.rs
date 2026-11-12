//! The web-engine rules (`element`, `attribute`) run on the general plan executor over a
//! hand-built U term (docs/design/shared/grl-spec.md section 6, docs/design/shared/code-model.md section 13.5).
//!
//! The GRL compiler does not lower to plans yet, so the plans are built by hand with the shape
//! the compiler will emit; GRL001 (unknown kind or field) is the checker's, tested in
//! `check_names.rs`.

use crate::support;

use gob_ir::markup::{self, ELEMENT, TAG};
use gob_ir::style;
use gob_ir::{GroupOrder, Model, NodeId, NodeSpec, Operator, Truth};
use gob_plan::catalog;
use gob_plan::exec::{BUCKET_ATTR, COMPONENT_ATTR, Input, run};
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
        ("class_selector", "Q49 style", "css"),
        ("declaration", "Q49 style", "jsx"),
        ("custom_property", "Q49 style", "scss"),
    ] {
        let k = catalog::kind(word).unwrap();
        assert_eq!(k.query, query, "{word}");
        assert!(k.answered_in(lang), "{word} in {lang}");
    }
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
#[test]
fn class_selector_kind_finds_only_class_selector_nodes_by_name() {
    let mut d = Doc::new("a.css", "css");
    let card = d.add(style::class_selector_op(), Some("card"), &[]);
    let tile = d.add(style::class_selector_op(), Some("tile"), &[]);
    let rule = d.add(
        Operator::unit(style::STYLE_RULE, "impl"),
        Some(".card .tile"),
        &[card, tile],
    );
    let (model, _) = d.root(&[rule]);

    let mut b = PlanBuilder::new("CLS001", Polarity::Pplus);
    let c = b.find("class_selector");
    let (name, want) = (b.field(c, "name"), b.str_lit("card"));
    let is_card = b.cmp(name, CmpOp::Eq, want);
    b.clause(is_card);
    b.report(None, c, "card class");
    let out = run(
        &b.build(),
        &Input {
            model: &model,
            source: None,
        },
    )
    .unwrap();
    assert_eq!(out.rows.len(), 1);
    assert_eq!(out.rows[0].node(0), Some(card));
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
// frob:ticket 01M555G0ADS5XD148DWTK6F9FS
#[test]
fn bucket_and_component_read_the_file_path_parts() {
    let mut b = PlanBuilder::new("ORG004", Polarity::Pplus);
    let p = b.find("class_selector");
    let (bucket, tokens) = (b.field(p, "file.bucket"), b.str_lit("tokens"));
    let outside = b.cmp(bucket, CmpOp::Ne, tokens);
    b.clause(outside);
    b.report(None, p, "custom property outside the tokens bucket");
    let plan = b.build();

    let mut d = Doc::new("css/components/card.css", "css");
    let prop = d.add(style::class_selector_op(), Some("gap"), &[]);
    let (model, _) = d.root(&[prop]);
    let out = run(
        &plan,
        &Input {
            model: &model,
            source: None,
        },
    )
    .unwrap();
    assert_eq!(out.rows.len(), 1, "components is not tokens");

    let mut b = PlanBuilder::new("ORG003", Polarity::Pplus);
    let p = b.find("class_selector");
    let (comp, card) = (b.field(p, "component"), b.str_lit("card"));
    let named = b.cmp(comp, CmpOp::Eq, card);
    b.clause(named);
    b.report(None, p, "in card");
    let out = run(
        &b.build(),
        &Input {
            model: &model,
            source: None,
        },
    )
    .unwrap();
    assert_eq!(out.rows.len(), 1, "the stem is the component");
}

// frob:tests crates/gob-plan/src/exec/core/mod.rs::run
// frob:ticket 01M5ETSE6D7CPPAVBD4KEM6AX5
#[test]
fn host_stamped_bucket_and_component_override_the_path() {
    let build = |bucket: &str, component: &str| {
        let mut d = Doc::new("css/nested/deep/card.css", "css");
        let prop = d.add(style::class_selector_op(), Some("gap"), &[]);
        d.at += 1;
        let (lo, hi) = (d.at, d.at + 1);
        let root = d.at_range(
            |loc| {
                NodeSpec::new(Operator::group(GroupOrder::Sequence), loc)
                    .attr(BUCKET_ATTR, bucket)
                    .attr(COMPONENT_ATTR, component)
            },
            lo,
            hi,
            &[prop],
        );
        let term = d.tb.finish(root).unwrap();
        Model::lexical(term)
    };
    let rows = |model: &Model, field: &str, want: &str| {
        let mut b = PlanBuilder::new("ORG003", Polarity::Pplus);
        let p = b.find("class_selector");
        let (f, lit) = (b.field(p, field), b.str_lit(want));
        let eq = b.cmp(f, CmpOp::Eq, lit);
        b.clause(eq);
        b.report(None, p, "matched");
        let input = Input {
            model,
            source: None,
        };
        run(&b.build(), &input).unwrap().rows.len()
    };

    let placed = build("components", "card");
    assert_eq!(
        rows(&placed, "file.bucket", "components"),
        1,
        "stamp beats the parent dir"
    );
    assert_eq!(rows(&placed, "file.component", "card"), 1);

    let stray = build("", "");
    assert_eq!(
        rows(&stray, "file.bucket", "deep"),
        0,
        "empty stamp means no bucket"
    );
    assert_eq!(
        rows(&stray, "component", "card"),
        0,
        "empty stamp means no component"
    );
}
