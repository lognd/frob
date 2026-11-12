//! Self-tests for the fix harness: a toy language with balanced-paren parsing and `mac!{` regions.
#![allow(missing_docs)]

use std::collections::BTreeMap;

use gob_fix::{
    Applicability, Edit, FindingClass, Fix, Fixture, MAX_ROUNDS, Observation, ObservedFinding,
    Outcome, ParseStatus, Tier, Violation, missing_fixtures, run_fixture,
};

/// A toy rule: `find` becomes `replace`; matches inside a `mac!{ .. }` region are unresolved.
struct Toy {
    id: &'static str,
    find: &'static str,
    replace: &'static str,
}

fn macro_spans(text: &str) -> Vec<(usize, usize)> {
    text.match_indices("mac!{")
        .map(|(s, _)| (s, text[s..].find('}').map_or(text.len(), |e| s + e + 1)))
        .collect()
}

fn observe(rules: &[Toy], files: &BTreeMap<String, String>) -> Observation {
    let mut o = Observation::default();
    for (path, text) in files {
        let depth = text.chars().try_fold(0i32, |d, c| match c {
            '(' => Some(d + 1),
            ')' if d > 0 => Some(d - 1),
            ')' => None,
            _ => Some(d),
        });
        let status = if depth == Some(0) {
            ParseStatus::Clean
        } else {
            ParseStatus::Failed
        };
        o.parse.insert(path.clone(), status);
        let spans = macro_spans(text);
        o.opaque += spans.len();
        o.holes += text.matches("???").count();
        for r in rules {
            for (at, _) in text.match_indices(r.find) {
                let inside = spans.iter().any(|(s, e)| *s <= at && at < *e);
                let class = if inside {
                    FindingClass::Unresolved
                } else {
                    FindingClass::Fire
                };
                o.findings.push(ObservedFinding {
                    rule: r.id.into(),
                    key: format!("{}:{}", r.id, r.find),
                    class,
                    fixable: !inside,
                });
                if !inside {
                    o.fixes.push(Fix {
                        rule: r.id.into(),
                        title: r.id.into(),
                        applicability: Applicability::Machine,
                        edits: vec![Edit {
                            path: path.clone(),
                            start: at,
                            end: at + r.find.len(),
                            replacement: r.replace.into(),
                        }],
                    });
                }
            }
        }
    }
    o
}

fn fixture(name: &str, files: &[(&str, &str)]) -> Fixture {
    Fixture {
        name: name.into(),
        rule: "TOY001".into(),
        files: files
            .iter()
            .map(|(p, t)| ((*p).into(), (*t).into()))
            .collect(),
    }
}

fn run(rules: &[Toy], f: &Fixture) -> Outcome {
    run_fixture(f, Tier::A, &|files| observe(rules, files))
}

const RENAME: Toy = Toy {
    id: "TOY001",
    find: "old_api",
    replace: "new_api",
};

// frob:tests run_fixture
// frob:tests crates/gob-fix/src/harness.rs::Outcome.snapshot_text
// frob:tests crates/gob-fix/src/harness.rs::Outcome.passed
#[test]
fn converging_multi_file_fixture_snapshots_its_diff() {
    let f = fixture(
        "rename",
        &[
            ("a.toy", "call(old_api)\nkeep\nold_api(1)\n"),
            ("b.toy", "x\ny\nz\nold_api\n"),
            ("c.toy", "untouched\n"),
        ],
    );
    let out = run(&[RENAME], &f);
    assert!(out.passed(), "{:?}", out.violations);
    insta::assert_snapshot!("converging_rename", out.snapshot_text());
}

// frob:tests run_fixture
#[test]
fn no_fixes_is_zero_rounds_and_empty_diff() {
    let out = run(&[RENAME], &fixture("clean", &[("a.toy", "fine\n")]));
    assert!(out.passed());
    assert_eq!(out.rounds, 0);
    assert_eq!(out.snapshot_text(), "rounds: 0\n");
}

// frob:tests run_fixture
#[test]
fn overlapping_fixes_converge_over_rounds() {
    let rules = [
        Toy {
            id: "TOY001",
            find: "ab",
            replace: "xb",
        },
        Toy {
            id: "TOY002",
            find: "bc",
            replace: "yy",
        },
    ];
    let out = run(&rules, &fixture("overlap", &[("a.toy", "abc\n")]));
    assert!(out.passed(), "{:?}", out.violations);
    assert_eq!(out.files["a.toy"], "xbc\n".replace("bc", "yy"));
    assert_eq!(out.rounds, 2);
}

// frob:tests run_fixture
#[test]
fn oscillating_fix_fails_to_reach_a_fixpoint() {
    let rules = [
        Toy {
            id: "TOY001",
            find: "ping",
            replace: "pong",
        },
        Toy {
            id: "TOY002",
            find: "pong",
            replace: "ping",
        },
    ];
    let out = run(&rules, &fixture("osc", &[("a.toy", "ping\n")]));
    assert_eq!(out.violations, vec![Violation::NoFixpoint]);
    assert_eq!(out.rounds, MAX_ROUNDS);
}

// frob:tests run_fixture
#[test]
fn parse_breaking_fix_fails() {
    let rules = [Toy {
        id: "TOY001",
        find: "foo()",
        replace: "foo(",
    }];
    let out = run(&rules, &fixture("brk", &[("a.toy", "foo()\n")]));
    assert_eq!(
        out.violations,
        vec![Violation::ParseDegraded {
            round: 1,
            path: "a.toy".into(),
            before: ParseStatus::Clean,
            after: ParseStatus::Failed,
        }]
    );
}

// frob:tests run_fixture
#[test]
fn macro_wrapping_fix_fails_when_fire_becomes_opaque() {
    let rules = [Toy {
        id: "TOY001",
        find: "danger",
        replace: "mac!{ danger }",
    }];
    let out = run(&rules, &fixture("mac", &[("a.toy", "danger\n")]));
    assert!(out.violations.contains(&Violation::OpaqueIncreased {
        round: 1,
        before: 0,
        after: 1
    }));
    assert!(out.violations.contains(&Violation::ClassChanged {
        round: 1,
        rule: "TOY001".into(),
        key: "TOY001:danger".into()
    }));
}

// frob:tests run_fixture
#[test]
fn macro_wrapping_that_hides_the_finding_still_fails_on_opaque_count() {
    let rules = [Toy {
        id: "TOY001",
        find: "danger",
        replace: "mac!{ safe }",
    }];
    let out = run(&rules, &fixture("mac2", &[("a.toy", "danger\n")]));
    assert_eq!(
        out.violations,
        vec![Violation::OpaqueIncreased {
            round: 1,
            before: 0,
            after: 1
        }]
    );
}

// frob:tests run_fixture
#[test]
fn hole_growth_fails() {
    let rules = [Toy {
        id: "TOY001",
        find: "todo",
        replace: "???",
    }];
    let out = run(&rules, &fixture("hole", &[("a.toy", "todo\n")]));
    assert_eq!(
        out.violations,
        vec![Violation::HolesIncreased {
            round: 1,
            before: 0,
            after: 1
        }]
    );
}

// frob:tests run_fixture
#[test]
fn no_op_fix_leaves_a_fixable_finding() {
    let rules = [Toy {
        id: "TOY001",
        find: "same",
        replace: "same",
    }];
    let out = run(&rules, &fixture("noop", &[("a.toy", "same\n")]));
    assert_eq!(
        out.violations,
        vec![Violation::FixableRemains {
            rule: "TOY001".into(),
            key: "TOY001:same".into()
        }]
    );
}

// frob:tests run_fixture
#[test]
fn out_of_range_edit_is_invalid() {
    let f = fixture("range", &[("a.toy", "abc\n")]);
    let out = run_fixture(&f, Tier::A, &|_| Observation {
        fixes: vec![Fix {
            rule: "TOY001".into(),
            title: "bad".into(),
            applicability: Applicability::Machine,
            edits: vec![Edit {
                path: "a.toy".into(),
                start: 0,
                end: 99,
                replacement: String::new(),
            }],
        }],
        ..Observation::default()
    });
    assert_eq!(
        out.violations,
        vec![Violation::InvalidEdit {
            round: 1,
            path: "a.toy".into()
        }]
    );
}

// frob:tests missing_fixtures
#[test]
fn fixable_rule_without_fixture_is_named_and_no_fixable_rules_pass() {
    let f = [fixture("rename", &[("a.toy", "x")])];
    assert!(missing_fixtures(&[], &f).is_empty());
    assert!(missing_fixtures(&["TOY001"], &f).is_empty());
    assert_eq!(
        missing_fixtures(&["TOY001", "TOY009"], &f),
        vec![Violation::NoFixture {
            rule: "TOY009".into()
        }]
    );
}
