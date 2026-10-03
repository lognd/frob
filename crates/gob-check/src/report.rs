//! The result of a check run: findings, timing, cache counters and the fix outcome.

use std::collections::BTreeMap;
use std::time::Duration;

use gob_diagnostics::{ExitCode, UnresolvedPolicy, fail_on};
use gob_rules::{Exception, Finding, Severity};
use gob_text::FileInterner;
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FailOn;
use crate::status::FidelityReport;

/// Wall time of one named pipeline stage.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct StageTime {
    /// Stage name (`walk`, `graph`, `file-rules`, `tool:ruff`, ...).
    pub name: String,
    /// Elapsed wall time in milliseconds (rounded down).
    pub ms: u64,
    /// True for the built-in stages that count against the `[perf]` budget.
    pub budgeted: bool,
}

/// Per-stage timing of one run; tool stages are listed apart from the budget.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Timing {
    /// Stages in execution order.
    pub stages: Vec<StageTime>,
}

impl Timing {
    /// Record a stage that took `took`; `budgeted` stages count against `[perf] budget_ms`.
    pub fn push(&mut self, name: impl Into<String>, took: Duration, budgeted: bool) {
        let ms = u64::try_from(took.as_millis()).unwrap_or(u64::MAX);
        let name = name.into();
        tracing::debug!(stage = %name, ms, budgeted, "stage finished");
        self.stages.push(StageTime { name, ms, budgeted });
    }

    /// Milliseconds spent in budgeted (built-in) stages.
    pub fn budget_ms(&self) -> u64 {
        self.stages
            .iter()
            .filter(|s| s.budgeted)
            .map(|s| s.ms)
            .sum()
    }

    /// Milliseconds spent in external tool stages (outside the budget).
    pub fn tools_ms(&self) -> u64 {
        self.stages
            .iter()
            .filter(|s| !s.budgeted)
            .map(|s| s.ms)
            .sum()
    }
}

/// Counters of one run.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Stats {
    /// Files walked (after excludes and the size cap).
    pub files: usize,
    /// Files the per-file rules were evaluated for (the whole walk, or the `--ticket` set).
    pub files_checked: usize,
    /// Per-file rule results served from the findings cache.
    pub file_hits: usize,
    /// Per-file rule results computed.
    pub file_misses: usize,
    /// Repo-rule results served from the cache.
    pub repo_hits: usize,
    /// Repo-rule results computed.
    pub repo_misses: usize,
    /// Files whose symbols came from the artifact cache.
    pub graph_cached: usize,
    /// Files whose symbols were extracted afresh.
    pub graph_extracted: usize,
}

impl Stats {
    /// All cache hits of the run (findings, repo rules, symbol artifacts).
    pub fn cached_hits(&self) -> usize {
        self.file_hits + self.repo_hits + self.graph_cached
    }
}

/// What one pass accumulates besides findings: timing, counters and subject counts.
#[derive(Debug, Default)]
pub(crate) struct Tally {
    /// Stage timing.
    pub timing: Timing,
    /// Counters.
    pub stats: Stats,
    /// Subjects examined per evaluated rule id.
    pub subjects: BTreeMap<String, usize>,
    /// Per-language fidelity accounting.
    pub fidelity: FidelityReport,
}

/// One Deterministic fix that was written to disk.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct AppliedFix {
    /// Rule whose finding the fix resolved.
    pub rule: String,
    /// Repo-relative file rewritten.
    pub file: String,
    /// The fix title.
    pub title: String,
}

/// What `--fix` did.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FixOutcome {
    /// Fixes applied, in file order.
    pub applied: Vec<AppliedFix>,
    /// Fixes skipped because their edits overlapped an earlier fix of the same file.
    pub skipped_overlap: usize,
    /// Findings left after the re-run (all severities).
    pub remaining: usize,
}

/// Findings per severity.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Counts {
    /// Error findings.
    pub error: usize,
    /// Warn findings.
    pub warn: usize,
    /// Advisory findings.
    pub advisory: usize,
    /// Unresolved findings.
    pub unresolved: usize,
}

impl Counts {
    /// Tally `findings` by severity.
    pub fn of(findings: &[Finding]) -> Self {
        let mut c = Self::default();
        for f in findings {
            match f.severity {
                Severity::Error => c.error += 1,
                Severity::Warn => c.warn += 1,
                Severity::Advisory => c.advisory += 1,
                Severity::Unresolved => c.unresolved += 1,
            }
        }
        c
    }
}

/// Everything one [`crate::run`] produced.
#[derive(Debug, Clone)]
pub struct CheckReport {
    /// Findings left standing, sorted by file, line, rule.
    pub findings: Vec<Finding>,
    /// Findings an exception suppressed, each with that exception.
    pub suppressed: Vec<(Finding, Exception)>,
    /// Resolves the file ids in the findings' spans.
    pub files: FileInterner,
    /// Stage timing, tool stages last.
    pub timing: Timing,
    /// Counters.
    pub stats: Stats,
    /// What `--fix` did; `None` when it was not requested.
    pub fix: Option<FixOutcome>,
    /// Non-fatal notes (an unresolvable base, a skipped stage).
    pub warnings: Vec<String>,
    /// The scope the run was limited to, as the product resolved it (frob: the ticket `~handle`).
    pub scope: Option<String>,
    /// The failing threshold in force (`[check] fail_on` or the override).
    pub fail_on: FailOn,
    /// The Unresolved gate in force (`[check] fail_on_unresolved`).
    pub fail_on_unresolved: UnresolvedPolicy,
    /// Subjects each evaluated rule examined (`rules.md` section 2); rules not evaluated are absent.
    pub subjects_examined: BTreeMap<String, usize>,
    /// Files examined, `NotApplicable` and Unresolved per language (every checked file appears).
    pub fidelity: FidelityReport,
}

impl CheckReport {
    /// `Negative` when a finding reaches `fail_on` or an Unresolved one fails `fail_on_unresolved`.
    pub fn exit_code(&self) -> ExitCode {
        fail_on(
            &self.findings,
            self.fail_on.threshold(),
            self.fail_on_unresolved,
        )
    }

    /// Unresolved findings that carry a required reason.
    pub fn required_unresolved(&self) -> usize {
        self.findings
            .iter()
            .filter(|f| f.severity == Severity::Unresolved && f.required.is_some())
            .count()
    }
}
