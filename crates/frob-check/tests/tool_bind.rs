//! `[[check.tool]]` parser stages end to end, with a fake tool script in the temp dir.

use std::path::Path;

use frob_check::{CheckOptions, CheckReport, run};
use gob_diagnostics::ExitCode;
use gob_rules::Severity;

const ZIZMOR: &str = include_str!("../../gob-check/tests/fixtures/zizmor-json-v1.json");
const ACTIONLINT: &str = include_str!("../../gob-check/tests/fixtures/actionlint.json");

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: false,
        only: vec!["TOOL".to_owned(), "CI".to_owned(), "EXC".to_owned()],
        ..CheckOptions::default()
    }
}

/// A workflow-shaped file long enough for the fixture's byte offsets, with `head` first.
fn workflow(head: &str) -> String {
    format!(
        "{head}name: ci\n{}",
        "# padding line for offsets\n".repeat(30)
    )
}

/// A stage that runs `fake.sh` (which prints `fixture`, then exits `code`) as `sh fake.sh`.
fn stage(root: &Path, fixture: &str, code: i32, parser: &str, extra: &str) -> String {
    write(root, "fixture.json", fixture);
    write(root, "fake.sh", &format!("cat fixture.json\nexit {code}\n"));
    format!(
        "[[check.tool]]\nname = \"fake\"\ncommand = \"sh\"\nargs = [\"fake.sh\"]\nparser = \"{parser}\"\nversion_args = [\"-c\", \"echo faketool 1.2.3\"]\n{extra}\n"
    )
}

fn rules(report: &CheckReport) -> Vec<String> {
    report.findings.iter().map(|f| f.rule.to_string()).collect()
}

fn path_of(report: &CheckReport, i: usize) -> Option<String> {
    report.findings[i]
        .span
        .and_then(|s| report.files.path(s.file).map(str::to_owned))
}

#[test]
fn zizmor_findings_carry_ci_ids_and_real_spans() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), ".github/workflows/ci.yml", &workflow(""));
    write(dir.path(), ".github/dependabot.yml", &workflow(""));
    // Exit 1 with parseable output is how tools report findings; not a stage failure.
    let toml = stage(dir.path(), ZIZMOR, 1, "zizmor-json-v1", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    let mut got = rules(&report);
    got.sort();
    assert_eq!(got, ["CI001", "CI010", "TOOL002"]);
    let ci001 = report
        .findings
        .iter()
        .position(|f| f.rule.as_str() == "CI001")
        .expect("CI001");
    assert_eq!(
        path_of(&report, ci001).as_deref(),
        Some(".github/workflows/ci.yml")
    );
    assert_eq!(report.findings[ci001].severity, Severity::Warn);
    let span = report.findings[ci001].span.expect("span");
    assert_eq!(u32::from(span.range.start()), 305);
    assert_eq!(u32::from(span.range.end()), 324);
    assert!(
        report.findings[ci001]
            .message
            .starts_with("fake/unpinned-uses:")
    );
    let tool002 = report
        .findings
        .iter()
        .find(|f| f.rule.as_str() == "TOOL002")
        .expect("TOOL002");
    assert_eq!(tool002.severity, Severity::Advisory);
}

// frob:tests crates/gob-check/src/pipeline.rs::resolve_exceptions
#[test]
fn a_frob_accept_suppresses_a_tool_finding_like_a_native_one() {
    // The directive scanner reads Rust, Markdown and TOML comments (no YAML yet), so the
    // tool is pointed at a TOML file to exercise the exception path.
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "ci.toml",
        &workflow("# frob:accept CI001 because=\"actions are bumped by dependabot in one PR\"\n"),
    );
    let fixture = ZIZMOR.replace("./.github/workflows/ci.yml", "ci.toml");
    let toml = stage(dir.path(), &fixture, 0, "zizmor-json-v1", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert!(
        !rules(&report).contains(&"CI001".to_owned()),
        "{:?}",
        report.findings
    );
    assert!(
        report
            .suppressed
            .iter()
            .any(|(f, _)| f.rule.as_str() == "CI001"),
        "the accepted finding is listed as suppressed"
    );
    assert!(
        rules(&report).contains(&"CI010".to_owned()),
        "other rules still fire"
    );
}

#[test]
fn actionlint_findings_map_to_ci014_and_configured_labels_are_dropped() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        ".github/workflows/bad.yml",
        "on: push\njobs:\n  a:\n    runs-on: blacksmith-4\n    steps:\n      - run: echo ${{ foo }}\n      - uses: actions/checkout@v3\n",
    );
    let toml = stage(dir.path(), ACTIONLINT, 1, "actionlint-json", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(rules(&report), ["CI014", "CI014", "CI014"]);
    let advisory = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Advisory)
        .count();
    assert_eq!(advisory, 1, "runner-label is Advisory without labels");
    assert!(report.findings.iter().all(|f| f.span.is_some()));

    let toml = stage(
        dir.path(),
        ACTIONLINT,
        1,
        "actionlint-json",
        "labels = [\"blacksmith-4\"]",
    );
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(
        rules(&report),
        ["CI014", "CI014"],
        "the configured label is dropped"
    );
    assert!(report.findings.iter().all(|f| f.severity == Severity::Warn));
}

#[test]
fn a_tool_outside_its_version_range_yields_one_non_required_unresolved() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), ".github/workflows/ci.yml", &workflow(""));
    let toml = stage(
        dir.path(),
        ZIZMOR,
        0,
        "zizmor-json-v1",
        "min_version = \"2.0\"",
    );
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(rules(&report), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, Severity::Unresolved);
    assert!(report.findings[0].message.contains("schema lag"));
    assert!(report.findings[0].message.contains("1.2.3"));
    assert_eq!(
        report.required_unresolved(),
        0,
        "schema lag is not required"
    );
    assert_eq!(report.exit_code(), ExitCode::Ok);
}

#[test]
fn an_optional_missing_tool_is_unresolved_but_not_required() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "frob.toml",
        "[[check.tool]]\nname = \"ghost\"\ncommand = \"frob-no-such-binary\"\nparser = \"zizmor-json-v1\"\noptional = true\n",
    );
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(rules(&report), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, Severity::Unresolved);
    assert_eq!(report.required_unresolved(), 0);
    assert_eq!(report.exit_code(), ExitCode::Ok);

    write(
        dir.path(),
        "frob.toml",
        "[[check.tool]]\nname = \"ghost\"\ncommand = \"frob-no-such-binary\"\nparser = \"zizmor-json-v1\"\n",
    );
    let required = run(dir.path(), &options()).expect("run");
    assert_eq!(
        required.required_unresolved(),
        1,
        "a missing binary stays required"
    );
}

#[test]
fn unparseable_output_is_a_tool001_error() {
    let dir = tempfile::tempdir().expect("tempdir");
    let toml = stage(dir.path(), "not json", 0, "actionlint-json", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(rules(&report), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, Severity::Error);
}
