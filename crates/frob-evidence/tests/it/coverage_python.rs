//! The Python coverage provider: its plan, test detection, report reading and registration.

// frob:ticket 01M5XD3SNPVCTD68M0QB25EXKE

use std::path::Path;

use frob_evidence::Workspace;
use frob_evidence::coverage::python::PythonCoverage;
use frob_evidence::coverage::{CoverageError, CoverageProvider, registered, run_coverage};
use frob_evidence::record::{CoverageStatus, Provider};
use gob_exec::Program;

fn workspace(python: &str) -> (tempfile::TempDir, Workspace) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path().to_path_buf();
    gob_git::Repo::init(&p).expect("init");
    std::fs::write(
        p.join("frob.toml"),
        format!("[tests]\npython = \"{python}\"\n"),
    )
    .expect("toml");
    let ws = Workspace::open(&p, std::sync::Arc::new(gob_time::SystemClock)).expect("workspace");
    (dir, ws)
}

// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.provider
// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.language
// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.required_tool
#[test]
fn python_is_registered_under_pytest() {
    assert_eq!(PythonCoverage.provider(), Provider::Pytest);
    assert_eq!(PythonCoverage.language(), "python");
    assert_eq!(PythonCoverage.required_tool(), "coverage");
    let p = registered(Provider::Pytest).expect("registered");
    assert_eq!(p.language(), "python");
}

// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.has_tests
// frob:tests crates/frob-evidence/src/coverage/mod.rs::CoverageProvider.has_tests
#[test]
fn has_tests_needs_a_collectable_test_file() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    assert!(!PythonCoverage.has_tests(root));
    std::fs::create_dir_all(root.join("pkg")).expect("pkg");
    std::fs::write(root.join("pkg/mod.py"), "x = 1\n").expect("mod");
    assert!(!PythonCoverage.has_tests(root));
    std::fs::create_dir_all(root.join(".venv/lib")).expect("venv");
    std::fs::write(root.join(".venv/lib/test_vendored.py"), "").expect("vendored");
    assert!(!PythonCoverage.has_tests(root));
    std::fs::write(root.join("pkg/test_mod.py"), "def test_a(): pass\n").expect("test");
    assert!(PythonCoverage.has_tests(root));
}

// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.has_tests
#[test]
fn a_suffix_named_test_file_counts() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("mod_test.py"), "").expect("test");
    assert!(PythonCoverage.has_tests(dir.path()));
}

// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.plan
#[test]
fn plan_runs_pytest_with_cov_and_the_arguments() {
    let (_dir, ws) = workspace("python3");
    let out = ws.root.join(".frob/coverage/raw/python");
    let plan = PythonCoverage
        .plan(&ws, "tests/test_a.py -k 'x y'", &out)
        .expect("plan");
    assert!(matches!(plan.program, Program::Tool { ref name } if name == "python3"));
    assert_eq!(&plan.args[..2], ["-m", "pytest"]);
    assert!(plan.args.contains(&"--cov".to_owned()));
    let lcov = out.join("lcov.info");
    let report = gob_path::exact_text(&lcov).expect("utf8");
    assert!(plan.args.contains(&format!("--cov-report=lcov:{report}")));
    assert_eq!(
        plan.args[plan.args.len() - 3..],
        ["tests/test_a.py", "-k", "x y"]
    );
    assert_eq!(plan.report, out.join("lcov.info"));
}

// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.plan
#[test]
fn plan_rejects_an_unterminated_argument() {
    let (_dir, ws) = workspace("python3");
    let r = PythonCoverage.plan(&ws, "-k 'oops", Path::new("/o"));
    assert!(matches!(r, Err(CoverageError::Io(_))));
}

// frob:tests crates/frob-evidence/src/coverage/python.rs::PythonCoverage.to_lcov
#[test]
fn to_lcov_reads_the_report_and_reports_absence() {
    let (_dir, ws) = workspace("python3");
    let out = ws.root.join(".frob/coverage/raw/python");
    std::fs::create_dir_all(&out).expect("out");
    let plan = PythonCoverage.plan(&ws, "tests", &out).expect("plan");
    assert!(matches!(
        PythonCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::NoReport(_))
    ));
    std::fs::write(&plan.report, "").expect("empty");
    assert!(matches!(
        PythonCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::Unparseable(_))
    ));
    std::fs::write(&plan.report, "SF:pkg/a.py\nDA:1,1\nend_of_record\n").expect("lcov");
    let text = PythonCoverage.to_lcov(&ws, &plan).expect("lcov");
    assert!(text.contains("SF:pkg/a.py"));
}

// frob:tests run_coverage
#[test]
fn a_missing_coverage_tool_is_not_run_never_measured() {
    let (_dir, ws) = workspace("python3");
    let s = run_coverage(&ws, Provider::Pytest, "tests");
    if which::which("coverage").is_err() {
        assert_eq!(s.status, CoverageStatus::NotRun, "{s:?}");
        assert!(s.report.is_none());
        assert_eq!(s.lines_found, 0);
    } else {
        assert_ne!(s.status, CoverageStatus::NotRun, "{s:?}");
    }
}
