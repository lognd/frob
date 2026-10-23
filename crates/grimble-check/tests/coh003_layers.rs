//! COH003 layer source: model-supplied layers, the module-depth fallback and their edge cases.

// frob:ticket 01M5HJDX1Q27XGZ77ACWXQ03KP

#![allow(unused_crate_dependencies)]

use gob_ir::{NodeId, Operator, Universal};
use gob_symbols::{Folded, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh003::{Coh003, Coh003Options, Coh003Unresolved, coh003};
use grimble_check::layers::{
    Definitions, FileLayer, LayerSource, ModelLayers, callee_layers, coh003_options, definitions,
};
use grimble_model::ModelFiles;

const CALLER: &str = "def f(order, raw):\n    total = price_order(order)\n    head = raw[2:5]\n    return total, head\n";
const PRICE: &str = "def price_order(order):\n    return order\n";
const HEADER: &str = "grimble = \"2\";\nmodule m;\n";

fn fold(path: &str, text: &str) -> Folded {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    fold_file(&entry, text).expect("fold")
}

fn defs(files: &[(&str, &str)]) -> Vec<Definitions> {
    files
        .iter()
        .map(|(p, t)| definitions(p, &fold(p, t)))
        .collect()
}

fn model(body: &str) -> ModelLayers {
    let files = ModelFiles::new()
        .with_file("m.grmb", format!("{HEADER}{body}"))
        .with_root("m.grmb");
    ModelLayers::from_model(&files)
}

fn verdict(opts: &Coh003Options) -> Coh003 {
    let folded = fold("top.py", CALLER);
    let unit: NodeId = folded
        .term
        .ids()
        .find(|&i| {
            matches!(folded.term.node(i).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
                && folded.term.node(i).name() == Some("f")
        })
        .expect("function f");
    coh003(&folded.term, "python", unit, opts)
}

const NODES: &str = "node hi : trusted { owns \"top.py\"; attr layer = 4; }\nnode lo : trusted { owns \"low/**\"; attr layer = 1; }\n";

// frob:tests crates/grimble-check/src/layers.rs::coh003_options
// frob:tests crates/grimble-check/src/layers.rs::ModelLayers.from_model
#[test]
fn model_layers_make_coh003_fire() {
    let d = defs(&[
        ("top.py", PRICE),
        ("low/h.py", "def helper():\n    return 1\n"),
    ]);
    let layers = callee_layers(&model(NODES), &d, 0);
    assert_eq!(layers.source, LayerSource::Model);
    assert_eq!(layers.layers.get("price_order"), Some(&4));
    assert_eq!(layers.layers.get("helper"), Some(&1));
    let v = verdict(&coh003_options(&model(NODES), &d));
    assert!(matches!(v, Coh003::Fire { spread: 4, .. }), "got {v:?}");
}

// frob:tests crates/grimble-check/src/layers.rs::coh003_options
#[test]
fn module_depth_fills_layers_without_a_model() {
    let d = defs(&[
        ("top.py", PRICE),
        ("a/b/h.py", "def helper():\n    return 1\n"),
    ]);
    let layers = callee_layers(&ModelLayers::default(), &d, 0);
    assert_eq!(layers.source, LayerSource::ModuleDepth);
    assert_eq!(layers.layers.get("helper"), Some(&1));
    assert_eq!(layers.layers.get("price_order"), Some(&3));
    let v = verdict(&coh003_options(&ModelLayers::default(), &d));
    assert!(matches!(v, Coh003::Fire { spread: 3, .. }), "got {v:?}");
}

// frob:tests crates/grimble-check/src/layers.rs::callee_layers
#[test]
fn single_depth_repo_places_nothing() {
    let d = defs(&[
        ("top.py", PRICE),
        ("other.py", "def helper():\n    return 1\n"),
    ]);
    let layers = callee_layers(&ModelLayers::default(), &d, 0);
    assert_eq!(layers.source, LayerSource::None);
    assert!(layers.layers.is_empty());
    let v = verdict(&coh003_options(&ModelLayers::default(), &d));
    assert!(
        matches!(
            v,
            Coh003::Unresolved(Coh003Unresolved::UnknownCallees { .. })
        ),
        "got {v:?}"
    );
}

// frob:tests crates/grimble-check/src/layers.rs::callee_layers
#[test]
fn depth_ties_share_a_layer() {
    let d = defs(&[
        ("a/x.py", "def one():\n    return 1\n"),
        ("b/y.py", "def two():\n    return 2\n"),
        ("a/b/z.py", "def three():\n    return 3\n"),
    ]);
    let l = callee_layers(&ModelLayers::default(), &d, 0).layers;
    assert_eq!(l.get("one"), l.get("two"));
    assert_eq!(l.get("three"), Some(&1));
    assert_eq!(l.get("one"), Some(&2));
}

// frob:tests crates/grimble-check/src/layers.rs::callee_layers
#[test]
fn partial_model_does_not_fall_back_per_file() {
    let d = defs(&[
        ("top.py", PRICE),
        ("a/b/h.py", "def helper():\n    return 1\n"),
    ]);
    let m = model("node hi : trusted { owns \"top.py\"; attr layer = 4; }\n");
    let l = callee_layers(&m, &d, 0);
    assert_eq!(l.source, LayerSource::Model);
    assert_eq!(l.layers.get("price_order"), Some(&4));
    assert!(!l.layers.contains_key("helper"));
}

// frob:tests crates/grimble-check/src/layers.rs::ModelLayers.layer_of
#[test]
fn conflicting_nodes_give_no_layer() {
    let m = model(
        "node a : trusted { owns \"x/**\"; attr layer = 2; }\nnode b : trusted { owns \"x/**\"; attr layer = 3; }\nnode c : trusted { owns \"x/**\"; attr layer = 3; }\n",
    );
    assert!(matches!(m.layer_of("x/f.py"), FileLayer::Conflict(_)));
    assert_eq!(m.layer_of("y/f.py"), FileLayer::Unowned);
}

// frob:tests crates/grimble-check/src/layers.rs::ModelLayers.from_model
#[test]
fn invalid_or_missing_layers_are_skipped() {
    let m = model(
        "node a : trusted { owns \"a/**\"; }\nnode b : trusted { owns \"b/**\"; attr layer = x; }\nnode c : trusted { owns \"c/**\"; attr layer = 2; }\n",
    );
    assert_eq!(m.layer_of("a/f.py"), FileLayer::Unowned);
    assert_eq!(m.layer_of("b/f.py"), FileLayer::Unowned);
    assert_eq!(m.layer_of("c/f.py"), FileLayer::At(2));
    assert!(model("node a : trusted { owns \"a/**\"; }\n").is_empty());
}

// frob:tests crates/grimble-check/src/layers.rs::callee_layers
#[test]
fn ambiguous_callee_is_left_unplaced() {
    let d = defs(&[("top.py", PRICE), ("a/b/p.py", PRICE), ("a/b/q.py", PRICE)]);
    let l = callee_layers(&ModelLayers::default(), &d, 0).layers;
    assert!(!l.contains_key("price_order"));
    let d = defs(&[
        ("a/b/p.py", PRICE),
        ("a/b/q.py", PRICE),
        ("t.py", "def g():\n    return 1\n"),
    ]);
    let l = callee_layers(&ModelLayers::default(), &d, 0).layers;
    assert_eq!(l.get("price_order"), Some(&1));
}
