//! Native coverage for every tested language: one provider trait, one registry, one shared lcov file.
//!
//! # The stable provider contract
//!
//! A language plugs in by implementing [`CoverageProvider`] on a unit struct in its own
//! module under `coverage/` and adding one entry to [`PROVIDERS`]. The provider says
//! *what to run* ([`CoverageProvider::plan`]: program, args, cwd, env, and where the raw
//! report lands) and *how to read it* ([`CoverageProvider::to_lcov`]: raw report to lcov
//! text). Everything else is shared and not the provider's business: finding the tool,
//! running it through the allowlisted [`gob_exec::Runner`], normalising paths to
//! repo-relative form, writing `.frob/coverage/<language>.info`, merging every language's
//! file into the `[coverage] report` lcov that COV004 reads, and the [`CoverageSummary`]
//! recorded on the evidence record.
//!
//! A missing tool is [`CoverageStatus::NotRun`], never a failure; a tool that ran but left
//! no usable report is [`CoverageStatus::MissingReport`], a COV004 finding when the
//! language has tests and `[coverage] require_reports` is true.

pub mod lcov;
pub mod rust;

use std::path::{Path, PathBuf};

use gob_exec::{Outcome, Program, Spec};
use gob_path::Shown;

use crate::config::CoverageConfig;
use crate::error::EvidenceError;
use crate::provider::plain_env;
use crate::record::{CoverageStatus, CoverageSummary, Provider, digest_hex};
use crate::workspace::Workspace;

use lcov::Lcov;

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// Why a provider could not plan or read a coverage run.
#[derive(Debug, thiserror::Error)]
pub enum CoverageError {
    /// The coverage tool is not installed (reported as not run).
    #[error("coverage tool `{0}` is not installed")]
    ToolMissing(String),
    /// The tool finished but wrote no report where the plan said it would.
    #[error("no coverage report at {0}")]
    NoReport(String),
    /// The report exists but could not be turned into lcov.
    #[error("coverage report is unparseable: {0}")]
    Unparseable(String),
    /// A filesystem failure around the report.
    #[error(transparent)]
    Io(#[from] EvidenceError),
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// One command to run with coverage and the raw report it leaves behind.
#[derive(Debug, Clone)]
pub struct CoveragePlan {
    /// What to spawn.
    pub program: Program,
    /// Its arguments.
    pub args: Vec<String>,
    /// Where to run it (usually the repository root).
    pub cwd: PathBuf,
    /// Extra environment, on top of the plain-text defaults.
    pub env: Vec<(String, String)>,
    /// Where the raw report lands (any format the provider's `to_lcov` reads).
    pub report: PathBuf,
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// What a language implements to take part in `--coverage` (the stable, documented contract).
pub trait CoverageProvider: Send + Sync {
    /// The test provider whose `--coverage` run this measures.
    fn provider(&self) -> Provider;
    /// The language name recorded on the summary and used for `.frob/coverage/<language>.info`.
    fn language(&self) -> &'static str;
    /// The executable the plan needs on `PATH`; absent means not run, never failed.
    fn required_tool(&self) -> &'static str;
    /// Whether the repository at `root` has tests in this language (so a report is owed).
    fn has_tests(&self, root: &Path) -> bool;
    /// The coverage command for `reference` (the test filter) and the raw report location under `out_dir`.
    ///
    /// # Errors
    ///
    /// A [`CoverageError`] when no plan can be made.
    fn plan(
        &self,
        ws: &Workspace,
        reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError>;
    /// Convert the raw report named by `plan` to lcov text (paths may be absolute; the shared normaliser fixes them).
    ///
    /// # Errors
    ///
    /// [`CoverageError::NoReport`] when the file is absent, [`CoverageError::Unparseable`] when it is unreadable.
    fn to_lcov(&self, ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError>;
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// Every registered language; each language ticket adds one entry here.
pub const PROVIDERS: &[&dyn CoverageProvider] = &[&rust::RustCoverage];

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// The registered coverage provider for test provider `provider`, if any.
pub fn registered(provider: Provider) -> Option<&'static dyn CoverageProvider> {
    PROVIDERS.iter().copied().find(|p| p.provider() == provider)
}

/// Directory (repo-relative) holding the per-language normalised lcov files.
pub const REPORT_DIR: &str = ".frob/coverage";

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// The per-language normalised lcov file under `root`.
pub fn language_report(root: &Path, language: &str) -> PathBuf {
    root.join(REPORT_DIR).join(format!("{language}.info"))
}

fn summary(language: &str, status: CoverageStatus, reason: Option<String>) -> CoverageSummary {
    CoverageSummary {
        language: language.to_owned(),
        status,
        reason,
        report: None,
        digest: None,
        lines_hit: 0,
        lines_found: 0,
        branches_hit: 0,
        branches_found: 0,
    }
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// Run the registered provider for `provider` with coverage; not run when none is registered.
pub fn run_coverage(ws: &Workspace, provider: Provider, reference: &str) -> CoverageSummary {
    if let Some(p) = registered(provider) {
        return run_provider(ws, p, reference);
    }
    tracing::info!(
        provider = provider.as_str(),
        "no coverage provider registered"
    );
    summary(
        provider.as_str(),
        CoverageStatus::NotRun,
        Some(format!(
            "no coverage provider is registered for {}",
            provider.as_str()
        )),
    )
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// Run `p` end to end: tool check, command, parse, per-language file, merged report. Never fails.
pub fn run_provider(ws: &Workspace, p: &dyn CoverageProvider, reference: &str) -> CoverageSummary {
    let language = p.language();
    if which::which(p.required_tool()).is_err() {
        tracing::info!(
            language,
            tool = p.required_tool(),
            "coverage tool missing; not run"
        );
        return summary(
            language,
            CoverageStatus::NotRun,
            Some(format!(
                "coverage tool `{}` is not installed",
                p.required_tool()
            )),
        );
    }
    let out_dir = ws.root.join(REPORT_DIR).join("raw").join(language);
    if let Err(e) = std::fs::create_dir_all(&out_dir) {
        tracing::warn!(language, error = %e, "cannot create the coverage output directory");
        return summary(language, CoverageStatus::NotRun, Some(e.to_string()));
    }
    let plan = match p.plan(ws, reference, &out_dir) {
        Ok(plan) => plan,
        Err(CoverageError::ToolMissing(tool)) => {
            return summary(
                language,
                CoverageStatus::NotRun,
                Some(format!("coverage tool `{tool}` is not installed")),
            );
        }
        Err(e) => {
            tracing::warn!(language, error = %e, "coverage plan failed");
            return summary(language, CoverageStatus::MissingReport, Some(e.to_string()));
        }
    };
    let mut env = plain_env();
    env.extend(plan.env.iter().cloned());
    let spec = Spec {
        program: plan.program.clone(),
        args: plan.args.clone(),
        cwd: Some(plan.cwd.clone()),
        env,
        timeout: ws.timeout(),
        capture: true,
    };
    match ws.runner().run(&spec) {
        Ok(out) => {
            tracing::info!(language, status = ?out.status, "coverage command finished");
            if matches!(out.status, Outcome::TimedOut) {
                return summary(
                    language,
                    CoverageStatus::MissingReport,
                    Some("coverage command timed out".to_owned()),
                );
            }
        }
        Err(e) => {
            tracing::info!(language, error = %e, "coverage command could not run");
            return summary(language, CoverageStatus::NotRun, Some(e.to_string()));
        }
    }
    finish(ws, p, &plan)
}

/// Parse the raw report, write the per-language file and merge all languages into the shared report.
fn finish(ws: &Workspace, p: &dyn CoverageProvider, plan: &CoveragePlan) -> CoverageSummary {
    let language = p.language();
    let text = match p.to_lcov(ws, plan) {
        Ok(text) => text,
        Err(e) => {
            tracing::warn!(language, error = %e, "coverage report missing or unreadable");
            return summary(language, CoverageStatus::MissingReport, Some(e.to_string()));
        }
    };
    let lcov = Lcov::parse(&text, &ws.root);
    let rendered = lcov.render();
    let own = language_report(&ws.root, language);
    if let Err(e) = write_file(&own, &rendered) {
        return summary(language, CoverageStatus::MissingReport, Some(e.to_string()));
    }
    let report = CoverageConfig::load(&ws.root).map_or_else(
        |e| {
            tracing::warn!(error = %e, "unreadable [coverage]; using the default report path");
            "lcov.info".to_owned()
        },
        |c| c.report,
    );
    if let Err(e) = merge_reports(&ws.root, &report) {
        return summary(language, CoverageStatus::MissingReport, Some(e.to_string()));
    }
    let totals = lcov.totals();
    tracing::info!(language, report = %report, files = lcov.files.len(), "coverage merged");
    CoverageSummary {
        report: Some(report),
        digest: Some(digest_hex(rendered.as_bytes())),
        lines_hit: totals.lines_hit,
        lines_found: totals.lines_found,
        branches_hit: totals.branches_hit,
        branches_found: totals.branches_found,
        ..summary(language, CoverageStatus::Measured, None)
    }
}

fn write_file(path: &Path, text: &str) -> Result<(), EvidenceError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| EvidenceError::io(dir, e))?;
    }
    std::fs::write(path, text).map_err(|e| EvidenceError::io(path, e))
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// Merge every `.frob/coverage/*.info` under `root` into `<root>/<report>` and return the merged report.
///
/// # Errors
///
/// [`EvidenceError`] when a file cannot be read or the merged file cannot be written.
pub fn merge_reports(root: &Path, report: &str) -> Result<Lcov, EvidenceError> {
    let dir = root.join(REPORT_DIR);
    let mut merged = Lcov::default();
    let mut names: Vec<PathBuf> = std::fs::read_dir(&dir)
        .map_err(|e| EvidenceError::io(&dir, e))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "info"))
        .collect();
    names.sort();
    for path in &names {
        let text = std::fs::read_to_string(path).map_err(|e| EvidenceError::io(path, e))?;
        merged.merge(&Lcov::parse(&text, root));
    }
    let target = root.join(report);
    write_file(&target, &merged.render())?;
    tracing::info!(target = %Shown::of(&target), inputs = names.len(), "merged coverage report written");
    Ok(merged)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn language_report_lives_under_the_coverage_dir() {
        let p = language_report(Path::new("/r"), "rust");
        assert!(p.ends_with(".frob/coverage/rust.info"));
    }

    // frob:tests merge_reports
    #[test]
    fn merge_reports_unions_languages_into_one_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::create_dir_all(root.join(REPORT_DIR)).unwrap();
        std::fs::write(
            language_report(root, "rust"),
            "SF:src/a.rs\nDA:1,1\nend_of_record\n",
        )
        .unwrap();
        std::fs::write(
            language_report(root, "python"),
            "SF:src/b.py\nDA:2,0\nend_of_record\n",
        )
        .unwrap();
        let merged = merge_reports(root, "lcov.info").unwrap();
        assert_eq!(merged.files.len(), 2);
        let text = std::fs::read_to_string(root.join("lcov.info")).unwrap();
        assert!(text.contains("SF:src/a.rs") && text.contains("SF:src/b.py"));
    }

    // frob:tests run_coverage
    #[test]
    fn unregistered_provider_is_not_run() {
        assert!(registered(Provider::Command).is_none());
    }
}
