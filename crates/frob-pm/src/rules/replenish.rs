//! `PM033`: the ready queue is below the `[pm] ready_min` order point.
//!
//! "Ready" is exactly the set `frob ticket doable` lists: [`Ledger::doable`]
//! is the one definition, so the advice and the pull verb can never disagree
//! about what is available. The advice names `cycle plan` without the `frob`
//! prefix until that verb exists (`remedies.rs` rejects unknown verb paths);
//! restore `run frob cycle plan` when it lands. The pure core [`pm033`] takes the count;
//! [`evaluate`] reads it from a ledger and a lease check.

// frob:ticket 01M4069TJA7YJTYSZCATV5ZYFS

use frob_ledger::Ledger;
use frob_ledger::guards::LeaseCheck;
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::rules::membership::Evaluation;

/// The ready queue holds fewer doable tickets than `[pm] ready_min`.
///
/// Advisory only: it never fails the gate. A `ready_min` of 0 turns the rule
/// off.
///
/// ## Remedy
///
/// Plan the next cycle (`cycle plan`) or triage the backlog so more tickets become
/// doable, or lower `[pm] ready_min` in `frob.toml`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM033",
    slug = "ready-queue-low",
    family = "PM",
    severity = Advisory,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm033;

fn rule_id() -> RuleId {
    Pm033
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// Evaluate `PM033` for a ready queue of `ready` tickets against `ready_min`; 0 is off.
pub fn pm033(ready_min: u32, ready: usize) -> Evaluation {
    let mut out = Evaluation::default();
    if ready_min == 0 {
        tracing::debug!("PM033 off: ready_min is 0");
        return out;
    }
    out.subjects = ready;
    if ready >= ready_min as usize {
        tracing::debug!(ready, ready_min, "PM033 queue at or above the order point");
        return out;
    }
    tracing::debug!(ready, ready_min, "PM033: ready queue below the order point");
    out.findings.push(Finding::new(
        rule_id(),
        Severity::Advisory,
        None,
        format!(
            "ready queue is {ready}, below {ready_min}: plan the next cycle (cycle plan) or triage"
        ),
        "ready:queue",
    ));
    out
}

/// Count the doable tickets of `ledger` under `leases` and run [`pm033`] against `ready_min`.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, leases: &dyn LeaseCheck, ready_min: u32) -> Result<Evaluation> {
    if ready_min == 0 {
        tracing::info!("PM033 not applicable: [pm] ready_min is 0");
        return Ok(Evaluation::default());
    }
    let ready = ledger.doable(leases)?.len();
    let out = pm033(ready_min, ready);
    tracing::info!(
        ready,
        ready_min,
        findings = out.findings.len(),
        "PM033 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ready_min_zero_is_off() {
        // frob:tests crates/frob-pm/src/rules/replenish.rs::pm033
        assert!(pm033(0, 0).findings.is_empty());
    }

    #[test]
    fn message_carries_both_counts() {
        // frob:tests crates/frob-pm/src/rules/replenish.rs::pm033
        let f = &pm033(4, 1).findings[0];
        assert_eq!(f.severity, Severity::Advisory);
        assert!(
            f.message.contains("ready queue is 1, below 4"),
            "{}",
            f.message
        );
    }
}
