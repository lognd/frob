//! Opaque regions: a lexical fire inside an island beside an Unresolved structural rule.

// frob:ticket 01M48Q4FV1V0ZRM8C4J1YMJ2G9

use gob_mdtest::opaque::analyze_opaque;
use gob_mdtest::parse_suite;

fn lexical() -> Vec<String> {
    vec!["LEX001".to_owned()]
}

fn run(body: &str) -> gob_mdtest::opaque::OpaqueReport {
    let blocks = parse_suite(body).expect("suite parses");
    analyze_opaque(&lexical(), &blocks)
}

const GOOD: &str = "# Shell in YAML\n\
```yaml rule=LEX001 expect=fire cell=island region=shell\nrun: rm -rf /\n```\n\
```yaml rule=STR001 expect=unresolved reason=opaque region=shell\nrun: rm -rf /\n```\n";

// frob:tests crates/gob-mdtest/src/opaque.rs::analyze_opaque
#[test]
fn a_fire_beside_an_unresolved_structural_rule_passes() {
    let r = run(GOOD);
    assert!(r.passed(), "{}", r.render());
    assert_eq!(r.regions, 1);
}

// frob:tests crates/gob-mdtest/src/opaque.rs::analyze_opaque
#[test]
fn a_region_without_a_structural_unresolved_fails() {
    let r = run(&GOOD
        .replace("rule=STR001", "rule=LEX001")
        .replace("expect=unresolved reason=opaque", "expect=clean"));
    assert_eq!(r.no_structural.len(), 1, "{}", r.render());
}

// frob:tests crates/gob-mdtest/src/opaque.rs::analyze_opaque
#[test]
fn a_structural_rule_that_fires_over_the_region_fails() {
    let r = run(&GOOD.replace("expect=unresolved reason=opaque", "expect=fire"));
    assert_eq!(r.not_unresolved.len(), 1, "{}", r.render());
    assert_eq!(r.no_structural.len(), 1, "{}", r.render());
}

// frob:tests crates/gob-mdtest/src/opaque.rs::analyze_opaque
#[test]
fn a_lexical_island_fire_without_a_region_fails() {
    let r = run(&GOOD.replace(
        " region=shell\nrun: rm -rf /\n```\n```yaml",
        "\nrun: rm -rf /\n```\n```yaml",
    ));
    assert_eq!(r.unnamed.len(), 1, "{}", r.render());
}

// frob:tests crates/gob-mdtest/src/opaque.rs::analyze_opaque
#[test]
fn regions_in_different_sections_do_not_pair() {
    let body = GOOD.replace("```yaml rule=STR001", "# Other\n```yaml rule=STR001");
    let r = run(&body);
    assert_eq!(r.no_structural.len(), 1, "{}", r.render());
}

// frob:tests crates/gob-mdtest/src/opaque.rs::assert_opaque
#[test]
fn the_workspace_corpus_has_no_dangling_opaque_region() {
    // The shipped lexical rules whose island fires live in product corpora, beside the fixture id.
    let mut ids = lexical();
    ids.extend(
        ["TICK004", "TICK005", "TODO001"]
            .into_iter()
            .map(str::to_owned),
    );
    gob_mdtest::opaque::assert_opaque(env!("CARGO_MANIFEST_DIR"), &ids);
}
