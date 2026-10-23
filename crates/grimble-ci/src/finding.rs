//! Construction of CI and DK verdicts; the type is the shared [`Verdict`] of grimble-verdict.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Severity, UnresolvedReason};
use grimble_verdict::Verdict;

/// A resolved finding of `rule` at `severity` in `file` over byte `range`.
pub(crate) fn fire(
    rule: &'static str,
    severity: Severity,
    site: (&str, (usize, usize)),
    message: String,
    anchor: String,
) -> Verdict {
    Verdict::fire(rule, severity, site, message, anchor)
}

/// An Unresolved finding of `rule` whose file could not be parsed.
pub(crate) fn parse_failed(rule: &'static str, file: &str, why: &str) -> Verdict {
    Verdict::unresolved(
        rule,
        UnresolvedReason::ParseFailed,
        (file, (0, 0)),
        format!("{rule} cannot judge {file}: {why}"),
        format!("{file}:parse-failed"),
    )
}
