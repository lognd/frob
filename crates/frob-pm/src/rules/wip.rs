//! `PM013`: more tickets are in progress than `[pm.wip] in_progress` allows.
//!
//! The count is the ledger index's in-progress list ([`in_progress`]), the
//! same list `work` and `start` count in `frob-worktree` before refusing, so
//! the gate and the rule can never disagree about who holds a slot. The rule
//! reads the index only (no leases): a stale in-progress ticket still counts
//! here and is named, because it is still a card in the column. The pure core
//! [`pm013`] takes the holders; [`evaluate`] reads them from a ledger.

// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY

use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::Category;
use frob_ledger::{Ledger, LedgerError};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::rules::membership::Evaluation;

/// The repository has more tickets in progress than `[pm.wip] in_progress` allows.
///
/// Fires once, naming every holder, when the in-progress count exceeds the
/// limit. A limit of 0 turns the rule off. `work` and `start` refuse before
/// the limit is crossed, so this fires for tickets moved past the gate
/// (by hand, by a merge of two ledger branches, or by lowering the limit).
///
/// ## Remedy
///
/// Finish or requeue one of the named holders with `frob requeue TICKET
/// --reason WHY`, or raise `[pm.wip] in_progress` in `frob.toml`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM013",
    slug = "wip-limit-exceeded",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm013;

fn rule_id() -> RuleId {
    Pm013
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// Every in-progress ticket at the ledger index, the one count behind the WIP gate and `PM013`.
///
/// # Errors
///
/// Ledger read failures.
pub fn in_progress(ledger: &Ledger) -> std::result::Result<Vec<Summary>, LedgerError> {
    let filter = ListFilter {
        category: Some(Category::InProgress),
        ..ListFilter::default()
    };
    ledger.list(&filter)
}

/// Split holders into the ones that count against the repository limit and the expedite lane.
///
/// This is the single point where the expedite exemption of `releases.md`
/// section 2 plugs in: until ticket classes exist every holder is standard,
/// so the second list is always empty.
pub fn split_lanes(holders: Vec<Summary>) -> (Vec<Summary>, Vec<Summary>) {
    (holders, Vec::new())
}

/// Evaluate `PM013` for `holders` (in-progress tickets) against `limit`; 0 is off.
pub fn pm013(limit: u32, holders: Vec<Summary>) -> Evaluation {
    let mut out = Evaluation::default();
    if limit == 0 {
        tracing::debug!("PM013 off: limit is 0");
        return out;
    }
    let (standard, expedite) = split_lanes(holders);
    out.subjects = standard.len() + expedite.len();
    if standard.len() <= limit as usize {
        tracing::debug!(count = standard.len(), limit, "PM013 within limit");
        return out;
    }
    let named = standard
        .iter()
        .map(|s| format!("{} ({})", s.handle, s.title))
        .collect::<Vec<_>>()
        .join(", ");
    tracing::debug!(count = standard.len(), limit, "PM013: over the limit");
    out.findings.push(Finding::new(
        rule_id(),
        Severity::Warn,
        None,
        format!(
            "{} tickets are in progress, over the [pm.wip] in_progress limit of {limit}; holders: {named}; finish or requeue one (frob requeue <ticket> --reason <why>) or raise the limit",
            standard.len()
        ),
        "wip:in_progress",
    ));
    out
}

/// Read the in-progress tickets from `ledger` and run [`pm013`] against `limit`.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, limit: u32) -> Result<Evaluation> {
    if limit == 0 {
        tracing::info!("PM013 not applicable: [pm.wip] in_progress is 0");
        return Ok(Evaluation::default());
    }
    let out = pm013(limit, in_progress(ledger)?);
    tracing::info!(
        limit,
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM013 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_lanes_has_no_expedite_until_classes_exist() {
        // frob:tests crates/frob-pm/src/rules/wip.rs::split_lanes
        let (standard, expedite) = split_lanes(Vec::new());
        assert!(standard.is_empty() && expedite.is_empty());
    }

    #[test]
    fn limit_zero_is_off() {
        // frob:tests crates/frob-pm/src/rules/wip.rs::pm013
        assert!(pm013(0, Vec::new()).findings.is_empty());
    }
}
