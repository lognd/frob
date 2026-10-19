//! The PATH001, PATH002 and PATH003 rule pages as an mdtest corpus, plus the acceptance tests.

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1

use gob_languages::Language;
use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_text::FileInterner;
use grimble_lints::pass::{PathFile, PathFinding, analyze};
use grimble_lints::path::Options;

/// Analyze one file and return its findings.
fn run(path: &str, text: &str) -> Vec<PathFinding> {
    let language = Language::detect(path).expect("a known extension");
    analyze(
        &[PathFile {
            path,
            language,
            text,
        }],
        &Options::default(),
    )
    .findings
}

/// Run one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-lints/src/rules/path001.rs::Path001
    // frob:tests crates/grimble-lints/src/rules/path002.rs::Path002
    // frob:tests crates/grimble-lints/src/rules/path003.rs::Path003
    let mut files = FileInterner::new();
    run(&case.file_name, &case.text)
        .into_iter()
        .filter(|f| f.rule == case.rule.as_str())
        .filter_map(|f| f.into_finding(&mut files))
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);

#[test]
fn absolute_path_is_an_error_outside_tests_and_advisory_inside() {
    // frob:tests crates/grimble-lints/src/pass.rs::analyze
    let src = "fn f() -> &'static str {\n    \"/home/ann/data.txt\"\n}\n";
    let lib = run("src/lib.rs", src);
    assert_eq!(lib.len(), 1, "{lib:?}");
    assert_eq!((lib[0].rule, lib[0].severity), ("PATH001", Severity::Error));
    let test = run("tests/a.rs", src);
    assert_eq!(test[0].severity, Severity::Advisory, "{test:?}");
}

#[test]
fn language_without_roles_is_unresolved_for_fidelity() {
    // frob:tests crates/grimble-lints/src/pass.rs::analyze
    let found = run("src/a.ts", "export const x = p.startsWith(\"src/\");\n");
    let rules: Vec<_> = found.iter().map(|f| f.rule).collect();
    assert_eq!(rules, ["PATH002", "PATH003"], "{found:?}");
    for f in &found {
        assert_eq!(f.severity, Severity::Unresolved);
        assert_eq!(f.reason, Some(UnresolvedReason::Fidelity));
    }
}

#[test]
fn empty_walk_makes_the_rules_not_applicable() {
    // frob:tests crates/grimble-lints/src/pass.rs::analyze
    let report = analyze(&[], &Options::default());
    let ids: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(ids, ["PATH001", "PATH002", "PATH003"]);
    assert!(report.subjects.is_empty());
}

#[test]
fn subjects_count_files_each_rule_can_judge() {
    // frob:tests crates/grimble-lints/src/pass.rs::analyze
    let rs = PathFile {
        path: "a.rs",
        language: Language::Rust,
        text: "fn f() {}\n",
    };
    let ts = PathFile {
        path: "a.ts",
        language: Language::TypeScript,
        text: "let a = 1;\n",
    };
    let report = analyze(&[rs, ts], &Options::default());
    assert_eq!(report.subjects.get("PATH001"), Some(&2));
    assert_eq!(report.subjects.get("PATH002"), Some(&1));
    assert!(report.not_applicable.is_empty());
}

/// A host with fixed subject counts.
struct Fixed;

impl grimble_lints::host::PathHost for Fixed {
    fn path_subjects_of(&self, id: &str) -> usize {
        id.len()
    }
}

#[test]
fn host_binds_and_converts() {
    // frob:tests crates/grimble-lints/src/rules/mod.rs::bind
    // frob:tests crates/grimble-lints/src/host.rs::PathHost.path_subjects_of
    // frob:tests crates/grimble-lints/src/pass.rs::PathFinding.into_finding
    assert_eq!(grimble_lints::rules::bind::<Fixed>().len(), 3);
    assert_eq!(
        grimble_lints::host::PathHost::path_subjects_of(&Fixed, "PATH003"),
        7
    );
    let found = run(
        "src/lib.rs",
        "fn f() -> &'static str {\n    \"/root/x\"\n}\n",
    );
    let mut files = FileInterner::new();
    let converted: Vec<_> = found
        .into_iter()
        .filter_map(|f| f.into_finding(&mut files))
        .collect();
    assert!(converted.iter().any(|f| f.rule.as_str() == "PATH001"));
}
