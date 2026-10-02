//! Process exit codes and the `--fail-on` evaluator.

use gob_rules::{Finding, Severity};

use crate::required::UnresolvedPolicy;

/// The one exit-code table (cli.md section 2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ExitCode {
    /// The verb did what was asked.
    Ok = 0,
    /// Domain negative: the caller asked for a yes/no answer and it is no.
    Negative = 1,
    /// Usage error: bad flags or input failing its schema.
    Usage = 2,
    /// Refusal: a guard cleared by waiting or needing action.
    Refused = 3,
    /// Internal error (a bug).
    Internal = 4,
}

impl ExitCode {
    /// Numeric process exit status.
    pub const fn code(self) -> i32 {
        self as i32
    }
}

impl From<ExitCode> for i32 {
    fn from(code: ExitCode) -> Self {
        code.code()
    }
}

/// `Negative` when a finding reaches `threshold`, or an Unresolved one fails `policy`.
///
/// `threshold` gates Error, Warn and Advisory only (`None` disables it).
/// Unresolved fails under `All`, or under `Required` when the finding carries a
/// required reason; the result is never `Refused` (cli.md section 2).
pub fn fail_on(
    findings: &[Finding],
    threshold: Option<Severity>,
    policy: UnresolvedPolicy,
) -> ExitCode {
    let by_severity = |f: &&Finding| {
        f.severity != Severity::Unresolved && threshold.is_some_and(|t| f.severity >= t)
    };
    let by_policy = |f: &&Finding| {
        f.severity == Severity::Unresolved
            && match policy {
                UnresolvedPolicy::All => true,
                UnresolvedPolicy::Never => false,
                UnresolvedPolicy::Required => f.required.is_some(),
            }
    };
    let failing = findings.iter().filter(by_severity).count();
    let unresolved_failing = findings.iter().filter(by_policy).count();
    tracing::debug!(
        failing,
        unresolved_failing,
        ?threshold,
        policy = policy.name(),
        "fail_on evaluated"
    );
    if failing + unresolved_failing > 0 {
        ExitCode::Negative
    } else {
        ExitCode::Ok
    }
}
