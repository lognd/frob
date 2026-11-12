//! The grimble-sysdesign pack examples that declare a `model`, which need the model reader.
//!
//! These live here, not in gob-packs, because the `.grmb` reader is in `grimble-check` (a higher layer).

// frob:ticket 01M5NQHBT2GVXS9EEXBMJZYWH9

use gob_packs::sysdesign as pack;

/// Install the grimble model reader once per test process.
fn install() {
    gob_plan::examples::install_model_reader(grimble_check::example_model::read_example_model);
}

// frob:tests crates/gob-packs/src/sysdesign.rs::compile_rule
#[test]
fn every_rule_passes_its_examples() {
    install();
    for (file, src) in pack::RULES {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert!(t.examples.len() >= 2, "{file}");
        assert!(src.contains("## Remedy"), "{file}");
    }
}

// frob:tests crates/gob-packs/src/sysdesign.rs::compile_rule
#[test]
fn grammar_rules_have_fire_clean_and_not_applicable_examples() {
    install();
    for (file, src) in pack::RULES.iter().filter(|(f, _)| f.contains("grammar/")) {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert_eq!(t.examples.len(), 3, "{file}");
        assert!(src.contains("example notapplicable"), "{file}");
    }
}

// frob:tests crates/gob-packs/src/sysdesign.rs::compile_rule
#[test]
fn sysdesign_slice_rules_have_fire_clean_and_not_applicable_examples() {
    install();
    let rules: Vec<_> = pack::RULES
        .iter()
        .filter(|(f, _)| f.contains("sysdesign/"))
        .collect();
    assert_eq!(rules.len(), 3);
    for (file, src) in rules {
        let t = gob_plan::verbs::test::test_file(file, src);
        assert!(t.passed(), "{file}: {:?} {:?}", t.diagnostics, t.examples);
        assert!(src.contains("example fire"), "{file}");
        assert!(src.contains("example clean"), "{file}");
        assert!(src.contains("example notapplicable"), "{file}");
        assert!(src.contains("severity error"), "{file}");
    }
}

// frob:tests crates/gob-packs/src/sysdesign.rs::compile_rule
#[test]
fn an_owns_expression_the_rule_cannot_read_is_unresolved_never_clean() {
    install();
    let (file, src) = pack::RULES
        .iter()
        .find(|(f, _)| f.ends_with("SYSDESIGN104.grl"))
        .unwrap();
    let t = gob_plan::verbs::test::test_file(file, src);
    assert!(t.passed(), "{:?} {:?}", t.diagnostics, t.examples);
    assert_eq!(t.examples.len(), 4);
    assert!(src.contains("example unresolved"));
}
