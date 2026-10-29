//! The vitest and jest coverage providers: plans, test and runner detection, report reading and registration.

// frob:ticket 01M5XD3SSSJP0R696S51X6RRD6

use std::path::Path;

use frob_evidence::Workspace;
use frob_evidence::coverage::js::{JestCoverage, VitestCoverage};
use frob_evidence::coverage::{CoverageError, CoverageProvider, registered, run_coverage};
use frob_evidence::record::{CoverageStatus, Provider};
use gob_exec::Program;

fn workspace() -> (tempfile::TempDir, Workspace) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path().to_path_buf();
    gob_git::Repo::init(&p).expect("init");
    std::fs::write(p.join("frob.toml"), "").expect("toml");
    let ws = Workspace::open(&p, std::sync::Arc::new(gob_time::SystemClock)).expect("workspace");
    (dir, ws)
}

/// Install an empty file `rel` under `root` (parents created).
fn touch(root: &Path, rel: &str, body: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("dirs");
    std::fs::write(path, body).expect("write");
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.provider
// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.language
// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.required_tool
// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.provider
// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.language
// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.required_tool
#[test]
fn both_runners_are_registered_under_their_own_provider() {
    assert_eq!(VitestCoverage.provider(), Provider::Vitest);
    assert_eq!(JestCoverage.provider(), Provider::Jest);
    assert_eq!(VitestCoverage.language(), "javascript");
    assert_eq!(JestCoverage.language(), "javascript");
    assert_eq!(VitestCoverage.required_tool(), "node");
    assert_eq!(JestCoverage.required_tool(), "node");
    assert!(registered(Provider::Vitest).is_some());
    assert!(registered(Provider::Jest).is_some());
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.has_tests
// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.has_tests
#[test]
fn has_tests_needs_a_test_file_and_a_declared_runner() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    assert!(!VitestCoverage.has_tests(root));
    touch(root, "src/a.ts", "export const a = 1;\n");
    touch(root, "node_modules/dep/x.test.js", "");
    touch(root, "package.json", r#"{"devDependencies":{"jest":"1"}}"#);
    assert!(!JestCoverage.has_tests(root), "vendored tests do not count");
    touch(root, "src/a.test.ts", "test('a', () => {});\n");
    assert!(JestCoverage.has_tests(root));
    assert!(
        !VitestCoverage.has_tests(root),
        "jest is declared, not vitest"
    );
    touch(
        root,
        "package.json",
        r#"{"devDependencies":{"vitest":"1","jest":"1"}}"#,
    );
    assert!(VitestCoverage.has_tests(root));
    assert!(
        !JestCoverage.has_tests(root),
        "vitest claims a repo that lists both"
    );
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.has_tests
// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.has_tests
#[test]
fn a_tests_directory_and_a_config_file_count() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    touch(root, "jest.config.js", "module.exports = {};\n");
    touch(root, "src/__tests__/a.js", "");
    assert!(JestCoverage.has_tests(root));
    let other = tempfile::tempdir().expect("tempdir");
    touch(other.path(), "vitest.config.ts", "");
    touch(other.path(), "x.spec.mts", "");
    assert!(VitestCoverage.has_tests(other.path()));
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.plan
#[test]
fn vitest_plan_uses_the_installed_backend_and_the_project_runner() {
    let (_dir, ws) = workspace();
    let out = ws.root.join(".frob/coverage/raw/javascript");
    touch(&ws.root, "node_modules/.bin/vitest", "");
    let missing = VitestCoverage.plan(&ws, "src/a.test.ts", &out);
    assert!(
        matches!(missing, Err(CoverageError::ToolMissing(ref t)) if t.contains("coverage")),
        "no coverage package means not run: {missing:?}"
    );
    std::fs::create_dir_all(ws.root.join("node_modules/@vitest/coverage-istanbul")).expect("pkg");
    let plan = VitestCoverage
        .plan(&ws, "src/a.test.ts -t 'x y'", &out)
        .expect("plan");
    assert!(matches!(plan.program, Program::Hook { ref path } if path.ends_with("vitest")));
    assert_eq!(plan.args[0], "run");
    assert!(
        plan.args
            .contains(&"--coverage.provider=istanbul".to_owned())
    );
    assert!(plan.args.contains(&"--coverage.reporter=lcov".to_owned()));
    let dir = gob_path::exact_text(&out).expect("utf8");
    assert!(
        plan.args
            .contains(&format!("--coverage.reportsDirectory={dir}"))
    );
    assert_eq!(
        plan.args[plan.args.len() - 3..],
        ["src/a.test.ts", "-t", "x y"]
    );
    assert_eq!(plan.report, out.join("lcov.info"));
    std::fs::create_dir_all(ws.root.join("node_modules/@vitest/coverage-v8")).expect("pkg");
    let v8 = VitestCoverage.plan(&ws, "", &out).expect("plan");
    assert!(v8.args.contains(&"--coverage.provider=v8".to_owned()));
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.plan
// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.plan
#[test]
fn a_missing_runner_or_bad_arguments_fail_the_plan() {
    let (_dir, ws) = workspace();
    let out = ws.root.join("o");
    assert!(matches!(
        JestCoverage.plan(&ws, "", &out),
        Err(CoverageError::ToolMissing(ref t)) if t == "jest"
    ));
    touch(&ws.root, "node_modules/.bin/jest", "");
    assert!(matches!(
        JestCoverage.plan(&ws, "-t 'oops", &out),
        Err(CoverageError::Io(_))
    ));
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.plan
#[test]
fn jest_plan_enables_coverage_and_the_lcov_reporter() {
    let (_dir, ws) = workspace();
    let out = ws.root.join(".frob/coverage/raw/javascript");
    touch(&ws.root, "node_modules/.bin/jest", "");
    let plan = JestCoverage.plan(&ws, "src/a.test.ts", &out).expect("plan");
    assert_eq!(
        &plan.args[..3],
        ["--ci", "--coverage", "--coverageReporters=lcov"]
    );
    let dir = gob_path::exact_text(&out).expect("utf8");
    assert!(plan.args.contains(&format!("--coverageDirectory={dir}")));
    assert_eq!(plan.args.last().map(String::as_str), Some("src/a.test.ts"));
    assert!(
        plan.env
            .iter()
            .any(|(k, v)| k == "PATH" && v.contains("node_modules"))
    );
}

// frob:tests crates/frob-evidence/src/coverage/js.rs::VitestCoverage.to_lcov
// frob:tests crates/frob-evidence/src/coverage/js.rs::JestCoverage.to_lcov
#[test]
fn to_lcov_reports_absence_emptiness_and_drops_dependencies() {
    let (_dir, ws) = workspace();
    let out = ws.root.join("raw");
    touch(&ws.root, "node_modules/.bin/jest", "");
    let plan = JestCoverage.plan(&ws, "", &out).expect("plan");
    assert!(matches!(
        JestCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::NoReport(_))
    ));
    touch(&out, "lcov.info", "");
    assert!(matches!(
        VitestCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::Unparseable(_))
    ));
    let lcov = "SF:src/a.ts\nDA:1,1\nend_of_record\nSF:/r/node_modules/dep/i.js\nDA:1,0\nend_of_record\nSF:node_modules/x.js\nDA:1,0\nend_of_record\n";
    touch(&out, "lcov.info", lcov);
    let text = JestCoverage.to_lcov(&ws, &plan).expect("lcov");
    assert!(text.contains("SF:src/a.ts") && !text.contains("node_modules"));
    touch(
        &out,
        "lcov.info",
        "SF:node_modules/x.js\nDA:1,0\nend_of_record\n",
    );
    assert!(matches!(
        JestCoverage.to_lcov(&ws, &plan),
        Err(CoverageError::Unparseable(_))
    ));
}

// frob:tests run_coverage
#[test]
fn a_missing_runner_is_not_run_never_measured() {
    let (_dir, ws) = workspace();
    for provider in [Provider::Vitest, Provider::Jest] {
        let s = run_coverage(&ws, provider, "");
        assert_eq!(s.status, CoverageStatus::NotRun, "{s:?}");
        assert!(s.report.is_none());
        assert_eq!(s.lines_found, 0);
    }
}

#[cfg(unix)]
mod fake_runner {
    use std::os::unix::fs::PermissionsExt;

    use super::*;

    /// Install a shell script as `node_modules/.bin/<name>` that writes `lcov` to the directory named by `flag`.
    fn install(root: &Path, name: &str, flag: &str, lcov: &str) {
        let script = format!(
            "#!/bin/sh\nfor a in \"$@\"; do case \"$a\" in {flag}*) d=\"${{a#{flag}}}\";; esac; done\nmkdir -p \"$d\"\ncat > \"$d/lcov.info\" <<'EOF'\n{lcov}EOF\n"
        );
        touch(root, &format!("node_modules/.bin/{name}"), &script);
        let path = root.join("node_modules/.bin").join(name);
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    }

    // frob:tests run_coverage
    #[test]
    fn a_jest_run_is_normalised_merged_and_recorded() {
        if which::which("node").is_err() {
            return;
        }
        let (_dir, ws) = workspace();
        let abs = ws.root.join("src/a.ts");
        let lcov = format!(
            "SF:{}\nDA:1,1\nDA:2,0\nBRDA:1,0,0,1\nBRDA:1,0,1,0\nend_of_record\n",
            gob_path::exact_text(&abs).expect("utf8")
        );
        install(&ws.root, "jest", "--coverageDirectory=", &lcov);
        let s = run_coverage(&ws, Provider::Jest, "");
        assert_eq!(s.status, CoverageStatus::Measured, "{s:?}");
        assert_eq!((s.lines_hit, s.lines_found), (1, 2));
        assert_eq!((s.branches_hit, s.branches_found), (1, 2));
        let own = std::fs::read_to_string(ws.root.join(".frob/coverage/javascript.info"))
            .expect("per-language file");
        assert!(own.contains("SF:src/a.ts"), "{own}");
        let merged = std::fs::read_to_string(ws.root.join("lcov.info")).expect("merged");
        assert!(merged.contains("SF:src/a.ts"));
    }

    // frob:tests run_coverage
    #[test]
    fn a_vitest_run_without_a_report_is_a_missing_report() {
        if which::which("node").is_err() {
            return;
        }
        let (_dir, ws) = workspace();
        std::fs::create_dir_all(ws.root.join("node_modules/@vitest/coverage-v8")).expect("pkg");
        touch(&ws.root, "node_modules/.bin/vitest", "#!/bin/sh\nexit 0\n");
        let path = ws.root.join("node_modules/.bin/vitest");
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
        let s = run_coverage(&ws, Provider::Vitest, "");
        assert_eq!(s.status, CoverageStatus::MissingReport, "{s:?}");
    }
}
