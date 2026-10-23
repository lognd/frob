//! COH002 counts Rust `match` expressions as decisions, with the edge cases of arms and nesting.

// frob:ticket 01M5HJ07B6E0NZ47RCV0HWZR5Y

#![allow(unused_crate_dependencies)]

use gob_ir::{NodeId, Operator, Universal};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh002::{Coh002, Coh002Options, UnitRole, coh002};

fn verdict(text: &str) -> Coh002 {
    let entry = FileEntry {
        path: "m.rs".to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path("m.rs"),
    };
    let folded = fold_file(&entry, text).expect("fold");
    let unit: NodeId = folded
        .term
        .ids()
        .find(|&i| {
            matches!(folded.term.node(i).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
                && folded.term.node(i).name() == Some("f")
        })
        .expect("function f");
    coh002(
        &folded,
        "rust",
        unit,
        UnitRole::None,
        &Coh002Options::default(),
    )
    .expect("rust")
}

fn fired(text: &str) -> usize {
    match verdict(text) {
        Coh002::Fire { decisions, .. } => decisions.len(),
        _ => 0,
    }
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
// frob:tests crates/grimble-check/src/coh002.rs::coh002
#[test]
fn match_arms_are_counted_as_decisions() {
    let text = "fn f(a: i32, sink: Sink) -> i32 {\n    let x = compute(a);\n    match x {\n        1 => sink.send(x),\n        _ => {}\n    }\n    x\n}\n";
    assert_eq!(fired(text), 1);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn match_as_tail_expression_and_single_arm() {
    let tail = "fn f(a: i32, sink: Sink) {\n    let x = compute(a);\n    match x {\n        _ => sink.send(x),\n    }\n}\n";
    assert_eq!(fired(tail), 1);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn match_with_guard_and_binding_arm() {
    let text = "fn f(a: i32, sink: Sink) {\n    let x = compute(a);\n    match x {\n        n if n > 3 => sink.send(n),\n        _ => {}\n    }\n}\n";
    assert_eq!(fired(text), 1);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn nested_match_counts_both_decisions() {
    let text = "fn f(a: i32, sink: Sink) {\n    let x = compute(a);\n    match x {\n        1 => match compute(x) {\n            2 => sink.send(x),\n            _ => {}\n        },\n        _ => {}\n    }\n}\n";
    assert_eq!(fired(text), 2);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn match_on_a_bare_parameter_is_dispatch_not_a_decision() {
    let text = "fn f(a: i32, sink: Sink) {\n    match a {\n        1 => sink.send(a),\n        _ => {}\n    }\n}\n";
    assert_eq!(verdict(text), Coh002::Clean);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn match_inside_a_closure_is_another_unit() {
    let text = "fn f(a: i32, sink: Sink) {\n    let g = |v: i32| match compute(v) {\n        1 => sink.send(v),\n        _ => {}\n    };\n}\n";
    assert_eq!(verdict(text), Coh002::Clean);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn match_without_effects_is_clean_and_if_let_still_fires() {
    let pure = "fn f(a: i32) -> i32 {\n    let x = compute(a);\n    match x {\n        1 => 2,\n        _ => 3,\n    }\n}\n";
    assert_eq!(verdict(pure), Coh002::Clean);
    let iflet = "fn f(a: i32, sink: Sink) {\n    let x = compute(a);\n    if let Some(v) = x {\n        sink.send(v);\n    }\n}\n";
    assert_eq!(fired(iflet), 1);
}

// frob:tests crates/grimble-check/src/coh002.rs::judge
#[test]
fn function_without_match_keeps_its_decision_count() {
    let text = "fn f(a: i32, sink: Sink) -> i32 {\n    let x = compute(a);\n    if x > 3 {\n        sink.send(x);\n    }\n    x\n}\n";
    assert_eq!(fired(text), 1);
}
