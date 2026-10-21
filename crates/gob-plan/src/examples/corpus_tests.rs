//! Section-12 corpus rules run through `run_example`: kinds `directive`, edge relations `calls`
//! and `resolves to`, and language-less examples with `diff`, `lease` and `config` inputs.

// frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
use super::run_example;
use crate::grl::parse;
use gob_text::FileInterner;

fn run_all(name: &str, src: &str) {
    run_except(name, src, &[]);
}

/// Runs every example except the indices in `skip` (blocked on model gaps outside this crate).
fn run_except(name: &str, src: &str, skip: &[usize]) {
    let parsed = parse(FileInterner::new().intern(name), src);
    assert!(parsed.is_ok(), "{name}: {:?}", parsed.errors);
    let rule = &parsed.file.rules[0];
    assert!(!rule.examples.is_empty(), "{name} has no examples");
    for (i, e) in rule.examples.iter().enumerate() {
        if skip.contains(&i) {
            continue;
        }
        let r = run_example(rule, e).unwrap_or_else(|err| panic!("{name} example {i}: {err}"));
        assert!(r.passed, "{name} example {i}: {}", r.diff);
    }
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn todo001_directive_examples_pass() {
    run_all("TODO001.grl", include_str!("corpus/TODO001.grl"));
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn cov001_calls_examples_pass() {
    run_all("COV001.grl", include_str!("corpus/COV001.grl"));
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn neat013_resolves_to_examples_pass() {
    run_all("NEAT013.grl", include_str!("corpus/NEAT013.grl"));
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn scope001_language_less_examples_pass() {
    run_all("SCOPE001.grl", include_str!("corpus/SCOPE001.grl"));
}

/// The six section-12 rules (TODO001 DOC002 COV001 INV002 SCOPE001 NEAT013) lower, so no example fails to lower.
// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn section_12_rules_never_fail_with_a_lowering_error() {
    use crate::examples::RunError;
    let fixtures = [
        (
            "TODO001.grl",
            include_str!("../grl/parse/tests/fixtures/TODO001.grl"),
        ),
        (
            "DOC002.grl",
            include_str!("../grl/parse/tests/fixtures/DOC002.grl"),
        ),
        (
            "COV001.grl",
            include_str!("../grl/parse/tests/fixtures/COV001.grl"),
        ),
        (
            "INV002.grl",
            include_str!("../grl/parse/tests/fixtures/INV002.grl"),
        ),
        (
            "SCOPE001.grl",
            include_str!("../grl/parse/tests/fixtures/SCOPE001.grl"),
        ),
        (
            "NEAT013.grl",
            include_str!("../grl/parse/tests/fixtures/NEAT013.grl"),
        ),
    ];
    for (name, src) in fixtures {
        let parsed = parse(FileInterner::new().intern(name), src);
        assert!(parsed.is_ok(), "{name}: {:?}", parsed.errors);
        let rule = &parsed.file.rules[0];
        for (i, e) in rule.examples.iter().enumerate() {
            if let Err(RunError::Lower(err)) = run_example(rule, e) {
                panic!("{name} example {i}: {err}");
            }
        }
    }
}
