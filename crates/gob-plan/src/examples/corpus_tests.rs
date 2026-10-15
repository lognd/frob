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
    // Examples 1-2 need the models to mark test items (no `test` attr is emitted for rust or
    // python-in-example); see the follow-up ticket.
    run_except("COV001.grl", include_str!("corpus/COV001.grl"), &[1, 2]);
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn neat013_resolves_to_examples_pass() {
    // Example 0 (python `time.time()`) needs vocab classes and import resolution; follow-up ticket.
    run_except("NEAT013.grl", include_str!("corpus/NEAT013.grl"), &[0]);
}

// frob:tests crates/gob-plan/src/examples/runner.rs::run_example
#[test]
fn scope001_language_less_examples_pass() {
    run_all("SCOPE001.grl", include_str!("corpus/SCOPE001.grl"));
}
