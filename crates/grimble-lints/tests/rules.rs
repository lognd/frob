//! The PATH and TIME rule pages as an mdtest corpus, plus the acceptance tests.

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1
// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5
// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01
// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY
// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

use gob_languages::Language;
use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_text::FileInterner;
use grimble_lints::pass::{PathFile, PathFinding, analyze};
use grimble_lints::path::Options;
use grimble_lints::unity_pass::SettingsFile;
use grimble_lints::{err_pass, pair_pass, time_pass, unity_pass};

/// Analyze one file and return its findings.
fn run(path: &str, text: &str) -> Vec<PathFinding> {
    run_with(path, text, &[])
}

/// Analyze one file with the given `ProjectSettings` files and return its findings.
fn run_with(path: &str, text: &str, settings: &[SettingsFile<'_>]) -> Vec<PathFinding> {
    let language = Language::detect(path).expect("a known extension");
    let file = PathFile {
        path,
        language,
        text,
    };
    let mut found = time_pass::analyze(std::slice::from_ref(&file)).findings;
    found.extend(err_pass::analyze(std::slice::from_ref(&file)).findings);
    found.extend(pair_pass::analyze(std::slice::from_ref(&file)).findings);
    found.extend(unity_pass::analyze_all(std::slice::from_ref(&file), settings).findings);
    found.extend(
        analyze(
            &[PathFile {
                path,
                language,
                text,
            }],
            &Options::default(),
        )
        .findings,
    );
    found
}

/// Run one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-lints/src/rules/path001.rs::Path001
    // frob:tests crates/grimble-lints/src/rules/path002.rs::Path002
    // frob:tests crates/grimble-lints/src/rules/path003.rs::Path003
    // frob:tests crates/grimble-lints/src/rules/time001.rs::Time001
    // frob:tests crates/grimble-lints/src/rules/time002.rs::Time002
    // frob:tests crates/grimble-lints/src/rules/err001.rs::Err001
    // frob:tests crates/grimble-lints/src/rules/err002.rs::Err002
    // frob:tests crates/grimble-lints/src/rules/err003.rs::Err003
    // frob:tests crates/grimble-lints/src/rules/pair001.rs::Pair001
    // frob:tests crates/grimble-lints/src/rules/unity201.rs::Unity201
    // frob:tests crates/grimble-lints/src/rules/unity202.rs::Unity202
    // frob:tests crates/grimble-lints/src/rules/unity301.rs::Unity301
    // frob:tests crates/grimble-lints/src/rules/unity302.rs::Unity302
    let mut files = FileInterner::new();
    let settings: Vec<SettingsFile<'_>> = case
        .files
        .iter()
        .filter(|f| unity_pass::is_project_settings(&f.file_name))
        .map(|f| SettingsFile {
            path: &f.file_name,
            text: &f.text,
        })
        .collect();
    run_with(&case.file_name, &case.text, &settings)
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
    let found: Vec<_> = found
        .into_iter()
        .filter(|f| f.rule.starts_with("PATH"))
        .collect();
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

impl grimble_lints::host::TimeHost for Fixed {
    fn time_subjects_of(&self, id: &str) -> usize {
        id.len() + 1
    }
}

impl grimble_lints::host::PairHost for Fixed {
    fn pair_subjects_of(&self, id: &str) -> usize {
        id.len() + 2
    }
}

impl grimble_lints::host::ErrHost for Fixed {
    fn err_subjects_of(&self, id: &str) -> usize {
        id.len() + 4
    }
}

impl grimble_lints::host::UnityHost for Fixed {
    fn unity_subjects_of(&self, id: &str) -> usize {
        id.len() + 3
    }
}

impl grimble_lints::host::PathHost for Fixed {
    fn path_subjects_of(&self, id: &str) -> usize {
        id.len()
    }
}

#[test]
fn host_binds_and_converts() {
    // frob:tests crates/grimble-lints/src/rules/mod.rs::bind
    // frob:tests crates/grimble-lints/src/host.rs::PathHost.path_subjects_of
    // frob:tests crates/grimble-lints/src/host.rs::UnityHost.unity_subjects_of
    // frob:tests crates/grimble-lints/src/host.rs::ErrHost.err_subjects_of
    // frob:tests crates/grimble-lints/src/pass.rs::PathFinding.into_finding
    assert_eq!(grimble_lints::rules::bind::<Fixed>().len(), 13);
    assert_eq!(
        grimble_lints::host::UnityHost::unity_subjects_of(&Fixed, "UNITY201"),
        11
    );
    assert_eq!(
        grimble_lints::host::PathHost::path_subjects_of(&Fixed, "PATH003"),
        7
    );
    assert_eq!(
        grimble_lints::host::ErrHost::err_subjects_of(&Fixed, "ERR001"),
        10
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

/// The findings of one rule for `text` as `path`.
fn of_rule(rule: &str, path: &str, text: &str) -> Vec<PathFinding> {
    run(path, text)
        .into_iter()
        .filter(|f| f.rule == rule)
        .collect()
}

#[test]
fn stored_naive_now_fires_and_displayed_one_stays_quiet() {
    // frob:tests crates/grimble-lints/src/time_pass.rs::analyze
    let stored = "import datetime\n\n\ndef f(r):\n    r.at = datetime.datetime.now()\n";
    let shown = "import datetime\n\n\ndef f():\n    n = datetime.datetime.now()\n    print(n)\n";
    assert_eq!(of_rule("TIME001", "a.py", stored).len(), 1);
    assert!(of_rule("TIME001", "a.py", shown).is_empty());
}

#[test]
fn naive_compared_with_aware_fires_time002() {
    // frob:tests crates/grimble-lints/src/time_pass.rs::analyze
    let src = "from datetime import datetime, timezone\n\n\ndef f():\n    a = datetime.now()\n    b = datetime.now(timezone.utc)\n    return a < b\n";
    let found = of_rule("TIME002", "a.py", src);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Warn);
}

#[test]
fn tz_kwarg_time_time_and_aliases_are_decided_correctly() {
    // frob:tests crates/grimble-lints/src/time_pass.rs::analyze
    let aware = "import datetime as d\nimport time\n\n\ndef f(r):\n    r.a = d.datetime.now(tz=d.timezone.utc)\n    r.b = time.time()\n    r.c = d.datetime.now(None)\n";
    let found = of_rule("TIME001", "a.py", aware);
    assert_eq!(found.len(), 1, "only now(None) is zone-less: {found:?}");
    let aliased = "from datetime import datetime as D\n\n\ndef f():\n    return D.utcnow()\n";
    assert_eq!(of_rule("TIME001", "a.py", aliased).len(), 1);
}

#[test]
fn rust_local_fires_utc_and_system_time_do_not() {
    // frob:tests crates/grimble-lints/src/time_pass.rs::analyze
    let src = "fn f() -> (i64, std::time::SystemTime, chrono::DateTime<chrono::Local>) {\n    let u = chrono::Utc::now().timestamp();\n    (u, std::time::SystemTime::now(), chrono::Local::now())\n}\n";
    let found = of_rule("TIME001", "a.rs", src);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].message.contains("local-zone"));
}

#[test]
fn time_without_roles_is_unresolved_and_empty_walk_is_not_applicable() {
    // frob:tests crates/grimble-lints/src/time_pass.rs::analyze
    let found = run("src/a.ts", "export const t = new Date();\n");
    let rules: Vec<_> = found
        .iter()
        .filter(|f| f.rule.starts_with("TIME"))
        .map(|f| f.rule)
        .collect();
    assert_eq!(rules, ["TIME001", "TIME002"], "{found:?}");
    let report = time_pass::analyze(&[]);
    let ids: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(ids, ["TIME001", "TIME002"]);
}
