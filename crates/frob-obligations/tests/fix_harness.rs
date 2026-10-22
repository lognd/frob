//! gob-fix harness over the `TICK006` fix: fixture, fixpoint run, diff snapshot and registry coverage.
// frob:ticket 01M5G2WH7Q04ERV0MCR8ERTF75

mod common;

use std::collections::BTreeMap;

use frob_obligations::{InvariantsConfig, collect, evaluate};
use gob_fix::{
    Edit, FindingClass, Fix, Fixture, Observation, ObservedFinding, Outcome, Tier, Violation,
    missing_fixtures, run_fixture,
};
use gob_rules::{FixKind, Registry};

const RULE: &str = "TICK006";
const ULID_A: &str = "01M3ZX86MA30ABW915Z943BQYB";
const ULID_B: &str = "01M5G2WH7Q04ERV0MCR8ERTF75";

/// Observe `files` through the real check pipeline (collect then evaluate) and report the `TICK006` findings and fixes.
fn observe(files: &BTreeMap<String, String>) -> Observation {
    let dir = tempfile::tempdir().expect("tempdir");
    for (path, text) in files {
        common::write_tree(dir.path(), &[(path.as_str(), text.as_str())]);
    }
    let collected = collect(dir.path()).expect("collect");
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let inputs = collected.inputs(dir.path(), None, &config);
    let ev = evaluate(&inputs);
    let mut obs = Observation::default();
    for f in ev.findings.iter().filter(|f| f.rule.as_str() == RULE) {
        let fix = f.fix.as_ref().filter(|x| x.kind == FixKind::Deterministic);
        obs.findings.push(ObservedFinding {
            rule: RULE.to_owned(),
            key: f.fingerprint.to_hex(),
            class: FindingClass::Fire,
            fixable: fix.is_some(),
        });
        if let Some(x) = fix {
            obs.fixes.push(Fix {
                rule: RULE.to_owned(),
                title: x.title.clone(),
                applicability: x.applicability,
                edits: x
                    .edits
                    .iter()
                    .map(|e| Edit {
                        path: ev.files.path(e.file).expect("path").to_owned(),
                        start: u32::from(e.range.start()) as usize,
                        end: u32::from(e.range.end()) as usize,
                        replacement: e.replacement.clone(),
                    })
                    .collect(),
            });
        }
    }
    obs
}

fn fixture(name: &str, files: &[(&str, &str)]) -> Fixture {
    Fixture {
        name: name.to_owned(),
        rule: RULE.to_owned(),
        files: files
            .iter()
            .map(|(p, t)| ((*p).to_owned(), (*t).to_owned()))
            .collect(),
    }
}

fn run(f: &Fixture) -> Outcome {
    run_fixture(f, Tier::A, &observe)
}

fn old_form(ulid: &str) -> String {
    format!("tickets/{ulid}/ticket.md")
}

// frob:tests run_fixture
// frob:tests crates/gob-fix/src/harness.rs::Outcome.snapshot_text
#[test]
fn tick006_fix_rewrites_old_ticket_paths_to_a_fixpoint_with_a_diff_snapshot() {
    let a = old_form(ULID_A);
    let b = old_form(ULID_B);
    let f = fixture(
        "tick006_old_form",
        &[
            ("docs/note.md", &format!("see {a} and {b}\nagain {a}.\n")),
            ("docs/other.md", &format!("[x]({b})\n")),
        ],
    );
    let out = run(&f);
    assert!(out.passed(), "{:?}", out.violations);
    assert_eq!(out.rounds, 1, "one round fixes every link at once");
    assert!(!out.files["docs/note.md"].contains("ticket.md"));
    insta::assert_snapshot!("tick006_old_form", out.snapshot_text());
}

// frob:tests run_fixture
#[test]
fn tick006_fix_is_idempotent_when_rerun_on_its_own_output() {
    let a = old_form(ULID_A);
    let first = run(&fixture("first", &[("docs/n.md", &format!("see {a}\n"))]));
    assert!(first.passed(), "{:?}", first.violations);
    let again = fixture(
        "second",
        &first
            .files
            .iter()
            .map(|(p, t)| (p.as_str(), t.as_str()))
            .collect::<Vec<_>>(),
    );
    let second = run(&again);
    assert!(second.passed(), "{:?}", second.violations);
    assert_eq!(second.rounds, 0);
    assert_eq!(second.files, first.files);
}

// frob:tests run_fixture
#[test]
fn tick006_fix_on_clean_and_generated_text_is_a_no_op() {
    let a = old_form(ULID_A);
    let generated = format!(
        "{} v1: DO NOT EDIT -->\n{a}\n",
        frob_ledger::reindex::GENERATED_MARKER_PREFIX
    );
    let f = fixture(
        "tick006_noop",
        &[
            (
                "docs/clean.md",
                "see docs/design/navigation.md and ../README.md\n",
            ),
            ("docs/generated.md", &generated),
        ],
    );
    let out = run(&f);
    assert!(out.passed(), "{:?}", out.violations);
    assert_eq!(out.rounds, 0);
    assert_eq!(out.snapshot_text(), "rounds: 0\n");
    assert_eq!(out.files, f.files);
}

// frob:tests missing_fixtures
#[test]
fn every_deterministic_rule_of_this_crate_has_a_fix_fixture() {
    let fixtures = [fixture("tick006_old_form", &[])];
    let fixable: Vec<&str> = Registry::global()
        .iter()
        .filter(|m| m.fix == FixKind::Deterministic && m.module.starts_with("frob_obligations"))
        .map(|m| m.id)
        .collect();
    assert!(fixable.contains(&RULE), "{fixable:?}");
    assert_eq!(
        missing_fixtures(&fixable, &fixtures),
        Vec::<Violation>::new()
    );
    assert_eq!(
        missing_fixtures(&fixable, &[]).len(),
        fixable.len(),
        "an uncovered fixable rule is reported"
    );
}
