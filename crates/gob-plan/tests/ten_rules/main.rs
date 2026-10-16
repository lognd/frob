//! Acceptance corpus A: six grl-spec.md section 12 rules written in GRL, examples all pass.

// frob:ticket 01M3ZX7HW6V59EBYZ2A0HC06TD

use gob_plan::examples::run_example;
use gob_plan::grl::parse;
use gob_text::FileInterner;

const RULES: [(&str, &str); 6] = [
    ("TODO001", include_str!("TODO001.grl")),
    ("DOC002", include_str!("DOC002.grl")),
    ("COV001", include_str!("COV001.grl")),
    ("INV002", include_str!("INV002.grl")),
    ("SCOPE001", include_str!("SCOPE001.grl")),
    ("NEAT013", include_str!("NEAT013.grl")),
];

/// Run every example of one corpus rule and return failure descriptions.
fn failures(name: &str) -> Vec<String> {
    let src = RULES.iter().find(|(n, _)| *n == name).expect("known rule").1;
    let parsed = parse(FileInterner::new().intern(&format!("rules/{name}.grl")), src);
    assert!(parsed.is_ok(), "{name}: {:?}", parsed.errors);
    let rule = &parsed.file.rules[0];
    assert!(!rule.examples.is_empty(), "{name} has no examples");
    rule.examples
        .iter()
        .enumerate()
        .filter_map(|(i, e)| match run_example(rule, e) {
            Ok(r) if r.passed => None,
            Ok(r) => Some(format!("{name} example {i}: {}", r.diff)),
            Err(err) => Some(format!("{name} example {i}: {err:?}")),
        })
        .collect()
}

macro_rules! corpus_test {
    ($fn:ident, $name:literal) => {
        #[test]
        fn $fn() {
            let f = failures($name);
            assert!(f.is_empty(), "{}", f.join("\n"));
        }
    };
}

corpus_test!(todo001_examples_pass, "TODO001");
corpus_test!(doc002_examples_pass, "DOC002");
corpus_test!(cov001_examples_pass, "COV001");
corpus_test!(inv002_examples_pass, "INV002");
corpus_test!(scope001_examples_pass, "SCOPE001");
corpus_test!(neat013_examples_pass, "NEAT013");
