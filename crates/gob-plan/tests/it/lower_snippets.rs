//! Snippet lowering: a grammar-level pattern becomes a match op the executor answers from text.

// frob:ticket 01M4WGCDS34JR3PFCWKHZ73YP7

use gob_plan::exec::Input;
use gob_plan::exec::outcome::{Kind, outcomes};
use gob_plan::exec::relations::Relations;
use gob_plan::grl::parse;
use gob_plan::lower::{LowerError, lower_rule};
use gob_plan::plan::{Op, Plan, Provenance};
use gob_text::FileInterner;

const EXPLAIN: &str = "  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n";
const TARGET: &str = "fn main() {\n    let a = x.unwrap();\n    let b = y.expect(\"m\");\n}\n";

fn lower(lang: &str, lines: &[&str]) -> Result<Plan, LowerError> {
    let src = format!(
        "rule TST001 \"t\" {{\n  {lang}\n  {}\n{EXPLAIN}}}\n",
        lines.join("\n  ")
    );
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    lower_rule(&parsed.file.rules[0], Provenance::Std)
}

fn finds(plan: &Plan, with_text: bool) -> usize {
    fires(plan, with_text).0
}

/// The (fires, unresolved) counts of the plan over `TARGET`.
fn fires(plan: &Plan, with_text: bool) -> (usize, usize) {
    let model = gob_symbols::model_of_source("rust", TARGET).unwrap();
    let source = gob_text::SourceText::new(TARGET.to_owned()).unwrap();
    let input = Input {
        model: &model,
        source: with_text.then_some(&source),
    };
    let out = outcomes(plan, &input, &Relations::new()).unwrap();
    let fired = out.findings.iter().filter(|f| f.kind == Kind::Fire).count();
    (fired, out.findings.len() - fired)
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_snippet_binder_and_an_is_snippet_lower_to_match_ops() {
    let binder = lower("lang rust", &["find c: `$X.unwrap()`", "report c \"x\""]).unwrap();
    assert!(
        binder
            .parts()
            .ops
            .iter()
            .any(|o| matches!(o, Op::MatchSnippet { .. }))
    );
    let is = lower(
        "lang rust",
        &[
            "find c: call",
            "where c is rust`$X.unwrap()`",
            "report c \"x\"",
        ],
    )
    .unwrap();
    assert!(
        is.parts()
            .ops
            .iter()
            .any(|o| matches!(o, Op::MatchSnippet { .. }))
    );
}

// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
#[test]
fn a_snippet_with_no_language_or_a_cast_is_refused_by_name() {
    let none = lower("lang *", &["find c: `$X.unwrap()`", "report c \"x\""]);
    assert!(matches!(
        none,
        Err(LowerError::Unsupported {
            what: "a snippet with no language",
            ..
        })
    ));
}

// frob:tests crates/gob-plan/src/plan/codec.rs::encode
#[test]
fn a_snippet_plan_round_trips_through_the_codec() {
    let plan = lower("lang rust", &["find c: `$X.unwrap()`", "report c \"x\""]).unwrap();
    let back = Plan::load(&plan.to_bytes()).unwrap();
    assert_eq!(back.to_bytes(), plan.to_bytes());
}

// frob:tests crates/gob-plan/src/exec/core/eval.rs::snippet_op
#[test]
fn the_executor_finds_exactly_the_snippet_matches_and_is_unknown_without_text() {
    let plan = lower("lang rust", &["find c: `$X.unwrap()`", "report c \"x\""]).unwrap();
    assert_eq!(finds(&plan, true), 1, "unwrap matches, expect does not");
    let (fired, unresolved) = fires(&plan, false);
    assert_eq!(fired, 0, "no text: never a certain finding");
    assert!(unresolved > 0, "no text: the nodes stay Unresolved");
}

// frob:tests crates/gob-plan/src/exec/core/eval.rs::snippet_op
#[test]
fn a_macro_snippet_with_a_sequence_metavariable_fires_on_its_call_only() {
    let plan = lower("lang rust", &["find d: `dbg!($$$ARGS)`", "report d \"x\""]).unwrap();
    let hit = "fn f(x: u32) -> u32 { dbg!(x) }\n";
    let miss = "fn f(x: u32) -> u32 { x }\n";
    let run = |text: &str| {
        let model = gob_symbols::model_of_source("rust", text).unwrap();
        let source = gob_text::SourceText::new(text.to_owned()).unwrap();
        let input = Input {
            model: &model,
            source: Some(&source),
        };
        outcomes(&plan, &input, &Relations::new())
            .unwrap()
            .findings
            .len()
    };
    assert_eq!(run(miss), 0);
    assert!(run(hit) >= 1);
}

// frob:ticket 01M4XF8KYPGPRH6J6CAH2V8QVT
// frob:tests crates/gob-plan/src/lower/mod.rs::lower_rule
// frob:tests crates/gob-plan/src/exec/core/eval.rs::snippet_op
#[test]
fn a_snippet_cast_selects_nodes_of_its_kind_inside_the_match() {
    const TEXT: &str = "mod m {\n    fn inner() {}\n}\nfn outer() {}\n";
    let run = |plan: &Plan, with_text: bool| {
        let model = gob_symbols::model_of_source("rust", TEXT).unwrap();
        let source = gob_text::SourceText::new(TEXT.to_owned()).unwrap();
        let input = Input {
            model: &model,
            source: with_text.then_some(&source),
        };
        let out = outcomes(plan, &input, &Relations::new()).unwrap();
        out.findings.iter().filter(|f| f.kind == Kind::Fire).count()
    };
    let cast = lower(
        "lang rust",
        &[
            "find c: `mod m { fn $F() {} }` as function",
            "report c \"x\"",
        ],
    )
    .unwrap();
    assert!(
        cast.parts()
            .ops
            .iter()
            .any(|o| matches!(o, Op::MatchSnippet { within: true, .. }))
    );
    // `inner` lies inside the matched module; `outer` does not.
    assert_eq!(run(&cast, true), 1);
    // Without the file text the match cannot be decided.
    assert_eq!(run(&cast, false), 0);
    let back = Plan::load(&cast.to_bytes()).unwrap();
    assert_eq!(back.to_bytes(), cast.to_bytes());
    // An uncast snippet demands the node be exactly the match, so no function qualifies.
    let exact = lower(
        "lang rust",
        &[
            "find c: function",
            "where c is `mod m { fn $F() {} }`",
            "report c \"x\"",
        ],
    )
    .unwrap();
    assert_eq!(run(&exact, true), 0);
}
