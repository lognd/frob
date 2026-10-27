//! The Rust coverage provider: its plan, test detection, report reading and registration.

// frob:ticket 01M5XD3SGEGXC7MSTTQJRW4R9E

use std::path::Path;

use frob_evidence::Workspace;
use frob_evidence::coverage::rust::RustCoverage;
use frob_evidence::coverage::{CoverageError, CoverageProvider, registered, run_coverage};
use frob_evidence::record::{CoverageStatus, Provider};
use gob_exec::Program;

fn workspace() -> (tempfile::TempDir, Workspace) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path().to_path_buf();
    gob_git::Repo::init(&p).expect("init");
    std::fs::write(
        p.join("frob.toml"),
        "[evidence]\nnextest_profile = \"ci\"\n",
    )
    .expect("toml");
    let ws = Workspace::open(&p, std::sync::Arc::new(gob_time::SystemClock)).expect("workspace");
    (dir, ws)
}

// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.provider
// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.language
// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.required_tool
#[test]
fn rust_is_registered_under_nextest() {
    assert_eq!(RustCoverage.provider(), Provider::Nextest);
    assert_eq!(RustCoverage.language(), "rust");
    assert_eq!(RustCoverage.required_tool(), "cargo-llvm-cov");
    let p = registered(Provider::Nextest).expect("registered");
    assert_eq!(p.language(), "rust");
}

// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.has_tests
// frob:tests crates/frob-evidence/src/coverage/mod.rs::CoverageProvider.has_tests
#[test]
fn has_tests_needs_a_manifest_and_a_test() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    assert!(!RustCoverage.has_tests(root));
    std::fs::write(root.join("Cargo.toml"), "[package]\n").expect("manifest");
    std::fs::create_dir_all(root.join("src")).expect("src");
    std::fs::write(root.join("src/lib.rs"), "pub fn f() {}\n").expect("lib");
    assert!(!RustCoverage.has_tests(root));
    std::fs::write(
        root.join("src/lib.rs"),
        "#[cfg(test)]\nmod t { #[test] fn a() {} }\n",
    )
    .expect("lib");
    assert!(RustCoverage.has_tests(root));
}

// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.plan
#[test]
fn plan_runs_llvm_cov_nextest_with_the_filter_and_profile() {
    let (_dir, ws) = workspace();
    let out = ws.root.join(".frob/coverage/raw/rust");
    let plan = RustCoverage
        .plan(&ws, "-p demo -E 'test(/x y/)'", &out)
        .expect("plan");
    assert_eq!(plan.program, Program::Cargo);
    assert_eq!(&plan.args[..2], ["llvm-cov", "nextest"]);
    assert!(plan.args.windows(2).any(|w| w == ["--profile", "ci"]));
    assert!(plan.args.contains(&"--lcov".to_owned()));
    assert_eq!(
        plan.args[plan.args.len() - 4..],
        ["-p", "demo", "-E", "test(/x y/)"]
    );
    assert_eq!(plan.report, out.join("lcov.info"));
    assert!(
        plan.args
            .contains(&gob_path::exact_text(&plan.report).expect("utf8").to_owned())
    );
}

// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.plan
#[test]
fn plan_rejects_an_unterminated_filter() {
    let (_dir, ws) = workspace();
    let r = RustCoverage.plan(&ws, "-E 'oops", Path::new("/o"));
    assert!(matches!(r, Err(CoverageError::Io(_))));
}

// frob:tests crates/frob-evidence/src/coverage/rust.rs::RustCoverage.to_lcov
#[test]
fn to_lcov_reads_the_report_and_reports_absence() {
    let (_dir, ws) = workspace();
    let out = ws.root.join(".frob/coverage/raw/rust");
    std::fs::create_dir_all(&out).expect("out");
    let plan = RustCoverage.plan(&ws, "-p demo", &out).expect("plan");
    assert!(matches!(
        RustCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::NoReport(_))
    ));
    std::fs::write(&plan.report, "").expect("empty");
    assert!(matches!(
        RustCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::Unparseable(_))
    ));
    std::fs::write(&plan.report, "SF:src/a.rs\nDA:1,1\nend_of_record\n").expect("lcov");
    let text = RustCoverage.to_lcov(&ws, &plan).expect("lcov");
    assert!(text.contains("SF:src/a.rs"));
}

// frob:tests run_coverage
#[test]
fn a_missing_llvm_cov_is_not_run_never_measured() {
    let (_dir, ws) = workspace();
    let s = run_coverage(&ws, Provider::Nextest, "-p demo");
    if which::which("cargo-llvm-cov").is_err() {
        assert_eq!(s.status, CoverageStatus::NotRun, "{s:?}");
        assert!(s.report.is_none());
    } else {
        assert_ne!(s.status, CoverageStatus::NotRun, "{s:?}");
    }
}
