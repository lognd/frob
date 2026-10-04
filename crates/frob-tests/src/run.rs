//! Running the selected tests: `cargo nextest run -p <pkg> -E '<filter>'` and `pytest <node id>...` through gob-exec.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_evidence::provider::{Capture, run_nextest, run_pytest};
use frob_evidence::record::Provider;
use gob_exec::Runner;
use gob_walk::{WalkConfig, walk};

use crate::error::Result;
use crate::select::{Framework, TestTarget};

/// How to run: where, how long, and whether to run everything.
#[derive(Debug, Clone)]
pub struct RunOptions {
    /// The work tree root the runners run in.
    pub root: PathBuf,
    /// Wall-clock limit for one runner process.
    pub timeout: Duration,
    /// `--profile` for nextest; empty passes none.
    pub profile: String,
    /// `[evidence] allowed_tools`: pytest runs only when it is listed.
    pub allowed_tools: Vec<String>,
    /// Run the whole workspace instead of the selection.
    pub all: bool,
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// What one runner produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameworkRun {
    /// The runner.
    pub framework: Framework,
    /// The arguments that were used (after `cargo nextest run`, or after `pytest`).
    pub args: Vec<String>,
    /// Verdict, executed test names and the redacted transcript.
    pub capture: Capture,
}

impl FrameworkRun {
    /// The evidence provider that records this run.
    pub const fn provider(&self) -> Provider {
        match self.framework {
            Framework::Nextest => Provider::Nextest,
            Framework::Pytest => Provider::Pytest,
        }
    }
}

/// What a run produced: one entry per runner that ran.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RunReport {
    /// The runs, nextest first.
    pub runs: Vec<FrameworkRun>,
}

impl RunReport {
    /// True when every run passed (and at least one ran).
    pub fn passed(&self) -> bool {
        !self.runs.is_empty() && self.runs.iter().all(|r| r.capture.passed)
    }

    /// Executed test names of every run.
    pub fn executed(&self) -> Vec<String> {
        self.runs
            .iter()
            .flat_map(|r| r.capture.tests.iter().cloned())
            .collect()
    }

    /// Failed test names of every run.
    pub fn failed(&self) -> Vec<String> {
        self.runs
            .iter()
            .flat_map(|r| r.capture.failed_tests.iter().cloned())
            .collect()
    }

    /// The exit code of the first run that did not pass, else of the first run.
    pub fn exit_code(&self) -> Option<i32> {
        self.runs
            .iter()
            .find(|r| !r.capture.passed)
            .or_else(|| self.runs.first())
            .and_then(|r| r.capture.exit_code)
    }
}

/// The filter arguments for the nextest tests of `selected`: `-p` per package plus one `-E` filterset (none when it has no nextest test).
///
/// The filterset pairs each package with its own tests, so equal test names in
/// different packages do not drag each other in:
/// `(package(=a) & (test(=x) | test(=y))) | (package(=b) & test(=z))`.
pub fn nextest_args(selected: &[TestTarget]) -> Vec<String> {
    let mut by_pkg: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for t in selected
        .iter()
        .filter(|t| t.framework == Framework::Nextest)
    {
        by_pkg.entry(&t.package).or_default().push(&t.test_path);
    }
    if by_pkg.is_empty() {
        return Vec::new();
    }
    let mut args = Vec::new();
    for pkg in by_pkg.keys() {
        args.extend(["-p".to_owned(), (*pkg).to_owned()]);
    }
    let expr = by_pkg
        .iter()
        .map(|(pkg, tests)| {
            let any = tests
                .iter()
                .map(|t| format!("test(={t})"))
                .collect::<Vec<_>>()
                .join(" | ");
            format!("(package(={pkg}) & ({any}))")
        })
        .collect::<Vec<_>>()
        .join(" | ");
    args.extend(["-E".to_owned(), expr]);
    args
}

/// Quote `args` so [`frob_evidence::provider::split_args`] reads them back unchanged.
pub fn join_args(args: &[String]) -> String {
    args.iter()
        .map(|a| {
            if a.is_empty() || a.contains(char::is_whitespace) || a.contains(['\'', '"']) {
                format!("'{a}'")
            } else {
                a.clone()
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// The pytest arguments for `selected`: the node ids of its Python tests, in order.
pub fn pytest_args(selected: &[TestTarget]) -> Vec<String> {
    selected
        .iter()
        .filter(|t| t.framework == Framework::Pytest)
        .map(|t| t.test_path.clone())
        .collect()
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// True when the work tree at `root` holds a Python test file (so `--all` must run pytest).
fn has_python_tests(root: &Path) -> bool {
    match walk(root, &WalkConfig::default()) {
        Ok(walked) => walked
            .files
            .iter()
            .any(|f| gob_symbols::is_python_test_file(&f.path)),
        Err(e) => {
            tracing::warn!(error = %e, "could not walk for Python tests; pytest skipped under --all");
            false
        }
    }
}

/// Run `selected` (or the whole workspace with `opts.all`) with cargo nextest and pytest.
///
/// A runner runs only when it has selected tests (or, with `opts.all`, when the work
/// tree has tests for it); nextest runs first.
///
/// # Errors
///
/// [`crate::TestsError::Evidence`] when pytest is not allowlisted, [`crate::TestsError::Exec`] when a runner cannot be started.
pub fn run(runner: &Runner, selected: &[TestTarget], opts: &RunOptions) -> Result<RunReport> {
    let mut report = RunReport::default();
    let nextest = if opts.all {
        vec!["--workspace".to_owned()]
    } else {
        nextest_args(selected)
    };
    if !nextest.is_empty() {
        tracing::info!(all = opts.all, "running nextest");
        let capture = run_nextest(runner, &opts.root, &nextest, &opts.profile, opts.timeout)?;
        report.runs.push(FrameworkRun {
            framework: Framework::Nextest,
            args: nextest,
            capture,
        });
    }
    let pytest = pytest_args(selected);
    if !pytest.is_empty() || (opts.all && has_python_tests(&opts.root)) {
        tracing::info!(all = opts.all, tests = pytest.len(), "running pytest");
        let capture = run_pytest(
            runner,
            &opts.allowed_tools,
            &opts.root,
            &pytest,
            opts.timeout,
        )?;
        report.runs.push(FrameworkRun {
            framework: Framework::Pytest,
            args: pytest,
            capture,
        });
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn t(package: &str, test_path: &str) -> TestTarget {
        TestTarget {
            framework: Framework::Nextest,
            package: package.into(),
            test_path: test_path.into(),
            symref: String::new(),
        }
    }

    #[test]
    fn pytest_targets_stay_out_of_the_nextest_filter() {
        let py = TestTarget {
            framework: Framework::Pytest,
            package: String::new(),
            test_path: "tests/test_a.py::TestC::test_m".into(),
            symref: String::new(),
        };
        let sel = [t("a", "tests::x"), py];
        assert_eq!(pytest_args(&sel), ["tests/test_a.py::TestC::test_m"]);
        assert_eq!(nextest_args(&sel), nextest_args(&sel[..1]));
        assert_eq!(sel[1].plan_line(), "pytest tests/test_a.py::TestC::test_m");
        assert!(pytest_args(&sel[..1]).is_empty());
    }

    #[test]
    fn filters_pair_each_package_with_its_tests() {
        let args = nextest_args(&[t("a", "tests::x"), t("a", "tests::y"), t("b", "tests::x")]);
        assert_eq!(
            args,
            [
                "-p",
                "a",
                "-p",
                "b",
                "-E",
                "(package(=a) & (test(=tests::x) | test(=tests::y))) | (package(=b) & (test(=tests::x)))"
            ]
        );
        let joined = join_args(&args);
        assert_eq!(frob_evidence::provider::split_args(&joined).unwrap(), args);
    }

    // frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
    #[test]
    fn a_report_passes_only_when_every_runner_passed() {
        // frob:tests crates/frob-tests/src/run.rs::RunReport.passed
        let one = |framework, passed, code, test: &str| FrameworkRun {
            framework,
            args: Vec::new(),
            capture: Capture {
                exit_code: Some(code),
                passed,
                measured: true,
                tests: vec![test.to_owned()],
                failed_tests: if passed {
                    Vec::new()
                } else {
                    vec![test.to_owned()]
                },
                transcript: String::new(),
            },
        };
        let report = RunReport {
            runs: vec![
                one(Framework::Nextest, true, 0, "a"),
                one(Framework::Pytest, false, 1, "b"),
            ],
        };
        assert!(!report.passed());
        assert_eq!(report.executed(), ["a", "b"]);
        assert_eq!(report.failed(), ["b"]);
        assert_eq!(report.exit_code(), Some(1));
        assert_eq!(report.runs[1].provider(), Provider::Pytest);
        assert!(!RunReport::default().passed());
    }
}
