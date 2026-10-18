//! `PM011`: a planned or active cycle has no goal.
//!
//! A cycle is a commitment to an outcome; `cycle new` requires a goal, so an
//! empty one means the cycle was edited or merged in without it. The pure
//! core [`pm011`] takes `(alias, goal)` pairs; [`evaluate`] reads them from a
//! ledger.

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use frob_ledger::Ledger;
use gob_rules::{Finding, RuleId, Severity};

use crate::cycle::lifecycle::with_state;
use crate::error::Result;
use crate::eval::cycle::cycles;
use crate::eval::id_of;
use crate::eval::membership::Evaluation;
use crate::model::State;
use crate::rules::pm011::Pm011;
use crate::store::PmStore;

fn rule_id() -> RuleId {
    id_of::<Pm011>()
}

/// Evaluate `PM011` over `(alias, goal)` pairs of the open cycles: one Warn per blank goal.
pub fn pm011(open: &[(String, String)]) -> Evaluation {
    let findings = open
        .iter()
        .filter(|(_, goal)| goal.trim().is_empty())
        .map(|(alias, _)| {
            tracing::debug!(cycle = %alias, "PM011: cycle has no goal");
            Finding::new(
                rule_id(),
                Severity::Warn,
                None,
                format!(
                    "cycle {alias} has no goal; state the outcome it commits to (recreate it with `frob cycle new --goal TEXT`)"
                ),
                &format!("cycle:{alias}"),
            )
        })
        .collect();
    Evaluation {
        findings,
        subjects: open.len(),
    }
}

/// Read the open cycles of `ledger` and run [`pm011`].
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger) -> Result<Evaluation> {
    let today = PmStore::new(ledger).today();
    let open: Vec<(String, String)> = cycles(ledger)?
        .into_iter()
        .map(|c| with_state(c, today))
        .filter(|c| c.state != State::Closed)
        .map(|c| (c.alias(), c.goal))
        .collect();
    let out = pm011(&open);
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM011 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pair(goal: &str) -> (String, String) {
        ("2026-10-05..2026-10-11".to_owned(), goal.to_owned())
    }

    #[test]
    fn blank_goal_fires() {
        // frob:tests crates/frob-pm/src/eval/goal.rs::pm011
        let out = pm011(&[pair(""), pair("   ")]);
        assert_eq!(out.findings.len(), 2);
        assert_eq!(out.findings[0].severity, Severity::Warn);
    }

    #[test]
    fn stated_goal_is_clean() {
        // frob:tests crates/frob-pm/src/eval/goal.rs::pm011
        let out = pm011(&[pair("ship the gate")]);
        assert!(out.findings.is_empty());
        assert_eq!(out.subjects, 1);
    }
}
