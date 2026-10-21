//! The example `model` reader: model text becomes node rows, and the SYSDESIGN101 corpus rule
//! runs its model examples through the installed reader.

// frob:ticket 01M5FRCMBS9DHQ223JWGN6RNW7
use grimble_check::example_model::read_example_model;

// frob:tests crates/grimble-check/src/example_model.rs::read_example_model
#[test]
fn model_text_yields_node_rows() {
    let rows = read_example_model(r#"node a : trusted { kind artifact; owns "src/**"; }"#)
        .expect("parses");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].kind, "artifact");
    assert_eq!(rows[0].selectors, [r#""src/**""#]);
}

// frob:tests crates/grimble-check/src/example_model.rs::read_example_model
#[test]
fn broken_model_text_is_refused() {
    assert!(read_example_model("node {{{").is_err());
}

// frob:tests crates/grimble-check/src/example_model.rs::read_example_model
#[test]
fn sysdesign101_model_examples_pass() {
    gob_plan::examples::install_model_reader(read_example_model);
    let src = include_str!("../../gob-plan/src/examples/corpus/SYSDESIGN101.grl");
    let t = gob_plan::verbs::test::test_file("SYSDESIGN101.grl", src);
    assert!(!t.examples.is_empty());
    for e in &t.examples {
        assert_eq!(e.status, "ok", "{}: {}", e.rule, e.detail);
    }
}
