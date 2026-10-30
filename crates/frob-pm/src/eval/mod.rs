//! The `PM` evaluators: the pure cores and ledger readers behind the rules in [`crate::rules`], plus the deprecated `[pm] strict` no-op.

pub mod cycle;
pub mod membership;
pub mod milestone;
pub mod replenish;
pub mod wip;

use gob_rules::{Finding, RuleDecl, RuleId};

/// The [`RuleId`] a declared rule carries (its declaration is validated at compile time).
pub(crate) fn id_of<R: RuleDecl>() -> RuleId {
    R::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("declaration validates the id: {e}"))
}

// frob:ticket 01M5XMJJHNP9GEX18NSBZF44PC
/// Deprecated `[pm] strict` knob: a no-op that logs a WARN when set and returns `findings` untouched, because every PM rule is already an Error.
pub fn apply_strict(strict: bool, findings: Vec<Finding>) -> Vec<Finding> {
    if strict {
        tracing::warn!(
            "[pm] strict is deprecated and has no effect: every PM rule is an Error (rules.md 6.1.6); remove the knob"
        );
    }
    findings
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::{RuleId, Severity};

    fn finding(rule: &str, sev: Severity) -> Finding {
        Finding::new(rule.parse::<RuleId>().unwrap(), sev, None, "m", "a")
    }

    // frob:ticket 01M5XMJJHNP9GEX18NSBZF44PC
    // frob:tests apply_strict
    #[test]
    fn strict_is_a_deprecated_no_op() {
        let fs = vec![
            finding("PM001", Severity::Error),
            finding("PM033", Severity::Unresolved),
        ];
        for strict in [true, false] {
            let out = apply_strict(strict, fs.clone());
            assert_eq!(out[0].severity, Severity::Error);
            assert_eq!(out[1].severity, Severity::Unresolved);
            assert_eq!(out.len(), fs.len());
        }
    }
}
