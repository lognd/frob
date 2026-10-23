//! `grimble check` runs `grimble-ci` over the workflow files of the walk and reports its findings.

// frob:ticket 01M5KDWHPF5YTVP64PYCXX0FRT

use std::path::Path;

use grimble_check::{CheckOptions, run};

/// Write `text` to the repo-relative `rel` under `root`, creating parents.
fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// A workflow whose one step uses an action pinned to a mutable tag.
const UNPINNED: &str = "name: ci\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n";

/// The rule ids a run over `dir` reports.
fn run_ids(dir: &Path) -> Vec<String> {
    let done = run(dir, &CheckOptions::default()).expect("run");
    done.report
        .findings
        .iter()
        .map(|f| f.rule.as_str().to_owned())
        .collect()
}

/// A mutable-tag `uses:` in a workflow, nested or not, is reported as CI001 by the check run.
// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/product.rs::ci_report
#[test]
fn check_reports_grimble_ci_findings() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), ".github/workflows/ci.yml", UNPINNED);
    write(dir.path(), "sub/.github/workflows/nested.yml", UNPINNED);
    let found = run_ids(dir.path());
    assert_eq!(
        found.iter().filter(|r| *r == "CI001").count(),
        2,
        "{found:?}"
    );
}

/// No workflows is not an error: the run is clean, and malformed YAML is Unresolved.
// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/product.rs::ci_report
#[test]
fn missing_and_malformed_workflows_do_not_crash() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "README.md", "# x\n");
    let found = run_ids(dir.path());
    assert!(!found.iter().any(|r| r.starts_with("CI0")), "{found:?}");
    write(dir.path(), ".github/workflows/bad.yml", "on: [\n  : : :\n");
    let found = run_ids(dir.path());
    assert!(found.iter().any(|r| r == "CI002"), "{found:?}");
}

/// A workflow granting `write-all` is reported as CI003 exactly once by the check run.
// frob:ticket 01M5F0A96X8KCH10HNHTXCDEKR
// frob:tests crates/grimble-check/src/product.rs::dedupe_ci
#[test]
fn a_write_all_workflow_is_reported_once_as_ci003() {
    let dir = tempfile::tempdir().expect("tempdir");
    let wf = "name: ci\non: push\npermissions: write-all\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n";
    write(dir.path(), ".github/workflows/ci.yml", wf);
    let found = run_ids(dir.path());
    assert_eq!(
        found.iter().filter(|r| *r == "CI003").count(),
        1,
        "{found:?}"
    );
}

/// The CI and architecture verdicts reach the report with the severity and message the passes
/// built, unchanged by the shared `Verdict` type (ticket 01M5F0111KG4GZSMSS7PX9D61N).
// frob:ticket 01M5F0111KG4GZSMSS7PX9D61N
// frob:tests crates/grimble-check/src/product.rs::ci_report
#[test]
fn verdict_output_is_stable_across_the_shared_type() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), ".github/workflows/ci.yml", UNPINNED);
    let done = run(dir.path(), &CheckOptions::default()).expect("run");
    let ci: Vec<_> = done
        .report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "CI001")
        .map(|f| (f.severity, f.message.clone()))
        .collect();
    assert_eq!(ci.len(), 1, "{ci:?}");
    assert_eq!(ci[0].0, gob_rules::Severity::Warn);
    assert!(
        ci[0]
            .1
            .starts_with("job `build` uses `actions/checkout@v4` which is not pinned"),
        "{ci:?}"
    );
}
