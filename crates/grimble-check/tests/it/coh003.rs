//! COH003 verdicts over mixed-level, same-level and unresolved units in each supported language.

// frob:ticket 01M4CXSSGYVE2QQ7ACW7T5Y51S

use gob_ir::{NodeId, Operator, Universal};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh003::{Coh003, Coh003Options, Coh003Unresolved, LayeredCall, coh003};

const PY_MIXED: &str = "def f(order, raw):\n    total = price_order(order)\n    head = low_step(raw)\n    return total, head\n";
const RS_MIXED: &str = "fn f(order: Order, raw: &str) -> (i32, &str) {\n    let total = price_order(order);\n    let head = low_step(raw);\n    (total, head)\n}\n";
const TS_MIXED: &str = "function f(order, raw) {\n  const total = price_order(order);\n  const head = low_step(raw);\n  return [total, head];\n}\n";

fn verdict_with(path: &str, lang: &str, text: &str, opts: &Coh003Options) -> Coh003 {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
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
    coh003(&folded.term, lang, unit, opts)
}

fn layered(spread: u32) -> Coh003Options {
    let mut o = Coh003Options::default();
    o.layers.insert("price_order".to_owned(), 3);
    o.layers.insert("low_step".to_owned(), 0);
    o.max_level_spread = spread;
    o
}

fn names(calls: &[LayeredCall]) -> Vec<(&str, u32)> {
    calls.iter().map(|c| (c.callee.as_str(), c.layer)).collect()
}

macro_rules! mixed_test {
    ($name:ident, $path:literal, $lang:literal, $text:ident, $low:literal) => {
        // frob:tests crates/grimble-check/src/coh003.rs::coh003
        #[test]
        fn $name() {
            let v = verdict_with($path, $lang, $text, &layered(1));
            let Coh003::Fire { spread, high, low } = v else {
                panic!("expected Fire, got {v:?}")
            };
            assert_eq!(spread, 3);
            assert_eq!(names(&high), vec![("price_order", 3)]);
            assert_eq!(names(&low), vec![($low, 0)]);
        }
    };
}

mixed_test!(fires_py, "m.py", "python", PY_MIXED, "low_step");
mixed_test!(fires_rs, "m.rs", "rust", RS_MIXED, "low_step");
mixed_test!(fires_ts, "m.ts", "typescript", TS_MIXED, "low_step");

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn spread_within_the_bound_is_clean() {
    let v = verdict_with("m.py", "python", PY_MIXED, &layered(3));
    assert_eq!(v, Coh003::Clean);
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn same_layer_calls_are_clean() {
    let text = "def f(order, raw):\n    a = price_order(order)\n    b = price_order(raw)\n    return a, b\n";
    let v = verdict_with("m.py", "python", text, &layered(0));
    assert_eq!(v, Coh003::Clean);
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn unplaced_callee_is_unresolved_and_named() {
    let text = "def f(order):\n    a = price_order(order)\n    return mystery(a)\n";
    let v = verdict_with("m.py", "python", text, &layered(1));
    assert_eq!(
        v,
        Coh003::Unresolved(Coh003Unresolved::UnknownCallees {
            callees: vec!["mystery".to_owned()]
        })
    );
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn proof_beats_unknown_callees() {
    let text = "def f(order, raw):\n    a = price_order(order)\n    b = mystery(a)\n    return b, low_step(raw)\n";
    let v = verdict_with("m.py", "python", text, &layered(1));
    assert!(matches!(v, Coh003::Fire { spread: 3, .. }), "{v:?}");
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn trivial_and_nested_calls_do_not_count() {
    let text = "def f(order):\n    a = price_order(order)\n    print(a)\n    def g(raw):\n        return raw[1:2]\n    return a\n";
    let v = verdict_with("m.py", "python", text, &layered(1));
    assert_eq!(v, Coh003::Clean);
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn model_layer_overrides_neutral_vocabulary() {
    let text = "def f(order, raw):\n    a = price_order(order)\n    return a, strip(raw)\n";
    let mut o = layered(1);
    assert_eq!(verdict_with("m.py", "python", text, &o), Coh003::Clean);
    o.layers.insert("strip".to_owned(), 0);
    assert!(matches!(
        verdict_with("m.py", "python", text, &o),
        Coh003::Fire { .. }
    ));
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn unit_without_calls_is_clean() {
    let v = verdict_with("m.py", "python", "def f(a):\n    return a\n", &layered(1));
    assert_eq!(v, Coh003::Clean);
}

// frob:tests crates/grimble-check/src/coh003.rs::coh003
#[test]
fn index_and_std_string_methods_are_layer_neutral() {
    let text = "def f(order, raw):\n    a = price_order(order)\n    return a, raw[1:2], raw.strip(), raw.find(\"x\")\n";
    let v = verdict_with("m.py", "python", text, &layered(1));
    assert_eq!(v, Coh003::Clean);
}
