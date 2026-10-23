//! `[[check.tool]]` parser stages end to end, with a fake tool script in the temp dir.

use std::path::Path;

use frob_check::{CheckOptions, CheckReport, run};
use gob_diagnostics::ExitCode;
use gob_rules::Severity;

const ZIZMOR: &str = include_str!("../../../gob-check/tests/fixtures/zizmor-json-v1.json");
const ACTIONLINT: &str = include_str!("../../../gob-check/tests/fixtures/actionlint.json");

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
    if !gob_exec::require_sh("zizmor_findings_carry_ci_ids_and_real_spans") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), ".github/workflows/ci.yml", &workflow(""));
    write(dir.path(), ".github/dependabot.yml", &workflow(""));
    // Exit 11 with parseable output is how zizmor reports findings; not a stage failure.
    let toml = stage(dir.path(), ZIZMOR, 11, "zizmor-json-v1", "");
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
    if !gob_exec::require_sh("a_frob_accept_suppresses_a_tool_finding_like_a_native_one") {
        return;
    }
    // The tool is pointed at a TOML file here; the YAML twin is below.
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

/// A workflow whose `first` key block covers zizmor fixture offsets 305..324 and whose
/// `second` key starts after them; `above_first` and `above_second` sit above each key.
fn keyed_workflow(above_first: &str, above_second: &str) -> String {
    let mut text = format!("{above_first}first:\n");
    while text.len() < 330 {
        text.push_str("  filler: value\n");
    }
    text.push_str(above_second);
    text.push_str("second:\n");
    while text.len() < 450 {
        text.push_str("  filler: value\n");
    }
    text
}

const ACCEPT_CI001: &str =
    "# frob:accept CI001 because=\"actions are bumped by dependabot in one PR\"\n";

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:tests crates/gob-check/src/pipeline.rs::resolve_exceptions
#[test]
fn a_yaml_accept_above_a_key_suppresses_the_finding_inside_that_key() {
    if !gob_exec::require_sh("a_yaml_accept_above_a_key_suppresses_the_finding_inside_that_key") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        ".github/workflows/ci.yml",
        &keyed_workflow(ACCEPT_CI001, ""),
    );
    write(dir.path(), ".github/dependabot.yml", &workflow(""));
    let toml = stage(dir.path(), ZIZMOR, 11, "zizmor-json-v1", "");
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
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:tests crates/gob-check/src/pipeline.rs::resolve_exceptions
#[test]
fn a_yaml_accept_above_another_key_does_not_suppress_the_finding() {
    if !gob_exec::require_sh("a_yaml_accept_above_another_key_does_not_suppress_the_finding") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        ".github/workflows/ci.yml",
        &keyed_workflow("", ACCEPT_CI001),
    );
    write(dir.path(), ".github/dependabot.yml", &workflow(""));
    let toml = stage(dir.path(), ZIZMOR, 11, "zizmor-json-v1", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert!(
        rules(&report).contains(&"CI001".to_owned()),
        "{:?}",
        report.findings
    );
    assert!(
        report
            .suppressed
            .iter()
            .all(|(f, _)| f.rule.as_str() != "CI001")
    );
}

/// A workflow of two `uses:` steps; the first covers zizmor fixture offsets 305..324.
fn stepped_workflow(above_first: &str, above_second: &str) -> String {
    let mut text = String::from("name: ci\njobs:\n  build:\n    steps:\n");
    text.push_str(above_first);
    text.push_str("      - uses: actions/checkout@v3\n");
    while text.len() < 330 {
        text.push_str("        with: value\n");
    }
    text.push_str(above_second);
    text.push_str("      - uses: actions/cache@v3\n");
    while text.len() < 450 {
        text.push_str("        with: value\n");
    }
    text
}

// frob:ticket 01M4MDH6NJXB6YK5NZFKC4NSBJ
// frob:tests crates/gob-check/src/pipeline.rs::resolve_exceptions
#[test]
fn a_step_accept_suppresses_only_that_steps_finding() {
    if !gob_exec::require_sh("a_step_accept_suppresses_only_that_steps_finding") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    let accept = "      # frob:accept CI001 because=\"pinned by dependabot\"\n";
    write(
        dir.path(),
        ".github/workflows/ci.yml",
        &stepped_workflow(accept, ""),
    );
    write(dir.path(), ".github/dependabot.yml", &workflow(""));
    let toml = stage(dir.path(), ZIZMOR, 11, "zizmor-json-v1", "");
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
            .any(|(f, _)| f.rule.as_str() == "CI001")
    );
}

// frob:ticket 01M4MDH6NJXB6YK5NZFKC4NSBJ
// frob:tests crates/gob-check/src/pipeline.rs::resolve_exceptions
#[test]
fn a_sibling_step_accept_does_not_suppress_the_finding() {
    if !gob_exec::require_sh("a_sibling_step_accept_does_not_suppress_the_finding") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    let accept = "      # frob:accept CI001 because=\"pinned by dependabot\"\n";
    write(
        dir.path(),
        ".github/workflows/ci.yml",
        &stepped_workflow("", accept),
    );
    write(dir.path(), ".github/dependabot.yml", &workflow(""));
    let toml = stage(dir.path(), ZIZMOR, 11, "zizmor-json-v1", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert!(
        rules(&report).contains(&"CI001".to_owned()),
        "{:?}",
        report.findings
    );
    assert!(
        report
            .suppressed
            .iter()
            .all(|(f, _)| f.rule.as_str() != "CI001")
    );
}

#[test]
fn actionlint_findings_map_to_ci014_and_configured_labels_are_dropped() {
    if !gob_exec::require_sh("actionlint_findings_map_to_ci014_and_configured_labels_are_dropped") {
        return;
    }
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
    if !gob_exec::require_sh("a_tool_outside_its_version_range_yields_one_non_required_unresolved")
    {
        return;
    }
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
        "[[check.tool]]\nname = \"ghost\"\ncommand = \"frob-no-such-binary\"\nargs = []\nparser = \"zizmor-json-v1\"\noptional = true\n",
    );
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(rules(&report), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, Severity::Unresolved);
    assert_eq!(report.required_unresolved(), 0);
    assert_eq!(report.exit_code(), ExitCode::Ok);

    write(
        dir.path(),
        "frob.toml",
        "[[check.tool]]\nname = \"ghost\"\ncommand = \"frob-no-such-binary\"\nargs = []\nparser = \"zizmor-json-v1\"\n",
    );
    let required = run(dir.path(), &options()).expect("run");
    assert_eq!(
        required.required_unresolved(),
        1,
        "a missing binary stays required"
    );
}

#[test]
fn unparseable_output_is_a_required_tool_failed() {
    if !gob_exec::require_sh("unparseable_output_is_a_required_tool_failed") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    let toml = stage(dir.path(), "not json", 0, "actionlint-json", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    assert_eq!(rules(&report), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, Severity::Unresolved);
    assert!(report.findings[0].required.is_some());
    assert_eq!(report.exit_code(), ExitCode::Negative);
}

/// One zizmor `excessive-permissions` finding is one `CI003` finding in `frob check`, with no native twin.
// frob:ticket 01M5F0A96X8KCH10HNHTXCDEKR
// frob:tests crates/gob-check/src/tool_parse.rs::classify
#[test]
fn a_zizmor_permissions_finding_is_reported_once_as_ci003() {
    if !gob_exec::require_sh("a_zizmor_permissions_finding_is_reported_once_as_ci003") {
        return;
    }
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), ".github/workflows/ci.yml", &workflow(""));
    let fixture = r#"[{"ident":"excessive-permissions","desc":"overly broad permissions","locations":[{"symbolic":{"key":{"Local":{"verbatim_path":"./.github/workflows/ci.yml"}},"annotation":"here","kind":"Primary"},"concrete":{"location":{"offset_span":{"start":10,"end":20}}}}]}]"#;
    let toml = stage(dir.path(), fixture, 11, "zizmor-json-v1", "");
    write(dir.path(), "frob.toml", &toml);
    let report = run(dir.path(), &options()).expect("run");
    let ci003 = report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "CI003")
        .count();
    assert_eq!(ci003, 1, "{:?}", report.findings);
    let only = CheckOptions {
        only: vec!["CI003".to_owned()],
        ..options()
    };
    let narrowed = run(dir.path(), &only).expect("--only CI003 is still a known rule");
    assert_eq!(rules(&narrowed), ["CI003"]);
}
