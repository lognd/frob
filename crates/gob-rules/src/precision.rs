//! The rule precision ledger: how often people accept, waive, dismiss or fix what a rule reports.
//!
//! A finding that is fixed was useful. A finding that is accepted (the rule does not apply here) or
//! dismissed was not. A waived (deferred) finding is real debt, so it counts as useful. The
//! not-useful rate is `(accepted + dismissed)` over every decided finding, as an integer percent so
//! the report stays exact and comparable. A rule with too few decided findings has no rate.

// frob:ticket 01M4D95B4W3XEMKKFG4B2ZBRER

use std::collections::BTreeMap;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::exception::{Exception, ExceptionKind};
use crate::finding::Finding;
use crate::id::RuleId;

/// Decided findings a rule needs before its not-useful rate is reported.
pub const MIN_DECIDED: u32 = 5;

/// What happened to the findings of one rule over a window.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct RuleTally {
    /// Findings suppressed by `accept`: the rule does not apply here.
    pub accepted: u32,
    /// Findings parked by `defer` or `hotfix`: real debt with an owner.
    pub waived: u32,
    /// Findings dismissed with a reason as not useful.
    pub dismissed: u32,
    /// Findings the author fixed.
    pub fixed: u32,
    /// Findings still standing.
    pub open: u32,
}

impl RuleTally {
    /// Findings someone decided on: everything but the open ones.
    pub fn decided(&self) -> u32 {
        self.accepted + self.waived + self.dismissed + self.fixed
    }

    /// Percent of decided findings that were not useful, or `None` below `min_decided`.
    pub fn not_useful_percent(&self, min_decided: u32) -> Option<u32> {
        let decided = self.decided();
        if decided == 0 || decided < min_decided {
            return None;
        }
        let bad = u64::from(self.accepted + self.dismissed);
        let pct = (bad * 100 + u64::from(decided) / 2) / u64::from(decided);
        u32::try_from(pct).ok()
    }
}

/// One rule's line of the ledger as reported by `check --json`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct PrecisionRow {
    /// The rule.
    pub rule: String,
    /// Its counts.
    #[serde(flatten)]
    pub tally: RuleTally,
    /// Percent not useful; absent below [`MIN_DECIDED`] decided findings.
    pub not_useful_percent: Option<u32>,
}

/// A rule whose not-useful rate is over the ceiling, with the numbers behind the advice.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Demotion {
    /// The rule to demote one severity step.
    pub rule: RuleId,
    /// Its counts.
    pub tally: RuleTally,
    /// Its not-useful percent.
    pub not_useful_percent: u32,
    /// The ceiling it exceeded.
    pub ceiling_percent: u32,
}

impl std::fmt::Display for Demotion {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}: demote; {}% not useful (ceiling {}%) over {} decided: {} accepted, {} dismissed, {} waived, {} fixed",
            self.rule,
            self.not_useful_percent,
            self.ceiling_percent,
            self.tally.decided(),
            self.tally.accepted,
            self.tally.dismissed,
            self.tally.waived,
            self.tally.fixed,
        )
    }
}

/// Per-rule tallies of one window.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct PrecisionLedger {
    rules: BTreeMap<RuleId, RuleTally>,
}

impl PrecisionLedger {
    /// An empty ledger.
    pub fn new() -> Self {
        Self::default()
    }

    /// The ledger of one run: `suppressed` findings by the kind of exception, `open` ones as standing.
    pub fn of_run(open: &[Finding], suppressed: &[(Finding, Exception)]) -> Self {
        let mut ledger = Self::new();
        for f in open {
            ledger.entry(&f.rule).open += 1;
        }
        for (f, ex) in suppressed {
            let t = ledger.entry(&f.rule);
            match ex.kind {
                ExceptionKind::Accept | ExceptionKind::Baseline => t.accepted += 1,
                ExceptionKind::Defer | ExceptionKind::Hotfix => t.waived += 1,
            }
        }
        tracing::debug!(rules = ledger.rules.len(), "precision ledger built");
        ledger
    }

    /// Count `n` fixed findings of `rule`.
    pub fn add_fixed(&mut self, rule: &RuleId, n: u32) {
        self.entry(rule).fixed += n;
    }

    /// Count `n` dismissed findings of `rule`.
    pub fn add_dismissed(&mut self, rule: &RuleId, n: u32) {
        self.entry(rule).dismissed += n;
    }

    fn entry(&mut self, rule: &RuleId) -> &mut RuleTally {
        self.rules.entry(rule.clone()).or_default()
    }

    /// The tally of `rule`, empty when it has none.
    pub fn tally(&self, rule: &RuleId) -> RuleTally {
        self.rules.get(rule).copied().unwrap_or_default()
    }

    /// One row per rule with any count, in rule order.
    pub fn rows(&self) -> Vec<PrecisionRow> {
        self.rules
            .iter()
            .map(|(rule, tally)| PrecisionRow {
                rule: rule.to_string(),
                tally: *tally,
                not_useful_percent: tally.not_useful_percent(MIN_DECIDED),
            })
            .collect()
    }

    /// Rules whose not-useful percent is above `ceiling_percent`, worst first.
    pub fn demotions(&self, ceiling_percent: u32) -> Vec<Demotion> {
        let mut out: Vec<Demotion> = self
            .rules
            .iter()
            .filter_map(|(rule, tally)| {
                let pct = tally.not_useful_percent(MIN_DECIDED)?;
                (pct > ceiling_percent).then(|| Demotion {
                    rule: rule.clone(),
                    tally: *tally,
                    not_useful_percent: pct,
                    ceiling_percent,
                })
            })
            .collect();
        out.sort_by_key(|d| std::cmp::Reverse(d.not_useful_percent));
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::meta::Severity;

    fn id(s: &str) -> RuleId {
        s.parse().unwrap()
    }

    fn finding(rule: &str) -> Finding {
        Finding::new(id(rule), Severity::Error, None, "m", "a.rs")
    }

    fn exception(kind: ExceptionKind, rule: &str) -> Exception {
        Exception {
            kind,
            rule: id(rule),
            reason: "a reason long enough".into(),
            ticket: None,
            until: None,
        }
    }

    // frob:tests crates/gob-rules/src/precision.rs::PrecisionLedger.of_run
    #[test]
    fn a_run_counts_accepts_waives_and_open_findings_per_rule() {
        let suppressed = vec![
            (
                finding("COV001"),
                exception(ExceptionKind::Accept, "COV001"),
            ),
            (
                finding("COV001"),
                exception(ExceptionKind::Accept, "COV001"),
            ),
            (finding("COV001"), exception(ExceptionKind::Defer, "COV001")),
            (
                finding("DOC001"),
                exception(ExceptionKind::Hotfix, "DOC001"),
            ),
        ];
        let ledger = PrecisionLedger::of_run(&[finding("COV001")], &suppressed);
        let t = ledger.tally(&id("COV001"));
        assert_eq!((t.accepted, t.waived, t.open), (2, 1, 1));
        assert_eq!(ledger.tally(&id("DOC001")).waived, 1);
        let rows = ledger.rows();
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0].rule, "COV001");
        assert_eq!(
            rows[0].not_useful_percent, None,
            "3 decided is below the minimum"
        );
    }

    // frob:tests crates/gob-rules/src/precision.rs::RuleTally.not_useful_percent
    #[test]
    fn the_rate_counts_accepts_and_dismissals_over_decided_findings() {
        let t = RuleTally {
            accepted: 3,
            dismissed: 1,
            waived: 2,
            fixed: 4,
            open: 9,
        };
        assert_eq!(t.decided(), 10);
        assert_eq!(t.not_useful_percent(5), Some(40));
        assert_eq!(t.not_useful_percent(11), None);
        assert_eq!(RuleTally::default().not_useful_percent(0), None);
    }

    // frob:tests crates/gob-rules/src/precision.rs::PrecisionLedger.demotions
    #[test]
    fn only_rules_over_the_ceiling_with_enough_samples_are_demoted() {
        let mut ledger = PrecisionLedger::new();
        let noisy = id("WEB001");
        let fine = id("COV001");
        let thin = id("DOC001");
        ledger.add_dismissed(&noisy, 9);
        ledger.add_fixed(&noisy, 1);
        ledger.add_fixed(&fine, 9);
        ledger.add_dismissed(&fine, 1);
        ledger.add_dismissed(&thin, 3);
        let d = ledger.demotions(15);
        assert_eq!(d.len(), 1);
        assert_eq!(d[0].rule, noisy);
        assert_eq!(d[0].not_useful_percent, 90);
        assert!(d[0].to_string().contains("90% not useful (ceiling 15%)"));
        assert!(
            ledger.demotions(90).is_empty(),
            "at the ceiling is not over it"
        );
    }
}
