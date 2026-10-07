//! TypeScript tests: vitest and jest selection, runs through fake runners, and the missing-tool refusal (~RNQ92ZK).

use std::path::Path;

use frob_evidence::events;
use frob_evidence::record::Provider;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_tests::{
    Framework, RunOptions, TestTarget, TestsError, build_repo_graph, run, select_tests, touched_set,
};
use gob_git::Repo;

mod common;
use common::{git, write};

const PACKAGE: &str = include_str!("../../gob-symbols/tests/corpus/web/repo/package.json");
const CLIENT: &str = include_str!("../../gob-symbols/tests/corpus/web/repo/src/api/client.ts");
const CLIENT_TEST: &str =
    include_str!("../../gob-symbols/tests/corpus/web/repo/src/api/client.test.ts");
const SUM: &str = "export function sum(a: number, b: number): number {\n  return a + b;\n}\n";
const SUM_TEST: &str = "import { describe, test, expect } from \"@jest/globals\";\nimport { sum } from \"./sum\";\n\ndescribe(\"math\", () => {\n  test(\"adds\", () => {\n    expect(sum(1, 2)).toBe(3);\n  });\n});\n";
const VITEST_ID: &str = "src/api/client.test.ts::test$fetchUser_returns_the_id";
const JEST_ID: &str = "legacy/src/sum.test.ts::suite$math::test$adds";

/// The web conformance fixture plus a `legacy` member that uses jest, committed on `main`; returns the dir and base commit.
fn fixture() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    write(p, ".gitignore", "node_modules/\n");
    write(p, "package.json", PACKAGE);
    write(p, "src/api/client.ts", CLIENT);
    write(p, "src/api/client.test.ts", CLIENT_TEST);
    write(
        p,
        "legacy/package.json",
        "{\"name\":\"legacy\",\"devDependencies\":{\"jest\":\"^29.0.0\"}}\n",
    );
    write(p, "legacy/src/sum.ts", SUM);
    write(p, "legacy/src/sum.test.ts", SUM_TEST);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let base = git(p, &["rev-parse", "HEAD"]);
    (dir, base)
}

/// Touch both test files so every TypeScript test is selected.
fn touch_tests(root: &Path) {
    write(
        root,
        "src/api/client.test.ts",
        &format!("{CLIENT_TEST}// touched\n"),
    );
    write(
        root,
        "legacy/src/sum.test.ts",
        &format!("{SUM_TEST}// touched\n"),
    );
}

fn selected(dir: &Path, base: &str) -> Vec<TestTarget> {
    let repo = Repo::discover(dir).expect("repo");
    let graph = build_repo_graph(dir).expect("graph");
    let touched = touched_set(&repo, &graph, base).expect("touched");
    select_tests(dir, &graph, &touched)
}

fn cli() -> gob_cli::Cli {
    frob_tests::register(frob_evidence::register(gob_cli::Cli::new("frob", "0.0.0")))
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
#[test]
fn touched_typescript_tests_select_vitest_and_jest_targets_per_member() {
    // frob:tests crates/frob-tests/src/select.rs::select_tests
    let (dir, base) = fixture();
    touch_tests(dir.path());
    let got = selected(dir.path(), &base);
    let line = |f: Framework, member: &str, id: &str| TestTarget {
        framework: f,
        package: member.to_owned(),
        test_path: id.to_owned(),
        symref: String::new(),
    };
    let key = |t: &TestTarget| (t.framework, t.package.clone(), t.test_path.clone());
    let mut keys: Vec<_> = got.iter().map(key).collect();
    keys.sort();
    let want = [
        line(Framework::Vitest, "", VITEST_ID),
        line(Framework::Jest, "legacy", JEST_ID),
        line(
            Framework::Jest,
            "legacy",
            "legacy/src/sum.test.ts::suite$math",
        ),
    ];
    let mut want: Vec<_> = want.iter().map(key).collect();
    want.sort();
    assert_eq!(keys, want, "{got:?}");
    let (code, out, err) = gob_cli::run_for_test(
        &cli(),
        &["--text", "test", "--base", &base, "--dry-run"],
        dir.path(),
    );
    assert_eq!(code, 0, "{out}{err}");
    assert!(out.contains(&format!("- vitest {VITEST_ID}")), "{out}");
    assert!(out.contains(&format!("- jest {JEST_ID}")), "{out}");
    assert!(out.contains("ran: false"), "{out}");
}

#[cfg(unix)]
fn fake_runner(dir: &Path, rel: &str, flag: &str, name: &str, ancestors: &str, title: &str) {
    use std::os::unix::fs::PermissionsExt;
    let script = format!(
        "#!/bin/sh\nfor a in \"$@\"; do case \"$a\" in {flag}=*) out=\"${{a#{flag}=}}\";; esac; done\nprintf '{{\"testResults\":[{{\"name\":\"{name}\",\"status\":\"passed\",\"assertionResults\":[{{\"ancestorTitles\":{ancestors},\"title\":\"{title}\",\"status\":\"passed\"}}]}}]}}' > \"$out\"\necho \"fake runner $*\"\n"
    );
    write(dir, rel, &script);
    let path = dir.join(rel);
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
#[cfg(unix)]
#[test]
fn test_verb_runs_vitest_and_jest_per_member_and_appends_per_test_evidence() {
    // frob:tests crates/frob-tests/src/verb.rs::TestVerb
    if !gob_testsupport::node_test_prerequisites(
        "test_verb_runs_vitest_and_jest_per_member_and_appends_per_test_evidence",
        &["node"],
    ) {
        return;
    }
    let (dir, base) = fixture();
    let p = dir.path();
    let ledger = Ledger::open(
        Repo::discover(p).expect("repo"),
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut req = NewTicket::new("Speed up fetchUser", TicketType::Task);
    req.acceptance = vec!["fetchUser is fast".into()];
    let id = ledger.new_ticket(req).expect("ticket").ticket.front.id;
    let leases = p.join(".git/frob/leases");
    std::fs::create_dir_all(&leases).expect("leases dir");
    std::fs::write(
        leases.join("lease.toml"),
        format!(
            "ticket = \"{id}\"\n\n[holder]\nworktree = '{}'\n",
            p.display()
        ),
    )
    .expect("lease");
    fake_runner(
        p,
        "node_modules/.bin/vitest",
        "--outputFile.json",
        "src/api/client.test.ts",
        "[]",
        "fetchUser returns the id",
    );
    fake_runner(
        p,
        "legacy/node_modules/.bin/jest",
        "--outputFile",
        "src/sum.test.ts",
        "[\"math\"]",
        "adds",
    );
    touch_tests(p);

    let (code, out, err) = gob_cli::run_for_test(&cli(), &["--json", "test", "--base", &base], p);
    assert_eq!(code, 0, "{out}{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(v["data"]["passed"], true, "{out}");
    let executed: Vec<&str> = v["data"]["executed"]
        .as_array()
        .expect("executed")
        .iter()
        .filter_map(|n| n.as_str())
        .collect();
    assert_eq!(executed, [VITEST_ID, JEST_ID], "{out}");
    let stored = events::list(&ledger, id).expect("evidence");
    let providers: Vec<_> = stored.iter().map(|e| e.record.provider).collect();
    assert_eq!(providers, [Provider::Vitest, Provider::Jest]);
    assert_eq!(stored[0].record.tests, [VITEST_ID]);
    assert_eq!(stored[1].record.tests, [JEST_ID]);
    assert_eq!(stored[1].record.reference, "legacy/src/sum.test.ts");
    assert!(stored.iter().all(|e| e.record.passed == Some(true)));
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
#[test]
fn a_missing_node_refuses_the_run_with_a_named_reason_not_a_skip() {
    // frob:tests crates/frob-tests/src/run.rs::run
    let (dir, base) = fixture();
    touch_tests(dir.path());
    let sel = selected(dir.path(), &base);
    let mut opts = RunOptions::new(
        dir.path().to_path_buf(),
        std::time::Duration::from_secs(30),
        String::new(),
        vec!["vitest".to_owned(), "jest".to_owned()],
        false,
    );
    opts.node = "frob-no-such-node-xyz".to_owned();
    let runner = gob_exec::Runner::new(gob_exec::Limits { jobs: 1 });
    let err = run(&runner, &sel, &opts).expect_err("refused");
    assert!(
        matches!(&err, TestsError::Evidence(frob_evidence::EvidenceError::RunnerMissing { missing, .. }) if missing == "frob-no-such-node-xyz"),
        "{err}"
    );
    let cli_err = err.into_cli().to_string();
    assert!(cli_err.contains("E-EVIDENCE-RUNNER-MISSING"), "{cli_err}");

    opts.allowed_tools.clear();
    let err = run(&runner, &sel, &opts).expect_err("refused");
    assert!(err.to_string().contains("E-EVIDENCE-TOOL"), "{err}");
}

/// Both fake runners installed in the fixture, as the runners of `src/api/client.test.ts` and `legacy/src/sum.test.ts`.
#[cfg(unix)]
fn install_fake_runners(p: &Path) {
    fake_runner(
        p,
        "node_modules/.bin/vitest",
        "--outputFile.json",
        "src/api/client.test.ts",
        "[]",
        "fetchUser returns the id",
    );
    fake_runner(
        p,
        "legacy/node_modules/.bin/jest",
        "--outputFile",
        "src/sum.test.ts",
        "[\"math\"]",
        "adds",
    );
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
#[cfg(unix)]
#[test]
fn run_groups_selected_tests_by_member_and_maps_results_back_to_units() {
    // frob:tests crates/frob-tests/src/run.rs::run
    let (dir, base) = fixture();
    let p = dir.path();
    install_fake_runners(p);
    touch_tests(p);
    let sel = selected(p, &base);
    let mut opts = RunOptions::new(
        p.to_path_buf(),
        std::time::Duration::from_secs(30),
        String::new(),
        vec!["vitest".to_owned(), "jest".to_owned()],
        false,
    );
    // `sh` stands in for node: the fake runners are shell scripts.
    opts.node = "sh".to_owned();
    let groups = frob_tests::js_groups(&sel, &opts);
    assert_eq!(
        groups
            .iter()
            .map(|g| (g.framework, g.member.as_str(), g.files.clone()))
            .collect::<Vec<_>>(),
        [
            (
                Framework::Vitest,
                "",
                vec!["src/api/client.test.ts".to_owned()]
            ),
            (
                Framework::Jest,
                "legacy",
                vec!["src/sum.test.ts".to_owned()]
            ),
        ]
    );
    let runner = gob_exec::Runner::new(gob_exec::Limits { jobs: 1 });
    let report = run(&runner, &sel, &opts).expect("run");
    assert!(report.passed(), "{report:?}");
    assert_eq!(report.executed(), [VITEST_ID, JEST_ID]);
    let providers: Vec<_> = report
        .runs
        .iter()
        .map(frob_tests::FrameworkRun::provider)
        .collect();
    assert_eq!(providers, [Provider::Vitest, Provider::Jest]);
    assert_eq!(report.runs[0].reference(), "src/api/client.test.ts");
    assert_eq!(report.runs[1].reference(), "legacy/src/sum.test.ts");
    assert!(
        report.runs[0]
            .capture
            .transcript
            .contains("run --reporter=default --reporter=json")
    );
    assert!(report.runs[1].capture.transcript.contains("--ci --json"));

    // --all runs every member that declares its runner and holds a test file, whole; the root member only
    // imports vitest, so it is left out.
    opts.all = true;
    let whole = frob_tests::js_groups(&[], &opts);
    assert_eq!(
        whole
            .iter()
            .map(|g| (g.framework, g.member.as_str(), g.files.len()))
            .collect::<Vec<_>>(),
        [(Framework::Jest, "legacy", 0)]
    );
}
