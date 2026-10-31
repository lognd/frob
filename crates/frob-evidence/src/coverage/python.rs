//! Python coverage: `pytest --cov` (coverage.py via pytest-cov) writing an lcov report for the pytest provider.

// frob:ticket 01M5XD3SNPVCTD68M0QB25EXKE

use std::path::Path;

use super::{CoverageError, CoveragePlan, CoverageProvider};
use crate::provider::{pytest_runner, split_args};
use crate::record::Provider;
use crate::workspace::Workspace;

/// The Python coverage provider (`coverage.py` driven through `pytest-cov`).
#[derive(Debug, Clone, Copy, Default)]
pub struct PythonCoverage;

/// Directories never searched for Python tests.
const SKIPPED: &[&str] = &[
    "target",
    ".git",
    ".frob",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
];

/// Whether `name` is a file pytest collects by default (`test_*.py` or `*_test.py`).
fn is_test_file(name: &str) -> bool {
    name.strip_suffix(".py")
        .is_some_and(|stem| stem.starts_with("test_") || stem.ends_with("_test"))
}

/// Whether any collectable Python test file lives under `dir`.
fn any_python_test(dir: &Path) -> bool {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return false;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name();
        if path.is_dir() {
            if !SKIPPED.iter().any(|s| name == *s) && any_python_test(&path) {
                return true;
            }
        } else if gob_path::exact_text(Path::new(&name)).is_some_and(is_test_file) {
            return true;
        }
    }
    false
}

impl CoverageProvider for PythonCoverage {
    /// Python is measured under the pytest provider.
    fn provider(&self) -> Provider {
        Provider::Pytest
    }

    /// The language name `python`.
    fn language(&self) -> &'static str {
        "python"
    }

    /// `coverage` (installed with pytest-cov) must be on `PATH`; absent means not run.
    fn required_tool(&self) -> &'static str {
        "coverage"
    }

    /// True when some collectable `test_*.py` or `*_test.py` file exists under `root`.
    fn has_tests(&self, root: &Path) -> bool {
        any_python_test(root)
    }

    /// `<pytest launcher> --cov --cov-report=lcov:<out_dir>/lcov.info <pytest args>`.
    fn plan(
        &self,
        ws: &Workspace,
        reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError> {
        let args = split_args(reference).map_err(CoverageError::Io)?;
        let report = out_dir.join("lcov.info");
        let report_text = gob_path::exact_text(&report)
            .ok_or_else(|| CoverageError::Unparseable("report path is not unicode".to_owned()))?
            .to_owned();
        let (program, mut full) = pytest_runner(&ws.root, &ws.tests.python).into_parts();
        full.extend([
            "--cov".to_owned(),
            format!("--cov-report=lcov:{report_text}"),
        ]);
        full.extend(args);
        tracing::info!(args = ?full, "planned python coverage");
        Ok(CoveragePlan {
            program,
            args: full,
            cwd: ws.root.clone(),
            env: Vec::new(),
            report,
        })
    }

    /// The lcov file pytest-cov wrote (already lcov; the shared normaliser fixes paths).
    fn to_lcov(&self, _ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError> {
        let text = std::fs::read_to_string(&plan.report)
            .map_err(|_| CoverageError::NoReport(gob_path::Shown::of(&plan.report).to_string()))?;
        if text.trim().is_empty() {
            return Err(CoverageError::Unparseable("empty lcov report".to_owned()));
        }
        Ok(text)
    }
}
