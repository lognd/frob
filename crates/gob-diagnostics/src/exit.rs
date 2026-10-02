//! Process exit codes and the `--fail-on` evaluator.

use gob_rules::{Finding, Severity};

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

/// `Negative` only if a finding at or above `threshold` exists, else `Ok`.
///
/// `Unresolved` is the lowest severity and never fails on its own: a
/// threshold of `Unresolved` is treated as "no gate" for unresolved findings.
pub fn fail_on(findings: &[Finding], threshold: Severity) -> ExitCode {
    let failing = findings
        .iter()
        .filter(|f| f.severity != Severity::Unresolved && f.severity >= threshold)
        .count();
    tracing::debug!(failing, ?threshold, "fail_on evaluated");
    if failing > 0 {
        ExitCode::Negative
    } else {
        ExitCode::Ok
    }
}
