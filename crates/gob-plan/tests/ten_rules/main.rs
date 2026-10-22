//! Acceptance corpus A and B: ten grl-spec.md section 12 rules written in GRL, examples all pass.

// frob:ticket 01M3ZX7HW6V59EBYZ2A0HC06TD

use gob_plan::examples::run_example;
use gob_plan::grl::parse;
use gob_text::FileInterner;

const RULES: [(&str, &str); 10] = [
    ("TODO001", include_str!("cases/TODO001.grl")),
    ("DOC002", include_str!("cases/DOC002.grl")),
    ("COV001", include_str!("cases/COV001.grl")),
    ("INV002", include_str!("cases/INV002.grl")),
    ("SCOPE001", include_str!("cases/SCOPE001.grl")),
    ("NEAT013", include_str!("cases/NEAT013.grl")),
    ("SYS001", include_str!("cases/SYS001.grl")),
    ("CAP001", include_str!("cases/CAP001.grl")),
    ("NEAT031", include_str!("cases/NEAT031.grl")),
    ("CI002", include_str!("cases/CI002.grl")),
];

/// Examples the current engine cannot yet judge, as (rule, example index); each is a filed gap.
///
/// A listed example must still fail: when the engine learns the feature the test fails
/// and the entry is deleted, so the list can only shrink.
const KNOWN_ENGINE_GAPS: [(&str, usize); 1] = [
    ("DOC002", 1), // example runner lacks multi-file `file "..."` inputs
];

/// Run every example of one corpus rule and return (index, description) of each failure.
fn failures(name: &str) -> Vec<(usize, String)> {
    let src = RULES
        .iter()
        .find(|(n, _)| *n == name)
        .expect("known rule")
        .1;
    let parsed = parse(
        FileInterner::new().intern(&format!("rules/{name}.grl")),
        src,
    );
    assert!(parsed.is_ok(), "{name}: {:?}", parsed.errors);
    gob_plan::examples::install_model_reader(grimble_check::example_model::read_example_model);
    let rule = &parsed.file.rules[0];
    assert!(!rule.examples.is_empty(), "{name} has no examples");
    rule.examples
        .iter()
        .enumerate()
        .filter_map(|(i, e)| match run_example(rule, e) {
            Ok(r) if r.passed => None,
            Ok(r) => Some((i, format!("{name} example {i}: {}", r.diff))),
            Err(err) => Some((i, format!("{name} example {i}: {err:?}"))),
        })
        .collect()
}

macro_rules! corpus_test {
    ($fn:ident, $name:literal) => {
        #[test]
        fn $fn() {
            let f = failures($name);
            let got: Vec<usize> = f.iter().map(|(i, _)| *i).collect();
            let want: Vec<usize> = KNOWN_ENGINE_GAPS
                .iter()
                .filter(|(n, _)| *n == $name)
                .map(|(_, i)| *i)
                .collect();
            let text: Vec<&str> = f.iter().map(|(_, t)| t.as_str()).collect();
            assert_eq!(
                got,
                want,
                "failing examples differ from the gap list:\n{}",
                text.join("\n")
            );
        }
    };
}

corpus_test!(todo001_examples_pass, "TODO001");
corpus_test!(doc002_examples_pass, "DOC002");
corpus_test!(cov001_examples_pass, "COV001");
corpus_test!(inv002_examples_pass, "INV002");
corpus_test!(scope001_examples_pass, "SCOPE001");
corpus_test!(neat013_examples_pass, "NEAT013");
corpus_test!(sys001_examples_pass, "SYS001");
corpus_test!(cap001_examples_pass, "CAP001");
corpus_test!(neat031_examples_pass, "NEAT031");
corpus_test!(ci002_examples_pass, "CI002");
