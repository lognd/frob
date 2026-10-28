//! Generated rule modules: byte-identical output, forbidden `unsafe`, and the same findings as
//! the plan run directly.

// frob:ticket 01M3ZX7HGX4HXKW1X8VKHW9BKW

use gob_plan::codegen::generate;
use gob_plan::exec::Input;
use gob_plan::exec::outcome::outcomes;
use gob_plan::exec::relations::Relations;
use gob_plan::lower::lower_rule;
use gob_plan::plan::{Plan, Provenance};

// The checked-in output of `generate`; compiling it here is the proof that it compiles.
#[allow(dead_code)] // the error payloads are only read by callers of the generated module
#[path = "codegen/danger001.rs"]
mod danger001;

const RULE: &str = r#"rule DANGER001 "danger-call" {
  lang typescript
  severity error
  find c: call where c.callee == "danger"
  report c "danger"
  explain """
    Danger.

    ## Remedy
    Do not.
  """
}
"#;

const TARGET: &str = "function a() {\n  danger();\n  safe();\n}\n";

fn plan() -> Plan {
    let parsed = gob_plan::grl::parse(gob_text::FileInterner::new().intern("r.grl"), RULE);
    lower_rule(&parsed.file.rules[0], Provenance::Std).unwrap()
}

// frob:tests crates/gob-plan/src/codegen/mod.rs::generate
#[test]
fn generation_is_byte_identical_and_matches_the_checked_in_module() {
    let (a, b) = (generate(&plan()), generate(&plan()));
    assert_eq!(a, b);
    assert!(a.contains("#![forbid(unsafe_code)]"));
    let on_disk = std::fs::read_to_string("tests/codegen/danger001.rs").unwrap();
    assert_eq!(a, on_disk, "regenerate tests/codegen/danger001.rs");
}

// frob:tests crates/gob-plan/src/codegen/mod.rs::generate
#[test]
fn the_generated_rule_and_its_plan_find_the_same_things() {
    let model = gob_symbols::model_of_source("typescript", TARGET).unwrap();
    let source = gob_text::SourceText::new(TARGET.to_owned()).unwrap();
    let input = Input {
        model: &model,
        source: Some(&source),
    };
    let rels = Relations::new();
    let want = outcomes(&plan(), &input, &rels).unwrap();
    let got = danger001::run(&input, &rels).unwrap();
    assert_eq!(want.findings.len(), 1);
    assert_eq!(got, want);
    assert_eq!(danger001::plan().unwrap().to_bytes(), plan().to_bytes());
}

/// Rewrites the checked-in module; run with `GEN_CODEGEN=1` after changing the generator.
#[test]
fn regenerate_when_asked() {
    if std::env::var_os("GEN_CODEGEN").is_some() {
        std::fs::write("tests/codegen/danger001.rs", generate(&plan())).unwrap();
    }
}
