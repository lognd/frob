//! `PM032`: fewer than `[tickets] good_first_min` ready good-first tickets.
//!
//! "Ready" is the set `frob ticket doable` lists ([`Ledger::doable`]) restricted to the
//! `good-first` label, so a newcomer's pool and the pull verb never disagree (navigation.md
//! section 4.2). The pure core [`pm032`] takes the count; [`evaluate`] reads it from a ledger.

// frob:ticket 01M3ZX87ZJR4YVZZ4AS7VSR4BQ

use std::collections::BTreeSet;

use frob_ledger::guards::LeaseCheck;
use frob_ledger::index::ListFilter;
use frob_ledger::{Ledger, TicketId};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::eval::membership::Evaluation;
use crate::legacy::good_first::GOOD_FIRST_LABEL;

/// The `[tickets] good_first_min` default.
pub const DEFAULT_MIN: u32 = 3;

/// Fewer than `[tickets] good_first_min` ready tickets carry the `good-first` label.
///
/// Reports the ready count and the minimum. A minimum of 0 turns the rule off.
///
/// ## Remedy
///
/// Label more ready tickets `good-first` (with a `## Start here` section), or lower
/// `[tickets] good_first_min` in `frob.toml`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM032",
    slug = "good-first-pool-low",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm032;

fn rule_id() -> RuleId {
    Pm032
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The `[tickets] good_first_min` of the `frob.toml` in `root`; the default when the file, table or key is absent or unreadable (the config loader reports a malformed file elsewhere).
pub fn min_ready(root: &std::path::Path) -> u32 {
    std::fs::read_to_string(root.join("frob.toml"))
        .ok()
        .and_then(|t| t.parse::<toml::Table>().ok())
        .and_then(|t| t.get("tickets")?.get("good_first_min")?.as_integer())
        .and_then(|n| u32::try_from(n).ok())
        .unwrap_or(DEFAULT_MIN)
}

/// Evaluate `PM032` for `ready` ready good-first tickets against `min`; 0 is off.
pub fn pm032(min: u32, ready: usize) -> Evaluation {
    let mut out = Evaluation::default();
    if min == 0 {
        tracing::debug!("PM032 off: good_first_min is 0");
        return out;
    }
    out.subjects = ready;
    if ready >= min as usize {
        tracing::debug!(ready, min, "PM032 pool at or above the minimum");
        return out;
    }
    out.findings.push(Finding::new(
        rule_id(),
        Severity::Warn,
        None,
        format!("{ready} ready good-first ticket(s), below the minimum of {min}"),
        "ready:good-first",
    ));
    out
}

/// Count the doable `good-first` tickets of `ledger` under `leases` and run [`pm032`] against `min`.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, leases: &dyn LeaseCheck, min: u32) -> Result<Evaluation> {
    if min == 0 {
        tracing::info!("PM032 not applicable: good_first_min is 0");
        return Ok(Evaluation::default());
    }
    let labelled: BTreeSet<TicketId> = ledger
        .list(&ListFilter {
            label: Some(GOOD_FIRST_LABEL.to_owned()),
            ..ListFilter::default()
        })?
        .into_iter()
        .map(|s| s.id)
        .collect();
    let ready = ledger
        .doable(leases)?
        .iter()
        .filter(|s| labelled.contains(&s.id))
        .count();
    let out = pm032(min, ready);
    tracing::info!(ready, min, findings = out.findings.len(), "PM032 evaluated");
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn minimum_zero_is_off() {
        // frob:tests crates/frob-pm/src/legacy/pm032.rs::pm032
        assert!(pm032(0, 0).findings.is_empty());
    }

    #[test]
    fn message_carries_count_and_minimum() {
        // frob:tests crates/frob-pm/src/legacy/pm032.rs::pm032
        let f = &pm032(3, 2).findings[0];
        assert_eq!(f.severity, Severity::Warn);
        assert!(f.message.contains('2') && f.message.contains("minimum of 3"));
        assert!(pm032(3, 3).findings.is_empty());
    }
}
