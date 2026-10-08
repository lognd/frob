//! The `dotnet` evidence provider end to end, against the `fake-dotnet` stand-in executable (no .NET SDK needed).

use std::path::Path;
use std::time::Duration;

use frob_evidence::provider::{dotnet_filter, parse_trx};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use gob_git::Repo;

/// A TRX with one passing NUnit-style test, one failing test (secret-shaped and non-ASCII message), one skipped, one parameterized pair.
const TRX: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<TestRun id="r" xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <Results>
    <UnitTestResult executionId="e1" testId="t1" testName="Adds" duration="00:00:00.0120000" outcome="Passed" />
    <UnitTestResult executionId="e2" testId="t2" testName="Breaks" duration="00:00:00.0340000" outcome="Failed">
      <Output>
        <StdOut>token AKIAIOSFODNN7EXAMPLE seen</StdOut>
        <ErrorInfo><Message>Expected caf&#233; &lt;3&gt; but was ghp_0123456789abcdefghijklmnopqrstuvwxyz</Message><StackTrace>at X</StackTrace></ErrorInfo>
      </Output>
    </UnitTestResult>
    <UnitTestResult executionId="e3" testId="t3" testName="Skipped" duration="00:00:00" outcome="NotExecuted" />
    <UnitTestResult executionId="e4" testId="t4" testName="Case(1)" duration="00:00:00.001" outcome="Passed" />
    <UnitTestResult executionId="e5" testId="t5" testName="Case(2)" duration="00:00:00.001" outcome="Passed" />
  </Results>
  <TestDefinitions>
    <UnitTest name="Adds" id="t1"><TestMethod codeBase="a.dll" className="Hb.Core.Tests.MathTests" name="Adds" /></UnitTest>
    <UnitTest name="Breaks" id="t2"><TestMethod codeBase="a.dll" className="Hb.Core.Tests.MathTests, Hb.Core.Tests, Version=1.0.0.0" name="Breaks" /></UnitTest>
    <UnitTest name="Skipped" id="t3"><TestMethod codeBase="a.dll" className="Hb.Core.Tests.MathTests" name="Skipped" /></UnitTest>
    <UnitTest name="Case(1)" id="t4"><TestMethod codeBase="a.dll" className="Hb.Core.Tests.Outer+Inner" name="Case" /></UnitTest>
    <UnitTest name="Case(2)" id="t5"><TestMethod codeBase="a.dll" className="Hb.Core.Tests.Outer+Inner" name="Case" /></UnitTest>
  </TestDefinitions>
</TestRun>
"#;

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("git");
    assert_eq!(
        out.status,
        ExecOutcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

/// A repository whose `frob.toml` points `[evidence.dotnet] path` at `dotnet` (the fake, or a missing path).
fn repo(dotnet: &Path, trx: Option<&str>, exit: Option<u8>) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    std::fs::write(
        p.join("frob.toml"),
        format!("[evidence.dotnet]\npath = '{}'\n", dotnet.display()),
    )
    .expect("frob.toml");
    if let Some(trx) = trx {
        std::fs::write(p.join("fake-dotnet.trx"), trx).expect("trx");
    }
    if let Some(code) = exit {
        std::fs::write(p.join("fake-dotnet.exit"), code.to_string()).expect("exit");
    }
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    dir
}

/// Run `evidence add --provider dotnet --ref <reference>` on a fresh ticket; returns (code, stdout, stderr, list count).
fn add_dotnet(dir: &Path, reference: &str) -> (i32, String, String, u64) {
    let ledger = Ledger::open(
        Repo::discover(dir).expect("repo"),
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut req = NewTicket::new("Do the thing", TicketType::Task);
    req.acceptance = vec!["first".into(), "second".into()];
    let handle = ledger.new_ticket(req).expect("new ticket").handle;
    drop(ledger);
    let cli = frob_evidence::register(gob_cli::Cli::new("frob", "0.0.0"));
    let run = |args: &[&str]| gob_cli::run_for_test(&cli, args, dir);
    let (code, out, err) = run(&[
        "--json",
        "ticket",
        "evidence",
        "add",
        &handle,
        "--provider",
        "dotnet",
        "--ref",
        reference,
        "--accepts",
        "1",
    ]);
    let (_, listed, _) = run(&["--json", "ticket", "evidence", "list", &handle]);
    let count =
        serde_json::from_str::<serde_json::Value>(&listed).expect("list json")["data"]["count"]
            .as_u64()
            .expect("count");
    (code, out, err, count)
}

fn json(out: &str) -> serde_json::Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("json {e}: {out}"))
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn trx_results_name_tests_by_their_definition_and_skip_unexecuted_ones() {
    // frob:tests crates/frob-evidence/src/provider.rs::parse_trx
    let trx = parse_trx(TRX);
    assert_eq!(
        trx.parsed.tests,
        [
            "Hb.Core.Tests.MathTests.Adds",
            "Hb.Core.Tests.MathTests.Breaks",
            "Hb.Core.Tests.Outer.Inner.Case"
        ]
    );
    assert_eq!(trx.parsed.failed, ["Hb.Core.Tests.MathTests.Breaks"]);
    assert!(trx.summary.contains("Passed Adds [00:00:00.0120000]"));
    assert!(trx.summary.contains("NotExecuted Skipped"));
    assert!(
        trx.summary
            .contains("message: Expected caf\u{e9} <3> but was")
    );
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn the_filter_matches_each_id_exactly_or_as_a_parameterized_method() {
    // frob:tests crates/frob-evidence/src/provider.rs::dotnet_filter
    let ids = ["A.B.M".to_owned(), "A.B.N".to_owned()];
    assert_eq!(
        dotnet_filter(&ids),
        "FullyQualifiedName=A.B.M|FullyQualifiedName~A.B.M\\(|FullyQualifiedName=A.B.N|FullyQualifiedName~A.B.N\\("
    );
    assert_eq!(
        dotnet_filter(&["A.M(1)".to_owned()]),
        "FullyQualifiedName=A.M\\(1\\)|FullyQualifiedName~A.M\\(1\\)\\("
    );
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn a_c_sharp_test_id_records_a_measured_run_with_per_test_results() {
    // frob:tests crates/frob-evidence/src/provider.rs::run_dotnet
    let dir = repo(&gob_testsupport::fake_dotnet(), Some(TRX), Some(1));
    let (code, out, err, count) = add_dotnet(
        dir.path(),
        "Hb.Core.Tests.MathTests.Adds Hb.Core.Tests.MathTests.Breaks",
    );
    assert_eq!(code, 0, "{out}{err}");
    assert_eq!(count, 1);
    let rec = &json(&out)["data"]["record"];
    assert_eq!(rec["provider"], "dotnet", "{out}");
    assert_eq!(rec["status"], "measured", "{out}");
    assert_eq!(rec["passed"], false, "{out}");
    assert_eq!(rec["exit_code"], 1, "{out}");
    assert_eq!(
        rec["tests"],
        serde_json::json!([
            "Hb.Core.Tests.MathTests.Adds",
            "Hb.Core.Tests.MathTests.Breaks",
            "Hb.Core.Tests.Outer.Inner.Case"
        ]),
        "{out}"
    );
    assert_eq!(
        rec["failed_tests"],
        serde_json::json!(["Hb.Core.Tests.MathTests.Breaks"]),
        "{out}"
    );
    let inline = rec["inline"].as_str().expect("inline transcript");
    assert!(
        inline.contains("--filter FullyQualifiedName=Hb.Core.Tests.MathTests.Adds|"),
        "{inline}"
    );
    assert!(inline.contains("--logger trx;LogFileName="), "{inline}");
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn a_failure_message_is_redacted_and_non_ascii_text_is_escaped() {
    // frob:tests crates/frob-evidence/src/provider.rs::run_dotnet
    let dir = repo(&gob_testsupport::fake_dotnet(), Some(TRX), Some(1));
    let (code, out, err, _) = add_dotnet(dir.path(), "Hb.Core.Tests.MathTests.Breaks");
    assert_eq!(code, 0, "{out}{err}");
    let inline = json(&out)["data"]["record"]["inline"]
        .as_str()
        .expect("inline")
        .to_owned();
    assert!(
        inline.contains("message: Expected caf\\u{e9} <3> but was [REDACTED]"),
        "{inline}"
    );
    assert!(inline.contains("stdout: token [REDACTED] seen"), "{inline}");
    assert!(!inline.contains("ghp_0123"), "{inline}");
    assert!(!inline.contains("AKIAIOSFODNN7EXAMPLE"), "{inline}");
    assert!(inline.is_ascii(), "{inline}");
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn a_missing_dotnet_sdk_refuses_with_a_remedy_and_records_nothing() {
    // frob:tests crates/frob-evidence/src/provider.rs::run_dotnet
    let dir = repo(Path::new("no-such-dotnet-binary"), Some(TRX), None);
    let (code, out, err, count) = add_dotnet(dir.path(), "Hb.Core.Tests.MathTests.Adds");
    assert_ne!(code, 0, "{out}{err}");
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-EVIDENCE-RUNNER-MISSING", "{out}");
    assert!(e["remedy"].as_str().expect("remedy").contains(".NET SDK"));
    assert_eq!(count, 0);
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn a_filter_that_runs_no_test_refuses_and_records_nothing() {
    // frob:tests crates/frob-evidence/src/provider.rs::dotnet_matched_no_tests
    let dir = repo(&gob_testsupport::fake_dotnet(), None, None);
    let (code, out, err, count) = add_dotnet(dir.path(), "Hb.Nothing.Here");
    assert_ne!(code, 0, "{out}{err}");
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-NO-TESTS", "{out}");
    assert_eq!(count, 0);
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
#[test]
fn an_option_like_reference_and_a_missing_allowlist_entry_are_refused() {
    // frob:tests crates/frob-evidence/src/provider.rs::run_dotnet
    let dir = repo(&gob_testsupport::fake_dotnet(), Some(TRX), None);
    let (code, out, err, count) = add_dotnet(dir.path(), "--no-build");
    assert_ne!(code, 0, "{out}{err}");
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-REF", "{out}");
    assert_eq!(count, 0);
    std::fs::write(
        dir.path().join("frob.toml"),
        "[evidence]\nallowed_tools = [\"cargo\"]\n",
    )
    .expect("frob.toml");
    let (code, out, err, count) = add_dotnet(dir.path(), "A.B.M");
    assert_ne!(code, 0, "{out}{err}");
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-TOOL", "{out}");
    assert_eq!(count, 0);
}
