//! `CFG001` fix fixtures: the gob-fix harness over the real check and materialize pipeline.

// frob:ticket 01M5G2WH1J8G8WR3PGF5N3TAQD

mod common;

use std::collections::BTreeMap;

use gob_config::{check, materialize};
use gob_fix::{
    Applicability, Edit, FindingClass, Fix, Fixture, Observation, ObservedFinding, Outcome, Tier,
    missing_fixtures, run_fixture,
};
use gob_rules::{FixKind, Registry};

const PATH: &str = "frob.toml";

/// Build a fixture for CFG001 holding one `frob.toml`.
fn fixture(name: &str, text: &str) -> Fixture {
    Fixture {
        name: name.into(),
        rule: "CFG001".into(),
        files: BTreeMap::from([(PATH.to_owned(), text.to_owned())]),
    }
}

/// Check the current `frob.toml`; the fix is the whole file as `materialize` would write it.
fn observe(files: &BTreeMap<String, String>) -> Observation {
    let text = &files[PATH];
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join(PATH), text).expect("write fixture");
    let (t, l) = common::tables();
    let found = check(dir.path(), "frob", &[&t, &l]).expect("check reads the fixture");
    let mut o = Observation::default();
    o.parse.insert(PATH.to_owned(), gob_fix::ParseStatus::Clean);
    for f in &found {
        o.findings.push(ObservedFinding {
            rule: f.rule.to_string(),
            key: f.fingerprint.to_hex(),
            class: FindingClass::Fire,
            fixable: true,
        });
    }
    if !found.is_empty() {
        materialize(dir.path(), "frob", &[&t, &l]).expect("materialize");
        let fixed = std::fs::read_to_string(dir.path().join(PATH)).expect("read fixed");
        // One whole-file edit however many knobs are missing, so edits never overlap.
        o.fixes.push(Fix {
            rule: "CFG001".into(),
            title: "materialize missing knobs".into(),
            applicability: Applicability::Machine,
            edits: vec![Edit {
                path: PATH.to_owned(),
                start: 0,
                end: text.len(),
                replacement: fixed,
            }],
        });
    }
    o
}

/// Run a fixture, require a pass and a clean final observation.
fn run(f: &Fixture) -> Outcome {
    let out = run_fixture(f, Tier::A, &observe);
    assert!(out.passed(), "{:?}", out.violations);
    let after = observe(&out.files);
    assert!(after.findings.is_empty(), "knobs remain after the fixpoint");
    out
}

// frob:tests run_fixture
#[test]
fn partial_file_gains_missing_knobs_and_keeps_comments() {
    let f = fixture(
        "partial",
        "# my settings\n[tickets]\ncas_retries = 9 # tuned\n",
    );
    let out = run(&f);
    assert_eq!(out.rounds, 1);
    assert!(out.files[PATH].contains("cas_retries = 9 # tuned"));
    insta::assert_snapshot!("cfg001_partial", out.snapshot_text());
}

// frob:tests run_fixture
#[test]
fn empty_file_fires_every_knob_and_converges_in_one_round() {
    let out = run(&fixture("empty", ""));
    assert_eq!(out.rounds, 1);
    insta::assert_snapshot!("cfg001_empty", out.snapshot_text());
}

// frob:tests run_fixture
#[test]
fn complete_file_is_a_no_op() {
    let text =
        "[tickets]\ncas_retries = 5\nref = \"trunk\"\n\n[tickets.lease]\nttl_minutes = 120\n";
    let out = run(&fixture("clean", text));
    assert_eq!(out.rounds, 0);
    assert_eq!(out.files[PATH], text);
    assert_eq!(out.snapshot_text(), "rounds: 0\n");
}

// frob:tests run_fixture
#[test]
fn fixed_output_is_a_fixpoint() {
    let first = run(&fixture("again", "[tickets]\nref = \"branch\"\n"));
    let second = run(&fixture("again2", &first.files[PATH]));
    assert_eq!(second.rounds, 0);
    assert_eq!(second.files, first.files);
}

// frob:tests missing_fixtures
#[test]
fn every_deterministic_config_rule_has_a_fixture() {
    let fixtures = [fixture("partial", ""), fixture("empty", "")];
    let fixable: Vec<&str> = Registry::global()
        .iter()
        .filter(|m| m.fix == FixKind::Deterministic && m.module == "gob_config")
        .map(|m| m.id)
        .collect();
    assert!(fixable.contains(&"CFG001"));
    assert!(missing_fixtures(&fixable, &fixtures).is_empty());
    assert!(!missing_fixtures(&fixable, &[]).is_empty());
}
