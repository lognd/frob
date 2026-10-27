//! Rust coverage: `cargo llvm-cov nextest` writing an lcov report for the nextest provider.

use std::path::Path;

use gob_exec::Program;

use super::{CoverageError, CoveragePlan, CoverageProvider};
use crate::provider::split_args;
use crate::record::Provider;
use crate::workspace::Workspace;

/// The Rust coverage provider (`cargo-llvm-cov` driving nextest).
#[derive(Debug, Clone, Copy, Default)]
pub struct RustCoverage;

/// Directories never searched for Rust tests.
const SKIPPED: &[&str] = &["target", ".git", ".frob", "node_modules"];

/// Whether any `.rs` file under `dir` declares a test.
fn any_rust_test(dir: &Path) -> bool {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return false;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name();
        if path.is_dir() {
            if !SKIPPED.iter().any(|s| name == *s) && any_rust_test(&path) {
                return true;
            }
        } else if path.extension().is_some_and(|x| x == "rs")
            && std::fs::read_to_string(&path)
                .is_ok_and(|t| t.contains("#[test]") || t.contains("#[cfg(test)]"))
        {
            return true;
        }
    }
    false
}

impl CoverageProvider for RustCoverage {
    /// Rust is measured under the nextest provider.
    fn provider(&self) -> Provider {
        Provider::Nextest
    }

    /// The language name `rust`.
    fn language(&self) -> &'static str {
        "rust"
    }

    /// `cargo-llvm-cov` must be on `PATH`; absent means not run.
    fn required_tool(&self) -> &'static str {
        "cargo-llvm-cov"
    }

    /// True when `root` has a `Cargo.toml` and some Rust file declares a test.
    fn has_tests(&self, root: &Path) -> bool {
        root.join("Cargo.toml").is_file() && any_rust_test(root)
    }

    /// `cargo llvm-cov nextest --lcov --output-path <out_dir>/lcov.info <filter args>`.
    fn plan(
        &self,
        ws: &Workspace,
        reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError> {
        let filter = split_args(reference).map_err(CoverageError::Io)?;
        let report = out_dir.join("lcov.info");
        let report_text = gob_path::exact_text(&report)
            .ok_or_else(|| CoverageError::Unparseable("report path is not unicode".to_owned()))?
            .to_owned();
        let mut args = vec!["llvm-cov".to_owned(), "nextest".to_owned()];
        if !ws.evidence.nextest_profile.is_empty() {
            args.push("--profile".to_owned());
            args.push(ws.evidence.nextest_profile.clone());
        }
        args.extend(["--lcov".to_owned(), "--output-path".to_owned(), report_text]);
        args.extend(filter);
        tracing::info!(?args, "planned rust coverage");
        Ok(CoveragePlan {
            program: Program::Cargo,
            args,
            cwd: ws.root.clone(),
            env: Vec::new(),
            report,
        })
    }

    /// The lcov file `cargo llvm-cov` wrote (already lcov; the shared normaliser fixes paths).
    fn to_lcov(&self, _ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError> {
        let text = std::fs::read_to_string(&plan.report)
            .map_err(|_| CoverageError::NoReport(gob_path::Shown::of(&plan.report).to_string()))?;
        if text.trim().is_empty() {
            return Err(CoverageError::Unparseable("empty lcov report".to_owned()));
        }
        Ok(text)
    }
}
