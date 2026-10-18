//! `PM010`: a planned or active cycle commits more points than its capacity.
//!
//! Capacity is the cycle's own `capacity_points`, else `rolling_mean - k *
//! stddev` over closed cycles once `[pm] min_history` of them exist; before
//! that nothing is enforced and the rule stays silent (a fresh repository
//! never trips it). `cycle assign` refuses past capacity unless
//! `--over-commit --reason`; this rule catches what got past that gate (by
//! hand edits, merged ledger branches or a capacity lowered later). The
//! pure core [`pm010`] takes the loads; [`evaluate`] reads them from a ledger.

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use frob_ledger::Ledger;
use gob_rules::{Finding, RuleId, Severity};

use crate::cycle::history::{deliveries, done_points, member_points};
use crate::cycle::lifecycle::with_state;
use crate::cycle::velocity::{Capacity, capacity, committed};
use crate::error::Result;
use crate::eval::cycle::cycles;
use crate::eval::id_of;
use crate::eval::membership::Evaluation;
use crate::model::State;
use crate::rules::pm010::Pm010;
use crate::store::PmStore;

fn rule_id() -> RuleId {
    id_of::<Pm010>()
}

/// The commitment of one open cycle against its capacity.
#[derive(Debug, Clone, PartialEq)]
pub struct Load {
    /// The cycle's alias (`START..END`).
    pub alias: String,
    /// Points committed by its velocity-counting members.
    pub committed: u32,
    /// The capacity that applies to it.
    pub capacity: Capacity,
}

/// Evaluate `PM010` over `loads`: one Advisory finding per cycle whose commitment exceeds an enforced capacity.
pub fn pm010(loads: &[Load]) -> Evaluation {
    let findings = loads
        .iter()
        .filter_map(|l| {
            let limit = l.capacity.limit()?;
            if l.committed <= limit {
                tracing::debug!(cycle = %l.alias, committed = l.committed, limit, "PM010: within capacity");
                return None;
            }
            tracing::debug!(cycle = %l.alias, committed = l.committed, limit, "PM010: over capacity");
            Some(Finding::new(
                rule_id(),
                Severity::Advisory,
                None,
                format!(
                    "cycle {} commits {} points, over its capacity of {limit}; {} (move work to a later cycle with `frob cycle assign TICKET CYCLE`, or record the over-commit with --over-commit --reason WHY)",
                    l.alias,
                    l.committed,
                    l.capacity.describe()
                ),
                &format!("cycle:{}", l.alias),
            ))
        })
        .collect();
    Evaluation {
        findings,
        subjects: loads.len(),
    }
}

/// Read the open cycles of `ledger`, their commitments and capacities, and run [`pm010`].
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, min_history: u32, k: f64) -> Result<Evaluation> {
    let store = PmStore::new(ledger);
    let today = store.today();
    let all: Vec<_> = cycles(ledger)?
        .into_iter()
        .map(|c| with_state(c, today))
        .collect();
    let done = done_points(&deliveries(store, ledger, &all));
    let loads: Vec<Load> = all
        .iter()
        .filter(|c| c.state != State::Closed)
        .map(|c| Load {
            alias: c.alias(),
            committed: committed(&member_points(ledger, c)),
            capacity: capacity(c, &all, &done, min_history, k),
        })
        .collect();
    let out = pm010(&loads);
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM010 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn load(committed: u32, capacity: Capacity) -> Load {
        Load {
            alias: "2026-10-05..2026-10-11".to_owned(),
            committed,
            capacity,
        }
    }

    #[test]
    fn over_a_set_capacity_fires_with_both_numbers() {
        // frob:tests crates/frob-pm/src/eval/capacity.rs::pm010
        let out = pm010(&[load(9, Capacity::Set(5))]);
        assert_eq!(out.findings.len(), 1);
        let f = &out.findings[0];
        assert_eq!(f.severity, Severity::Advisory);
        assert!(f.message.contains("commits 9 points"), "{}", f.message);
        assert!(f.message.contains("capacity of 5"), "{}", f.message);
    }

    #[test]
    fn at_capacity_and_unenforced_are_silent() {
        // frob:tests crates/frob-pm/src/eval/capacity.rs::pm010
        let loads = [
            load(5, Capacity::Set(5)),
            load(99, Capacity::Unenforced { have: 1, need: 3 }),
        ];
        let out = pm010(&loads);
        assert!(out.findings.is_empty());
        assert_eq!(out.subjects, 2);
    }

    #[test]
    fn computed_capacity_is_enforced() {
        // frob:tests crates/frob-pm/src/eval/capacity.rs::pm010
        let cap = Capacity::Computed {
            limit: 4,
            mean: 5.0,
            stddev: 1.0,
            k: 0.5,
            cycles: 3,
        };
        assert_eq!(pm010(&[load(6, cap)]).findings.len(), 1);
    }
}
