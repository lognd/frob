//! COV004: measured lcov coverage per scope against the `[coverage]` minimums.

// frob:ticket 01M4FD1NX760N78Z1T60MQ76H2

use std::collections::BTreeMap;
use std::path::Path;

use frob_evidence::coverage::lcov::{FileCov, Lcov};
use frob_evidence::coverage::{CoverageProvider, PROVIDERS, language_report};
use globset::{Glob, GlobSet, GlobSetBuilder};
use gob_rules::{Finding, RuleDecl as _, Severity};
use gob_text::{FileInterner, Span};

use crate::config::{CoverageConfig, CoverageThreshold};
use crate::rules::cov004::Cov004;
use crate::todo::range;
use crate::util::{def_id, finding_def};

/// The file the thresholds are written in, which findings point at.
const CONFIG_FILE: &str = "frob.toml";

/// The header of one threshold entry.
const ENTRY_HEADER: &str = "[[coverage.threshold]]";

/// Hit and found counts of a scope.
#[derive(Debug, Default, Clone, Copy)]
struct Tally {
    /// Items executed or taken.
    hit: usize,
    /// Items instrumented.
    found: usize,
}

impl Tally {
    /// The covered share in percent, `None` when nothing was instrumented.
    #[allow(clippy::cast_precision_loss, reason = "counts stay far below 2^52")]
    fn percent(self) -> Option<f64> {
        (self.found > 0).then(|| self.hit as f64 * 100.0 / self.found as f64)
    }
}

/// A matcher for `scope`: the glob itself, plus everything below it when it has no glob characters.
fn scope_matcher(scope: &str) -> Result<GlobSet, globset::Error> {
    let mut b = GlobSetBuilder::new();
    b.add(Glob::new(scope)?);
    if !scope.contains(['*', '?', '[', '{']) {
        let mut below = scope.trim_end_matches('/').to_owned();
        below.push('/');
        below.push_str("**");
        b.add(Glob::new(&below)?);
    }
    b.build()
}

/// Line and branch tallies of every reported file `matcher` accepts, with the file count.
fn tally(report: &BTreeMap<String, FileCov>, matcher: &GlobSet) -> (Tally, Tally, usize) {
    let (mut lines, mut branches, mut files) = (Tally::default(), Tally::default(), 0);
    for (path, cov) in report.iter().filter(|(p, _)| matcher.is_match(p.as_str())) {
        files += 1;
        lines.found += cov.lines.len();
        lines.hit += cov.lines.values().filter(|h| **h > 0).count();
        branches.found += cov.branches.len();
        branches.hit += cov.branches.values().filter(|t| **t).count();
        tracing::trace!(file = %path, "counted in scope");
    }
    (lines, branches, files)
}

/// The byte range of the `index`th threshold header in `<root>/frob.toml` (offset 0 when absent).
fn entry_span(root: &Path, index: usize, files: &mut FileInterner) -> Span {
    let (start, len) = std::fs::read_to_string(root.join(CONFIG_FILE))
        .ok()
        .and_then(|text| {
            let mut offset = 0;
            let mut seen = 0;
            for line in text.split_inclusive('\n') {
                if line.trim() == ENTRY_HEADER {
                    if seen == index {
                        return Some((offset, ENTRY_HEADER.len()));
                    }
                    seen += 1;
                }
                offset += line.len();
            }
            None
        })
        .unwrap_or((0, 0));
    Span::new(files.intern(CONFIG_FILE), range(start, len))
}

/// An unresolved COV004 finding for threshold `index`: nothing could be measured.
fn unresolved(
    root: &Path,
    index: usize,
    scope: &str,
    why: &str,
    files: &mut FileInterner,
) -> Finding {
    tracing::warn!(index, scope, why, "coverage threshold not measurable");
    Finding::new(
        def_id(Cov004::DEF),
        Severity::Unresolved,
        Some(entry_span(root, index, files)),
        format!("[coverage] scope `{scope}` could not be measured: {why}"),
        &format!("threshold[{index}]:{scope}"),
    )
}

/// Whether `pct` is a usable minimum.
fn valid_percent(pct: f64) -> bool {
    (0.0..=100.0).contains(&pct)
}

/// COV004 over the repo: every `[[coverage.threshold]]` entry against the lcov report.
pub(crate) fn cov004(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    cov004_with(root, files, PROVIDERS)
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// [`cov004`] over an explicit provider registry: report presence per language, then the thresholds.
pub(crate) fn cov004_with(
    root: &Path,
    files: &mut FileInterner,
    providers: &[&dyn CoverageProvider],
) -> Vec<Finding> {
    let config = match CoverageConfig::load(root) {
        Ok(c) => c,
        Err(err) => {
            tracing::warn!(%err, "[coverage] table unreadable");
            return vec![Finding::new(
                def_id(Cov004::DEF),
                Severity::Unresolved,
                Some(entry_span(root, 0, files)),
                format!("[coverage] table could not be read: {err}"),
                "coverage-config",
            )];
        }
    };
    let mut out = if config.require_reports {
        missing_reports(root, providers)
    } else {
        Vec::new()
    };
    if config.threshold.is_empty() {
        return out;
    }
    let report = std::fs::read_to_string(root.join(&config.report))
        .map(|t| Lcov::parse(&t, root).files)
        .map_err(|e| format!("report `{}` is unreadable ({e})", config.report));
    for (i, t) in config.threshold.iter().enumerate() {
        check_entry(root, i, t, &report, files, &mut out);
    }
    out
}

/// Evaluate threshold `t` (entry `index`) against `report`, pushing its findings onto `out`.
fn check_entry(
    root: &Path,
    index: usize,
    t: &CoverageThreshold,
    report: &Result<BTreeMap<String, FileCov>, String>,
    files: &mut FileInterner,
    out: &mut Vec<Finding>,
) {
    if t.line.is_none() && t.branch.is_none() {
        out.push(unresolved(
            root,
            index,
            &t.scope,
            "no `line` or `branch` minimum is set",
            files,
        ));
        return;
    }
    if let Some(bad) = [t.line, t.branch]
        .into_iter()
        .flatten()
        .find(|p| !valid_percent(*p))
    {
        let why = format!("minimum {bad} is not a percent between 0 and 100");
        out.push(unresolved(root, index, &t.scope, &why, files));
        return;
    }
    let matcher = match scope_matcher(&t.scope) {
        Ok(m) => m,
        Err(err) => {
            let why = format!("scope is not a valid glob ({err})");
            out.push(unresolved(root, index, &t.scope, &why, files));
            return;
        }
    };
    let report = match report {
        Ok(r) => r,
        Err(why) => {
            out.push(unresolved(root, index, &t.scope, why, files));
            return;
        }
    };
    let (by_line, by_branch, in_scope) = tally(report, &matcher);
    if in_scope == 0 {
        out.push(unresolved(
            root,
            index,
            &t.scope,
            "no file of the scope is in the report",
            files,
        ));
        return;
    }
    for (metric, required, tally) in [("line", t.line, by_line), ("branch", t.branch, by_branch)] {
        let Some(required) = required else { continue };
        let Some(measured) = tally.percent() else {
            let why = format!("the report holds no {metric} data for the scope");
            out.push(unresolved(root, index, &t.scope, &why, files));
            continue;
        };
        if measured < required {
            tracing::info!(scope = %t.scope, metric, measured, required, "coverage below threshold");
            out.push(finding_def(
                Cov004::DEF,
                Some(entry_span(root, index, files)),
                format!(
                    "scope `{}`: {metric} coverage {measured:.2}% ({}/{}) is below the required {required:.2}%",
                    t.scope, tally.hit, tally.found
                ),
                &format!("{}:{metric}", t.scope),
            ));
        } else {
            tracing::debug!(scope = %t.scope, metric, measured, required, "coverage meets threshold");
        }
    }
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// One finding per language that has tests but no coverage report: a missing tool is unresolved ("not run"), anything else an error.
fn missing_reports(root: &Path, providers: &[&dyn CoverageProvider]) -> Vec<Finding> {
    let mut out = Vec::new();
    for p in providers {
        let language = p.language();
        if !p.has_tests(root) || language_report(root, language).is_file() {
            continue;
        }
        let key = format!("coverage-report:{language}");
        if which::which(p.required_tool()).is_err() {
            tracing::info!(
                language,
                tool = p.required_tool(),
                "coverage not run: tool missing"
            );
            out.push(Finding::new(
                def_id(Cov004::DEF),
                Severity::Unresolved,
                None,
                format!(
                    "{language} coverage not run: `{}` is not installed",
                    p.required_tool()
                ),
                &key,
            ));
        } else {
            tracing::warn!(language, "language has tests but no coverage report");
            out.push(finding_def(
                Cov004::DEF,
                None,
                format!(
                    "{language} has tests but no coverage report; run `frob ticket evidence add --coverage` for its test provider"
                ),
                &key,
            ));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_evidence::Workspace;
    use frob_evidence::coverage::{CoverageError, CoveragePlan};
    use frob_evidence::record::Provider;

    /// A provider whose tests and tool are set by the test.
    struct Fake(&'static str, &'static str);

    impl CoverageProvider for Fake {
        fn provider(&self) -> Provider {
            Provider::Nextest
        }
        fn language(&self) -> &'static str {
            self.0
        }
        fn required_tool(&self) -> &'static str {
            self.1
        }
        fn has_tests(&self, _root: &Path) -> bool {
            true
        }
        fn plan(&self, _: &Workspace, _: &str, _: &Path) -> Result<CoveragePlan, CoverageError> {
            Err(CoverageError::ToolMissing(self.1.to_owned()))
        }
        fn to_lcov(&self, _: &Workspace, _: &CoveragePlan) -> Result<String, CoverageError> {
            Err(CoverageError::Unparseable(String::new()))
        }
    }

    fn run(root: &Path, providers: &[&dyn CoverageProvider]) -> Vec<Finding> {
        cov004_with(root, &mut FileInterner::default(), providers)
    }

    // frob:tests cov004_with
    #[test]
    fn a_tested_language_without_a_report_is_a_finding() {
        let dir = tempfile::tempdir().expect("tempdir");
        let found = run(dir.path(), &[&Fake("alpha", "sh")]);
        assert_eq!(found.len(), 1, "{found:?}");
        assert_eq!(found[0].severity, Severity::Error);
        assert!(
            found[0]
                .message
                .contains("alpha has tests but no coverage report")
        );
    }

    // frob:tests cov004_with
    #[test]
    fn a_missing_tool_is_not_run_not_a_failure() {
        let dir = tempfile::tempdir().expect("tempdir");
        let found = run(dir.path(), &[&Fake("beta", "frob-no-such-coverage-tool")]);
        assert_eq!(found.len(), 1, "{found:?}");
        assert_eq!(found[0].severity, Severity::Unresolved);
        assert!(found[0].message.contains("not run"));
    }

    // frob:tests cov004_with
    #[test]
    fn a_present_report_or_disabled_requirement_is_clean() {
        let dir = tempfile::tempdir().expect("tempdir");
        let report = language_report(dir.path(), "alpha");
        std::fs::create_dir_all(report.parent().expect("parent")).expect("mkdir");
        std::fs::write(&report, "").expect("write");
        assert!(run(dir.path(), &[&Fake("alpha", "sh")]).is_empty());
        std::fs::write(
            dir.path().join("frob.toml"),
            "[coverage]\nrequire_reports = false\n",
        )
        .expect("toml");
        let bare = tempfile::tempdir().expect("tempdir");
        std::fs::write(
            bare.path().join("frob.toml"),
            "[coverage]\nrequire_reports = false\n",
        )
        .expect("toml");
        assert!(run(bare.path(), &[&Fake("gamma", "sh")]).is_empty());
    }
}
