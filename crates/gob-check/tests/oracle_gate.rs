//! The committed oracle corpus passes the incompleteness gate (`cohesion.md` section 2.3).

#![allow(
    clippy::disallowed_methods,
    reason = "a test reads committed fixtures, not a walked snapshot"
)]

use std::path::Path;

use gob_check::incompleteness::{gate, measure, parse_baseline, parse_corpus};

fn fixture(name: &str) -> String {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/incompleteness")
        .join(name);
    std::fs::read_to_string(path).expect("read fixture")
}

// frob:tests crates/gob-check/src/incompleteness.rs::gate
// frob:tests crates/gob-check/src/incompleteness.rs::measure
// frob:tests crates/gob-check/src/incompleteness.rs::parse_corpus
// frob:tests crates/gob-check/src/incompleteness.rs::parse_baseline
#[test]
fn corpus_false_unknown_rate_is_reported_and_a_rise_or_false_must_fails() {
    let cases = parse_corpus(&fixture("oracle-corpus.toml")).expect("corpus parses");
    let baseline = parse_baseline(&fixture("baseline.toml")).expect("baseline parses");
    let report = measure(&cases);
    assert!(
        report
            .render_text()
            .contains("python/resolve_ref: 2/3 false Unknown")
    );
    assert!(
        gate(&report, &baseline).is_empty(),
        "{}",
        report.render_text()
    );

    // One more false Unknown in a cell: a rise fails.
    let mut worse = cases.clone();
    let c = worse
        .iter_mut()
        .find(|c| c.language == "rust" && c.capability == "visibility")
        .expect("a rust visibility case");
    c.observed = gob_check::incompleteness::Verdict::Unknown;
    assert_eq!(gate(&measure(&worse), &baseline).len(), 1);

    // A wrong decided answer fails even though the baseline is untouched.
    let mut wrong = cases;
    let c = wrong
        .iter_mut()
        .find(|c| c.id == "rust-visibility-06")
        .expect("case present");
    c.observed = gob_check::incompleteness::Verdict::No;
    let v = gate(&measure(&wrong), &baseline);
    assert!(
        v.iter().any(|x| x.to_string().contains("false Must")),
        "{v:?}"
    );
}
