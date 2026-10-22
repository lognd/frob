//! Fix-harness fixtures for the Deterministic directive rules (DSL002, DSL003).
//!
//! The observe closure runs the real scanner over each file, so the proposed fixes are exactly
//! what `--fix` would apply; the harness drives them to a fixpoint and snapshots the diff.
#![allow(missing_docs)]

// frob:ticket 01M5G2WH43B41KTYYK40WS3RZW

mod common;

use std::collections::BTreeMap;

use gob_directives::{Dsl001, Dsl002, Dsl003, Parse001, Parse002};
use gob_fix::{
    Edit, FindingClass, Fix, Fixture, Observation, ObservedFinding, Outcome, Tier, Violation,
    missing_fixtures, run_fixture,
};
use gob_rules::{FixKind, Registry, RuleMeta};

/// Observe `files` with the real scanner; every finding is a firing one, fixable iff `tier` admits its fix.
fn observe(tier: Tier, files: &BTreeMap<String, String>) -> Observation {
    let mut obs = Observation::default();
    for (path, text) in files {
        let result = common::scan(path, text);
        for finding in result.findings {
            let fix = finding.fix.as_ref().map(|f| Fix {
                rule: finding.rule.to_string(),
                title: f.title.clone(),
                applicability: f.applicability,
                edits: f
                    .edits
                    .iter()
                    .map(|e| {
                        let range = e.range.to_usize_range();
                        Edit {
                            path: path.clone(),
                            start: range.start,
                            end: range.end,
                            replacement: e.replacement.clone(),
                        }
                    })
                    .collect(),
            });
            obs.findings.push(ObservedFinding {
                rule: finding.rule.to_string(),
                key: finding.fingerprint.to_hex(),
                class: FindingClass::Fire,
                fixable: fix.as_ref().is_some_and(|f| tier.admits(f.applicability)),
            });
            obs.fixes.extend(fix);
        }
    }
    obs
}

fn fixture(name: &str, rule: &str, files: &[(&str, &str)]) -> Fixture {
    Fixture {
        name: name.into(),
        rule: rule.into(),
        files: files
            .iter()
            .map(|(p, t)| ((*p).into(), (*t).into()))
            .collect(),
    }
}

fn run(f: &Fixture, tier: Tier) -> Outcome {
    run_fixture(f, tier, &|files| observe(tier, files))
}

/// Every fixture that must exist: one per Deterministic rule.
fn fixtures() -> Vec<Fixture> {
    vec![
        fixture(
            "v1_keys",
            "DSL002",
            &[
                (
                    "src/a.rs",
                    "// frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 note=\"two   words\"\nfn a() {}\n\n// frob:invariant name reason=\"why\"\nfn b() {}\n",
                ),
                (
                    "src/b.rs",
                    "// frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 note=\"third\"\nfn c() {}\n",
                ),
                ("src/clean.rs", "fn untouched() {}\n"),
            ],
        ),
        fixture(
            "deprecated_spellings",
            "DSL003",
            &[(
                "src/a.rs",
                "// frob:pure\nfn a() {}\n\n// frob:honest\nfn b() {}\n\n// frob:core\nfn c() {}\n",
            )],
        ),
    ]
}

/// Snapshot the outcome under `tests/fixtures/snapshots`, which the directive scan excludes.
fn snap(name: &str, out: &Outcome) {
    insta::with_settings!({ snapshot_path => "fixtures/snapshots", prepend_module_to_snapshot => false }, {
        insta::assert_snapshot!(name, out.snapshot_text());
    });
}

// frob:tests run_fixture
// frob:tests Outcome.snapshot_text
#[test]
fn dsl002_v1_keys_fix_to_a_fixpoint() {
    let f = &fixtures()[0];
    let out = run(f, Tier::A);
    assert!(out.passed(), "{:?}", out.violations);
    assert_eq!(out.rounds, 1);
    snap("dsl002_v1_keys", &out);
}

// frob:tests run_fixture
// frob:tests Outcome.snapshot_text
#[test]
fn dsl003_deprecated_spellings_fix_to_a_fixpoint() {
    let f = &fixtures()[1];
    let out = run(f, Tier::A);
    assert!(out.passed(), "{:?}", out.violations);
    assert_eq!(out.rounds, 1);
    snap("dsl003_deprecated_spellings", &out);
}

// frob:tests run_fixture
#[test]
fn fixed_output_is_idempotent_and_clean() {
    for f in fixtures() {
        let out = run(&f, Tier::A);
        let again = Fixture {
            files: out.files.clone(),
            ..f.clone()
        };
        let second = run(&again, Tier::A);
        assert_eq!(second.rounds, 0, "{}: second run changed files", f.name);
        assert_eq!(second.files, out.files, "{}", f.name);
        assert!(
            out.files.values().all(|t| observe(
                Tier::A,
                &BTreeMap::from([("src/a.rs".into(), t.clone())])
            )
            .findings
            .is_empty()),
            "{}: findings survive the fixpoint",
            f.name
        );
    }
}

// frob:tests run_fixture
#[test]
fn clean_input_is_a_no_op() {
    let out = run(
        &fixture("clean", "DSL002", &[("src/a.rs", "fn a() {}\n")]),
        Tier::A,
    );
    assert!(out.passed());
    assert_eq!(out.rounds, 0);
    assert_eq!(out.snapshot_text(), "rounds: 0\n");
}

// frob:tests run_fixture
#[test]
fn finding_without_a_fix_is_left_alone() {
    // An abbreviated ticket id is DSL002 but has no mechanical repair.
    let f = fixture(
        "abbreviated",
        "DSL002",
        &[("src/a.rs", "// frob:ticket ~3M8Z4T7\nfn a() {}\n")],
    );
    assert!(!observe(Tier::A, &f.files).findings.is_empty());
    let out = run(&f, Tier::A);
    assert!(out.passed(), "{:?}", out.violations);
    assert_eq!(out.rounds, 0);
    assert_eq!(out.files, f.files);
}

// frob:tests run_fixture
#[test]
fn placeholder_fix_waits_for_a_higher_tier() {
    // `frob:hook` offers a HasPlaceholders fix: untouched at tier A, applied at tier C.
    let f = fixture(
        "hook",
        "DSL003",
        &[("src/a.rs", "// frob:hook\nfn a() {}\n")],
    );
    let a = run(&f, Tier::A);
    assert!(a.passed(), "{:?}", a.violations);
    assert_eq!(a.files, f.files);
    let c = run(&f, Tier::C);
    assert!(c.passed(), "{:?}", c.violations);
    assert_eq!(c.rounds, 1);
    assert!(c.files["src/a.rs"].contains("frob:accept NEAT030"));
}

// frob:tests missing_fixtures
#[test]
fn every_deterministic_rule_has_a_fixture() {
    let metas: [&'static RuleMeta; 5] = [
        &Parse001::META,
        &Parse002::META,
        &Dsl001::META,
        &Dsl002::META,
        &Dsl003::META,
    ];
    let registry = Registry::from_metas(metas);
    let fixable: Vec<&str> = registry
        .iter()
        .filter(|m| m.fix == FixKind::Deterministic)
        .map(|m| m.id)
        .collect();
    assert_eq!(fixable, ["DSL002", "DSL003"]);
    assert_eq!(missing_fixtures(&fixable, &fixtures()), []);
}

// frob:tests missing_fixtures
#[test]
fn a_rule_without_a_fixture_is_reported() {
    let only = [fixtures().remove(0)];
    assert_eq!(
        missing_fixtures(&["DSL002", "DSL003"], &only),
        [Violation::NoFixture {
            rule: "DSL003".into()
        }]
    );
}
