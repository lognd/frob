//! The C# coverage provider: plan, test and collector detection, report reading and registration.

// frob:ticket 01M5XD3SXWDQJE0YT8K5GRB80B

use std::path::Path;

use frob_evidence::Workspace;
use frob_evidence::coverage::csharp::CsharpCoverage;
use frob_evidence::coverage::lcov::Lcov;
use frob_evidence::coverage::{CoverageError, CoverageProvider, registered, run_coverage};
use frob_evidence::record::{CoverageStatus, Provider};

fn workspace() -> (tempfile::TempDir, Workspace) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path().to_path_buf();
    gob_git::Repo::init(&p).expect("init");
    std::fs::write(p.join("frob.toml"), "").expect("toml");
    let ws = Workspace::open(&p, std::sync::Arc::new(gob_time::SystemClock)).expect("workspace");
    (dir, ws)
}

/// Write `body` to `rel` under `root` (parents created).
fn touch(root: &Path, rel: &str, body: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("dirs");
    std::fs::write(path, body).expect("write");
}

// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.provider
// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.language
// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.required_tool
#[test]
fn csharp_is_registered_under_the_dotnet_provider() {
    assert_eq!(CsharpCoverage.provider(), Provider::Dotnet);
    assert_eq!(CsharpCoverage.language(), "csharp");
    assert_eq!(CsharpCoverage.required_tool(), "dotnet");
    assert!(registered(Provider::Dotnet).is_some());
}

// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.has_tests
#[test]
fn has_tests_needs_a_test_attribute_outside_build_output() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    assert!(!CsharpCoverage.has_tests(root));
    touch(root, "src/A.cs", "class A {}\n");
    touch(root, "obj/T.cs", "[Fact] void X() {}\n");
    assert!(!CsharpCoverage.has_tests(root));
    touch(
        root,
        "tests/ATests.cs",
        "public class T { [Fact] public void X() {} }\n",
    );
    assert!(CsharpCoverage.has_tests(root));
    let other = tempfile::tempdir().expect("tempdir");
    touch(other.path(), "T.cs", "[TestMethod] public void X() {}\n");
    assert!(CsharpCoverage.has_tests(other.path()));
}

// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.plan
#[test]
fn plan_collects_with_coverlet_as_lcov_and_filters_ids() {
    let (_dir, ws) = workspace();
    let out = ws.root.join(".frob/coverage/raw/csharp");
    touch(&ws.root, "T/T.csproj", "<Project/>");
    let missing = CsharpCoverage.plan(&ws, "", &out);
    assert!(
        matches!(missing, Err(CoverageError::ToolMissing(ref t)) if t == "coverlet.collector"),
        "{missing:?}"
    );
    touch(
        &ws.root,
        "T/T.csproj",
        r#"<PackageReference Include="coverlet.collector" Version="6" />"#,
    );
    let plan = CsharpCoverage
        .plan(&ws, "T/T.csproj --no-build N.C.M", &out)
        .expect("plan");
    assert_eq!(plan.args[..3], ["test", "T/T.csproj", "--no-build"]);
    assert!(
        plan.args
            .contains(&"--collect:XPlat Code Coverage".to_owned())
    );
    let dir = gob_path::exact_text(&out).expect("utf8");
    assert!(plan.args.contains(&dir.to_owned()));
    assert!(plan.args.contains(&"--filter".to_owned()));
    assert!(plan.args.last().expect("last").ends_with("Format=lcov"));
    assert!(matches!(
        CsharpCoverage.plan(&ws, "--logger x", &out),
        Err(CoverageError::Io(_))
    ));
}

// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.to_lcov
#[test]
fn to_lcov_finds_the_nested_report_and_drops_build_output() {
    let (_dir, ws) = workspace();
    let out = ws.root.join("raw");
    touch(&ws.root, "T.csproj", "coverlet.collector");
    let plan = CsharpCoverage.plan(&ws, "", &out).expect("plan");
    std::fs::create_dir_all(&out).expect("out");
    assert!(matches!(
        CsharpCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::NoReport(_))
    ));
    touch(
        &out,
        "guid/coverage.info",
        "SF:/r/obj/G.cs\nDA:1,0\nend_of_record\n",
    );
    assert!(matches!(
        CsharpCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::Unparseable(_))
    ));
    touch(
        &out,
        "guid/coverage.info",
        "SF:/r/src/A.cs\nDA:1,1\nend_of_record\nSF:/r/obj/G.cs\nDA:1,0\nend_of_record\n",
    );
    let text = CsharpCoverage.to_lcov(&ws, &plan).expect("lcov");
    assert!(text.contains("src/A.cs") && !text.contains("G.cs"));
}

// frob:tests run_coverage
#[test]
fn a_missing_dotnet_or_collector_is_not_run_never_measured() {
    let (_dir, ws) = workspace();
    let s = run_coverage(&ws, Provider::Dotnet, "");
    assert_eq!(s.status, CoverageStatus::NotRun, "{s:?}");
    assert!(s.report.is_none());
    assert_eq!(s.lines_found, 0);
}

// frob:tests crates/frob-evidence/src/coverage/csharp.rs::CsharpCoverage.to_lcov
#[test]
fn the_report_normalises_to_repo_relative_totals() {
    let (_dir, ws) = workspace();
    let out = ws.root.join("raw");
    touch(&ws.root, "T.csproj", "coverlet.collector");
    let plan = CsharpCoverage.plan(&ws, "", &out).expect("plan");
    let abs = gob_path::exact_text(&ws.root.join("src/A.cs"))
        .expect("utf8")
        .to_owned();
    touch(
        &out,
        "g/coverage.info",
        &format!("SF:{abs}\nDA:1,1\nDA:2,0\nend_of_record\n"),
    );
    let text = CsharpCoverage.to_lcov(&ws, &plan).expect("lcov");
    let lcov = Lcov::parse(&text, &ws.root);
    assert!(lcov.render().contains("SF:src/A.cs"), "{}", lcov.render());
    let t = lcov.totals();
    assert_eq!((t.lines_hit, t.lines_found), (1, 2));
}
