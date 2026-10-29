//! JavaScript/TypeScript coverage: vitest (`@vitest/coverage-v8`/`-istanbul`) and jest (built-in istanbul) writing lcov.

// frob:ticket 01M5XD3SSSJP0R696S51X6RRD6

use std::path::{Path, PathBuf};

use gob_exec::Program;

use super::{CoverageError, CoveragePlan, CoverageProvider};
use crate::provider::{find_js_runner, js_bin_path, split_args};
use crate::record::Provider;
use crate::workspace::Workspace;

/// The vitest coverage provider (`vitest run --coverage`, v8 or istanbul).
#[derive(Debug, Clone, Copy, Default)]
pub struct VitestCoverage;

/// The jest coverage provider (`jest --coverage`, jest's bundled istanbul instrumentation).
#[derive(Debug, Clone, Copy, Default)]
pub struct JestCoverage;

/// The language name both runners record: `javascript` (covers TypeScript sources too).
pub const LANGUAGE: &str = "javascript";

/// Directories never searched for JavaScript tests.
const SKIPPED: &[&str] = &[
    "target",
    ".git",
    ".frob",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
];

/// Extensions of JavaScript and TypeScript sources.
const EXTENSIONS: &[&str] = &["js", "jsx", "mjs", "cjs", "ts", "tsx", "mts", "cts"];

/// Whether `name` is a test file by the vitest and jest default patterns (`*.test.*`, `*.spec.*`).
fn is_test_file(name: &str) -> bool {
    let parts: Vec<&str> = name.split('.').collect();
    let [.., kind, ext] = parts.as_slice() else {
        return false;
    };
    (*kind == "test" || *kind == "spec") && EXTENSIONS.contains(ext)
}

/// Whether `name` is a source file inside a `__tests__` directory.
fn is_source(name: &str) -> bool {
    name.rsplit_once('.')
        .is_some_and(|(stem, ext)| !stem.is_empty() && EXTENSIONS.contains(&ext))
}

/// Whether any JavaScript or TypeScript test file lives under `dir` (`in_tests` inside a `__tests__` directory).
fn any_js_test(dir: &Path, in_tests: bool) -> bool {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return false;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name();
        let Some(text) = gob_path::exact_text(Path::new(&name)) else {
            continue;
        };
        if path.is_dir() {
            if !SKIPPED.contains(&text) && any_js_test(&path, in_tests || text == "__tests__") {
                return true;
            }
        } else if is_test_file(text) || (in_tests && is_source(text)) {
            return true;
        }
    }
    false
}

/// Whether the repository root declares `runner`: its name appears in `package.json` or a `<runner>.config.*` file exists.
fn declares(root: &Path, runner: &str) -> bool {
    if std::fs::read_to_string(root.join("package.json")).is_ok_and(|t| t.contains(runner)) {
        return true;
    }
    let prefix = format!("{runner}.config.");
    std::fs::read_dir(root).is_ok_and(|rd| {
        rd.flatten().any(|e| {
            gob_path::exact_text(Path::new(&e.file_name())).is_some_and(|n| n.starts_with(&prefix))
        })
    })
}

/// The first `node_modules/<package>` directory from `cwd` up to `root`.
fn installed_package(root: &Path, cwd: &Path, package: &str) -> Option<PathBuf> {
    for dir in cwd.ancestors() {
        let hit = dir.join("node_modules").join(package);
        if hit.is_dir() {
            return Some(hit);
        }
        if dir == root {
            break;
        }
    }
    None
}

/// The report path of `out_dir` as text.
fn report_in(out_dir: &Path) -> Result<(PathBuf, String), CoverageError> {
    let report = out_dir.join("lcov.info");
    let text = gob_path::exact_text(out_dir)
        .ok_or_else(|| CoverageError::Unparseable("report path is not unicode".to_owned()))?
        .to_owned();
    Ok((report, text))
}

/// The runner binary and the `PATH` that leads with the project's `node_modules/.bin`.
fn launcher(
    ws: &Workspace,
    runner: &str,
) -> Result<(Program, Vec<(String, String)>), CoverageError> {
    let Some(path) = find_js_runner(&ws.root, &ws.root, runner) else {
        tracing::info!(runner, "coverage runner not found; not run");
        return Err(CoverageError::ToolMissing(runner.to_owned()));
    };
    let env = js_bin_path(&ws.root, &ws.root, std::env::var_os("PATH"))
        .map(|p| vec![("PATH".to_owned(), p)])
        .unwrap_or_default();
    Ok((Program::Hook { path }, env))
}

/// The lcov file a JavaScript runner wrote, with records for dependencies dropped.
fn read_lcov(plan: &CoveragePlan) -> Result<String, CoverageError> {
    let text = std::fs::read_to_string(&plan.report)
        .map_err(|_| CoverageError::NoReport(gob_path::Shown::of(&plan.report).to_string()))?;
    let kept = drop_dependencies(&text);
    if kept.trim().is_empty() {
        return Err(CoverageError::Unparseable(
            "empty lcov report (no instrumented source files)".to_owned(),
        ));
    }
    Ok(kept)
}

/// `text` without the records whose `SF:` lies under a `node_modules` directory.
fn drop_dependencies(text: &str) -> String {
    let mut out = String::new();
    let mut record = String::new();
    let mut skip = false;
    for line in text.lines() {
        if let Some(sf) = line.trim().strip_prefix("SF:") {
            skip =
                sf.replace('\\', "/").contains("/node_modules/") || sf.starts_with("node_modules/");
        }
        record.push_str(line);
        record.push('\n');
        if line.trim() == "end_of_record" {
            if !skip {
                out.push_str(&record);
            }
            record.clear();
            skip = false;
        }
    }
    out
}

impl CoverageProvider for VitestCoverage {
    /// Vitest is measured under the vitest provider.
    fn provider(&self) -> Provider {
        Provider::Vitest
    }

    /// The language name `javascript`.
    fn language(&self) -> &'static str {
        LANGUAGE
    }

    /// `node` must be on `PATH`; the vitest binary and coverage package are checked in `plan` (absent means not run).
    fn required_tool(&self) -> &'static str {
        crate::provider::NODE_PROGRAM
    }

    /// True when a JS/TS test file exists and the repository declares vitest.
    fn has_tests(&self, root: &Path) -> bool {
        declares(root, "vitest") && any_js_test(root, false)
    }

    /// `vitest run --coverage.enabled --coverage.provider=<v8|istanbul> --coverage.reporter=lcov --coverage.reportsDirectory=<out_dir> <args>`.
    fn plan(
        &self,
        ws: &Workspace,
        reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError> {
        let args = split_args(reference).map_err(CoverageError::Io)?;
        let (report, dir) = report_in(out_dir)?;
        let (program, env) = launcher(ws, "vitest")?;
        let backend = if installed_package(&ws.root, &ws.root, "@vitest/coverage-v8").is_some() {
            "v8"
        } else if installed_package(&ws.root, &ws.root, "@vitest/coverage-istanbul").is_some() {
            "istanbul"
        } else {
            tracing::info!("no @vitest/coverage-* package installed; not run");
            return Err(CoverageError::ToolMissing("@vitest/coverage-v8".to_owned()));
        };
        let mut full = vec![
            "run".to_owned(),
            "--coverage.enabled".to_owned(),
            format!("--coverage.provider={backend}"),
            "--coverage.reporter=lcov".to_owned(),
            format!("--coverage.reportsDirectory={dir}"),
        ];
        full.extend(args);
        tracing::info!(args = ?full, "planned vitest coverage");
        Ok(CoveragePlan {
            program,
            args: full,
            cwd: ws.root.clone(),
            env,
            report,
        })
    }

    /// The lcov file vitest wrote (dependency records dropped; the shared normaliser fixes paths).
    fn to_lcov(&self, _ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError> {
        read_lcov(plan)
    }
}

impl CoverageProvider for JestCoverage {
    /// Jest is measured under the jest provider.
    fn provider(&self) -> Provider {
        Provider::Jest
    }

    /// The language name `javascript`.
    fn language(&self) -> &'static str {
        LANGUAGE
    }

    /// `node` must be on `PATH`; the jest binary is checked in `plan` (absent means not run).
    fn required_tool(&self) -> &'static str {
        crate::provider::NODE_PROGRAM
    }

    /// True when a JS/TS test file exists, the repository declares jest, and vitest does not claim it.
    fn has_tests(&self, root: &Path) -> bool {
        declares(root, "jest") && !declares(root, "vitest") && any_js_test(root, false)
    }

    /// `jest --ci --coverage --coverageReporters=lcov --coverageDirectory=<out_dir> <args>`.
    fn plan(
        &self,
        ws: &Workspace,
        reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError> {
        let args = split_args(reference).map_err(CoverageError::Io)?;
        let (report, dir) = report_in(out_dir)?;
        let (program, env) = launcher(ws, "jest")?;
        let mut full = vec![
            "--ci".to_owned(),
            "--coverage".to_owned(),
            "--coverageReporters=lcov".to_owned(),
            format!("--coverageDirectory={dir}"),
        ];
        full.extend(args);
        tracing::info!(args = ?full, "planned jest coverage");
        Ok(CoveragePlan {
            program,
            args: full,
            cwd: ws.root.clone(),
            env,
            report,
        })
    }

    /// The lcov file jest wrote (dependency records dropped; the shared normaliser fixes paths).
    fn to_lcov(&self, _ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError> {
        read_lcov(plan)
    }
}
