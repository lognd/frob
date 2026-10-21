//! Construction of verdicts; the type is the architecture pass's, shared instead of copied.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Severity, UnresolvedReason};

/// One CI or DK verdict before the product interns its span (the same shape as the architecture pass's).
pub type CiFinding = grimble_arch::ArchFinding;

/// A resolved finding of `rule` at `severity` in `file` over byte `range`.
pub(crate) fn fire(
    rule: &'static str,
    severity: Severity,
    site: (&str, (usize, usize)),
    message: String,
    anchor: String,
) -> CiFinding {
    CiFinding {
        rule,
        severity,
        file: site.0.to_owned(),
        range: site.1,
        message,
        reason: None,
        anchor,
    }
}

/// An Unresolved finding of `rule` whose file could not be parsed.
pub(crate) fn parse_failed(rule: &'static str, file: &str, why: &str) -> CiFinding {
    CiFinding {
        rule,
        severity: Severity::Unresolved,
        file: file.to_owned(),
        range: (0, 0),
        message: format!("{rule} cannot judge {file}: {why}"),
        reason: Some(UnresolvedReason::ParseFailed),
        anchor: format!("{file}:parse-failed"),
    }
}
