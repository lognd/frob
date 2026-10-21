//! Parity gate: the Rust crunk against the frozen Python corpus, every difference reasoned.
//!
//! Each captured Python invocation (`tests/crunk-parity/expected/matrix`) is run through the
//! Rust crunk; the exit code and the projected stdout must match the golden or be listed, with a
//! reason, in `tests/crunk-parity/divergences.toml`. A listed difference that has gone away fails
//! too, so the list can only shrink toward retiring the Python crunk (monorepo.md 5 step 3).

// frob:ticket 01M43AVKMT52QCG7DGNQ4J906S

#[path = "parity/compare.rs"]
mod compare;
#[path = "parity/corpus.rs"]
mod corpus;
#[path = "parity/divergences.rs"]
mod divergences;

use std::collections::BTreeSet;

use compare::{Body, Outcome, golden, judge, observe};
use corpus::{Case, load_cases, work_copy};
use divergences::{Divergence, Field};

/// Every parity failure for `cases` run in a fresh work copy against `listed`.
fn run_corpus(cases: &[Case], listed: &[Divergence]) -> Vec<String> {
    let tmp = tempfile::tempdir().expect("tempdir");
    let work = work_copy(tmp.path());
    let known: BTreeSet<&str> = cases.iter().map(|c| c.id.as_str()).collect();
    let mut failures = Vec::new();
    let mut seen = BTreeSet::new();
    for d in listed {
        for id in &d.cases {
            if !known.contains(id.as_str()) {
                failures.push(format!("divergence `{}` names unknown case {id}", d.id));
            } else if !seen.insert(id.clone()) {
                failures.push(format!("{id}: covered by more than one divergence"));
            }
        }
        if d.reason.trim().is_empty() {
            failures.push(format!("divergence `{}` has no reason", d.id));
        }
    }
    for case in cases {
        let want = golden(case, &work);
        let got = observe(case, &work, &want.body);
        let entry = listed.iter().find(|d| d.cases.contains(&case.id));
        failures.extend(judge(case, &want, &got, entry));
    }
    failures
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn every_corpus_project_passes_or_has_a_reasoned_divergence() {
    let failures = run_corpus(&load_cases(), &divergences::load());
    assert!(
        failures.is_empty(),
        "{} parity failure(s):\n{}",
        failures.len(),
        failures.join("\n")
    );
}

fn sample(id: &str) -> Case {
    Case {
        id: id.to_owned(),
        project: "p".to_owned(),
        argv: vec!["check".to_owned()],
        exit: 0,
        stdout: "ok\n".to_owned(),
    }
}

fn entry(fields: Vec<Field>) -> Divergence {
    Divergence {
        id: "D-test".to_owned(),
        cases: vec!["p/c".to_owned()],
        fields,
        reason: "r".to_owned(),
    }
}

fn outcome(exit: i64, text: &str) -> Outcome {
    Outcome {
        exit,
        body: Body::Text(text.to_owned()),
    }
}

// frob:tests crates/crunk/tests/parity/compare.rs::judge
#[test]
fn a_divergence_that_no_longer_differs_fails_and_names_the_entry() {
    let case = sample("p/c");
    let same = outcome(0, "ok");
    let failures = judge(&case, &same, &same, Some(&entry(vec![Field::Stdout])));
    assert_eq!(failures.len(), 1, "{failures:?}");
    assert!(
        failures[0].contains("D-test") && failures[0].contains("p/c"),
        "{failures:?}"
    );
    assert!(failures[0].contains("no longer differs"), "{failures:?}");
}

// frob:tests crates/crunk/tests/parity/compare.rs::judge
#[test]
fn an_unlisted_difference_fails_and_a_listed_one_passes() {
    let case = sample("p/c");
    let (want, got) = (outcome(0, "ok"), outcome(0, "different"));
    assert_eq!(judge(&case, &want, &got, None).len(), 1);
    assert!(judge(&case, &want, &got, Some(&entry(vec![Field::Stdout]))).is_empty());
    assert_eq!(
        judge(&case, &want, &got, Some(&entry(vec![Field::Exit]))).len(),
        2
    );
}

// frob:tests crates/crunk/tests/parity/divergences.rs::parse
#[test]
fn a_divergence_entry_with_an_unknown_case_fails_the_run() {
    let mut d = entry(vec![Field::Exit]);
    d.cases = vec!["nope/none".to_owned()];
    let failures = run_corpus(&[], &[d]);
    assert!(
        failures
            .iter()
            .any(|f| f.contains("D-test") && f.contains("nope/none")),
        "{failures:?}"
    );
}
