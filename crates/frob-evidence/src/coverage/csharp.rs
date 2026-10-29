//! C# coverage: `dotnet test` with the coverlet collector (`coverlet.collector`) writing lcov.

// frob:ticket 5GRB80B

use std::path::{Path, PathBuf};

use gob_exec::Program;

use super::{CoverageError, CoveragePlan, CoverageProvider};
use crate::provider::{DOTNET_PROGRAM, DotnetArgs, dotnet_filter, split_args, split_dotnet_args};
use crate::record::Provider;
use crate::workspace::Workspace;

/// The C# coverage provider (`dotnet test` with the coverlet collector).
#[derive(Debug, Clone, Copy, Default)]
pub struct CsharpCoverage;

/// The language name recorded for C#.
pub const LANGUAGE: &str = "csharp";

/// The file name coverlet writes its lcov report to (inside a per-run directory).
const REPORT_FILE: &str = "coverage.info";

/// Directories never searched for C# tests or projects.
const SKIPPED: &[&str] = &[
    "target",
    ".git",
    ".frob",
    "node_modules",
    "bin",
    "obj",
    "Library",
    "Temp",
];

/// Attributes that mark a method as a test in `xUnit`, `NUnit` and `MSTest`.
const TEST_ATTRIBUTES: &[&str] = &[
    "[Fact",
    "[Theory",
    "[Test]",
    "[Test(",
    "[TestCase",
    "[TestMethod",
    "[DataTestMethod",
];

/// Whether any `.cs` file under `dir` declares a test method.
fn any_csharp_test(dir: &Path) -> bool {
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
            if !SKIPPED.contains(&text) && any_csharp_test(&path) {
                return true;
            }
        } else if path.extension().is_some_and(|x| x == "cs")
            && std::fs::read_to_string(&path)
                .is_ok_and(|t| TEST_ATTRIBUTES.iter().any(|a| t.contains(a)))
        {
            return true;
        }
    }
    false
}

/// Whether any `.csproj` or `Directory.Packages.props`/`Directory.Build.props` under `dir` names `coverlet.collector`.
fn references_coverlet(dir: &Path) -> bool {
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
            if !SKIPPED.contains(&text) && references_coverlet(&path) {
                return true;
            }
        } else if path
            .extension()
            .is_some_and(|x| x.eq_ignore_ascii_case("csproj") || x.eq_ignore_ascii_case("props"))
            && std::fs::read_to_string(&path)
                .is_ok_and(|t| t.to_ascii_lowercase().contains("coverlet.collector"))
        {
            return true;
        }
    }
    false
}

/// The first `coverage.info` under `dir` (coverlet nests it in a per-run GUID directory).
fn find_report(dir: &Path) -> Option<PathBuf> {
    let mut found: Vec<PathBuf> = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        for entry in std::fs::read_dir(&d).ok()?.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.file_name().is_some_and(|n| n == REPORT_FILE) {
                found.push(path);
            }
        }
    }
    found.sort();
    found.into_iter().next()
}

/// `text` without the records whose `SF:` lies under a build output (`bin`/`obj`) directory.
fn drop_generated(text: &str) -> String {
    let mut out = String::new();
    let mut record = String::new();
    let mut skip = false;
    for line in text.lines() {
        if let Some(sf) = line.trim().strip_prefix("SF:") {
            let sf = sf.replace('\\', "/");
            skip = ["/obj/", "/bin/"].iter().any(|d| sf.contains(d));
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

impl CoverageProvider for CsharpCoverage {
    /// C# is measured under the dotnet provider.
    fn provider(&self) -> Provider {
        Provider::Dotnet
    }

    /// The language name `csharp`.
    fn language(&self) -> &'static str {
        LANGUAGE
    }

    /// `dotnet` must be on `PATH`; the coverlet collector is checked in `plan` (absent means not run).
    fn required_tool(&self) -> &'static str {
        DOTNET_PROGRAM
    }

    /// True when some `.cs` file declares an `xUnit`, `NUnit` or `MSTest` test.
    fn has_tests(&self, root: &Path) -> bool {
        any_csharp_test(root)
    }

    /// `dotnet test <projects> <flags> --collect:"XPlat Code Coverage" --results-directory <out_dir> [--filter ..] -- ...Format=lcov`.
    fn plan(
        &self,
        ws: &Workspace,
        reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError> {
        let args = split_args(reference).map_err(CoverageError::Io)?;
        let DotnetArgs {
            flags,
            projects,
            ids,
        } = split_dotnet_args(&args).map_err(CoverageError::Io)?;
        if !references_coverlet(&ws.root) {
            tracing::info!("no project references coverlet.collector; not run");
            return Err(CoverageError::ToolMissing("coverlet.collector".to_owned()));
        }
        let dir = gob_path::exact_text(out_dir)
            .ok_or_else(|| CoverageError::Unparseable("report path is not unicode".to_owned()))?
            .to_owned();
        let mut full = vec!["test".to_owned()];
        full.extend(projects);
        full.extend(flags);
        full.extend([
            "--nologo".to_owned(),
            "--collect:XPlat Code Coverage".to_owned(),
            "--results-directory".to_owned(),
            dir,
        ]);
        if !ids.is_empty() {
            full.extend(["--filter".to_owned(), dotnet_filter(&ids)]);
        }
        full.extend([
            "--".to_owned(),
            "DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=lcov"
                .to_owned(),
        ]);
        tracing::info!(args = ?full, "planned csharp coverage");
        Ok(CoveragePlan {
            program: Program::Tool {
                name: DOTNET_PROGRAM.to_owned(),
            },
            args: full,
            cwd: ws.root.clone(),
            env: Vec::new(),
            report: out_dir.join(REPORT_FILE),
        })
    }

    /// The `coverage.info` coverlet wrote under the results directory (build-output records dropped).
    fn to_lcov(&self, _ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError> {
        let dir = plan.report.parent().unwrap_or(&plan.cwd);
        let Some(path) = find_report(dir) else {
            return Err(CoverageError::NoReport(
                gob_path::Shown::of(&plan.report).to_string(),
            ));
        };
        let text = std::fs::read_to_string(&path)
            .map_err(|_| CoverageError::NoReport(gob_path::Shown::of(&path).to_string()))?;
        let kept = drop_generated(&text);
        if kept.trim().is_empty() {
            return Err(CoverageError::Unparseable(
                "empty lcov report (no instrumented source files)".to_owned(),
            ));
        }
        Ok(kept)
    }
}
