//! The `PM` evaluators: the pure cores and ledger readers behind the rules in [`crate::rules`], plus `[pm] strict`.

pub mod cycle;
pub mod membership;
pub mod milestone;
pub mod replenish;
pub mod wip;

use gob_rules::{Finding, RuleDecl, RuleId, Severity};

/// The [`RuleId`] a declared rule carries (its declaration is validated at compile time).
pub(crate) fn id_of<R: RuleDecl>() -> RuleId {
    R::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("declaration validates the id: {e}"))
}

// frob:ticket 01M41B2PD4NAV8VACA13750GWB
/// Every PM rule that `[pm] strict = true` escalates, with the severity it takes; the one table `apply_strict` consults.
pub const STRICT_SEVERITY: &[(&str, Severity)] = &[
    ("PM001", Severity::Error),
    ("PM002", Severity::Error),
    ("PM003", Severity::Error),
    ("PM004", Severity::Error),
    ("PM005", Severity::Error),
    ("PM006", Severity::Error),
    ("PM007", Severity::Error),
    ("PM008", Severity::Error),
    ("PM009", Severity::Error),
    ("PM013", Severity::Error),
    ("PM034", Severity::Error),
    ("PM036", Severity::Error),
];

// frob:ticket 01M41B2PD4NAV8VACA13750GWB
/// The severity `rule` takes under `[pm] strict = true`, or `None` when strict does not change it.
pub fn strict_severity(rule: &str) -> Option<Severity> {
    STRICT_SEVERITY
        .iter()
        .find(|(id, _)| *id == rule)
        .map(|(_, sev)| *sev)
}

// frob:ticket 01M41B2PD4NAV8VACA13750GWB
/// Escalate PM `findings` per [`strict_severity`] when `strict` is set; the single place the knob takes effect (a no-op when off).
pub fn apply_strict(strict: bool, mut findings: Vec<Finding>) -> Vec<Finding> {
    if !strict {
        return findings;
    }
    for f in &mut findings {
        if let Some(sev) = strict_severity(f.rule.as_str())
            && f.severity != sev
        {
            tracing::debug!(rule = %f.rule, from = ?f.severity, to = ?sev, "[pm] strict escalates severity");
            f.severity = sev;
        }
    }
    findings
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::RuleId;

    fn finding(rule: &str, sev: Severity) -> Finding {
        Finding::new(rule.parse::<RuleId>().unwrap(), sev, None, "m", "a")
    }

    // frob:tests apply_strict
    #[test]
    fn strict_escalates_listed_rules_only() {
        let fs = vec![
            finding("PM001", Severity::Error),
            finding("PM033", Severity::Error),
        ];
        let out = apply_strict(true, fs.clone());
        assert_eq!(out[0].severity, Severity::Error);
        assert_eq!(out[1].severity, Severity::Error);
        let off = apply_strict(false, fs);
        assert_eq!(off[0].severity, Severity::Error);
    }
}
