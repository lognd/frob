//! Small public accessors of the model crate: spans, tokens, plan items, arg kinds, rule binding.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use grimble_model::args::ArgKind;
use grimble_model::ast::{Direction, Item};
use grimble_model::lex::{Tok, lex};
use grimble_model::plan::PlanItem;
use grimble_model::{ModelFiles, PackPin, Span, parse_file};

const PLAN: &str =
    "grimble = \"2\";\nmodule m;\n\nsystem s {\n  actor u : human;\n  step u.go;\n}\n";

#[test]
// frob:tests crates/grimble-model/src/span.rs::Span.to
// frob:tests crates/grimble-model/src/span.rs::Span.slice
fn span_joins_and_slices() {
    let a = Span::new(2, 4);
    let b = Span::new(6, 9);
    assert_eq!(a.to(b), Span::new(2, 9));
    assert_eq!("0123456789".get(2..9), Some(a.to(b).slice("0123456789")));
    assert_eq!(Span::new(0, 99).slice("abc"), "");
}

#[test]
// frob:tests crates/grimble-model/src/lex.rs::Tok.is_word
// frob:tests crates/grimble-model/src/lex.rs::Tok.describe
fn tokens_describe_themselves_and_know_words() {
    let lexed = lex("node r#type 12 \"s\"");
    let toks: Vec<&Tok> = lexed.tokens.iter().map(|t| &t.tok).collect();
    assert!(toks[0].is_word() && toks[1].is_word());
    assert!(!toks[2].is_word());
    assert_eq!(toks[0].describe(), "`node`");
    assert_eq!(toks[1].describe(), "`r#type`");
    assert_eq!(toks[2].describe(), "number `12`");
    assert_eq!(toks[3].describe(), "a string");
}

#[test]
// frob:tests crates/grimble-model/src/ast.rs::Direction.keyword
fn direction_keywords_are_the_spec_words() {
    assert_eq!(Direction::Endorse.keyword(), "endorse");
    assert_eq!(Direction::Declassify.keyword(), "declassify");
}

#[test]
// frob:tests crates/grimble-model/src/args.rs::ArgKind.describe
fn arg_kinds_describe_what_they_accept() {
    assert_eq!(ArgKind::Path.describe(), "a path pattern");
    assert_eq!(ArgKind::Host.describe(), "a host pattern");
    assert_eq!(ArgKind::EnvName.describe(), "an environment variable name");
}

#[test]
// frob:tests crates/grimble-model/src/ast.rs::Item.span
// frob:tests crates/grimble-model/src/ast.rs::Item.id
// frob:tests crates/grimble-model/src/plan.rs::PlanItem.span
// frob:tests crates/grimble-model/src/plan.rs::PlanItem.id
// frob:tests crates/grimble-model/src/plan.rs::Step.name
fn plan_items_report_span_id_and_step_name() {
    let f = parse_file("m.grmb", PLAN.as_bytes());
    assert!(f.diags.is_empty(), "{:?}", f.diags);
    let Item::Plan(sys) = &f.items[0] else {
        panic!("expected a plan item, got {:?}", f.items[0]);
    };
    let PlanItem::System(s) = &**sys else {
        panic!("expected a system");
    };
    assert_eq!(f.items[0].span(), sys.span());
    assert_eq!(f.items[0].id(), sys.id());
    assert_eq!(sys.span().slice(PLAN), PLAN[sys.span().start..].trim_end());
    let step = s
        .items
        .iter()
        .find_map(|i| match i {
            Item::Plan(p) => match &**p {
                PlanItem::Step(st) => Some((i, st)),
                _ => None,
            },
            _ => None,
        })
        .expect("step");
    assert_eq!(step.1.name(), "go");
    assert_eq!(step.0.span(), step.1.span);
    assert_eq!(step.0.id(), step.1.id);
}

#[test]
// frob:tests crates/grimble-model/src/model.rs::ModelFiles.with_pack
fn with_pack_enables_the_pack_by_id() {
    let pin = PackPin {
        version: "1".to_owned(),
        digest: None,
        atoms: ["net".to_owned()].into_iter().collect(),
        arg_kinds: std::collections::BTreeMap::default(),
        detectors: Vec::new(),
    };
    let files = ModelFiles::default().with_pack("p", pin);
    assert_eq!(files.packs["p"].version, "1");
}

struct Stub;
impl grimble_model::host::MdlHost for Stub {}

#[test]
// frob:tests crates/grimble-model/src/rules/mod.rs::bind
fn bind_yields_one_rule_per_declared_rule() {
    assert_eq!(
        grimble_model::rules::bind::<Stub>().len(),
        grimble_model::rules::METAS.len()
    );
}

#[test]
// frob:tests crates/grimble-model/src/rules/mod.rs::BindPart.push_all
fn a_part_appends_only_its_own_rules() {
    use grimble_model::rules::{BindPart, Part0};
    let mut rules: Vec<gob_rules::BoundRule<Stub>> = Vec::new();
    Part0::push_all(&mut rules);
    assert!(!rules.is_empty());
    assert!(rules.len() < grimble_model::rules::METAS.len());
}
