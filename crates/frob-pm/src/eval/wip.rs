//! `PM013`: more tickets are in progress than `[pm.wip] in_progress` allows.
//!
//! What counts toward WIP has one definition, implemented once here ([`count`])
//! and used by both this rule and the `work`/`start` gate in `frob-worktree`:
//!
//! - an in-progress ticket holds a slot only while its lease is live; one whose
//!   lease expired is *stale*, listed in [`Wip::stale`] and never counted;
//! - an expedite ticket (class field) is in the expedite lane, exempt from the
//!   repository limit and bounded by `[pm.classes] expedite_max` instead; with
//!   `expedite_max = 0` the lane is closed and expedite counts like standard.
//!
//! Liveness is passed in as a set of ticket ids (the caller reads the lease
//! store), so this crate stays free of the lease dependency. `None` means the
//! leases could not be read: every in-progress ticket is then taken as live.

// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
// frob:ticket 01M416Z11V5GR012FR47HWFTBP

use std::collections::BTreeSet;

use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::{Category, Class};
use frob_ledger::{Ledger, LedgerError, TicketId};
use gob_rules::{Finding, RuleId, Severity};

use crate::eval::id_of;
use crate::rules::pm013::Pm013;

use crate::error::Result;
use crate::eval::membership::Evaluation;

fn rule_id() -> RuleId {
    id_of::<Pm013>()
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

/// Split holders into the standard lane (counts against the repository limit) and the expedite lane.
///
/// A holder is in the expedite lane when its class is expedite and the lane is
/// open (`expedite_max` above 0); otherwise it is standard.
pub fn split_lanes(holders: Vec<Summary>, expedite_max: u32) -> (Vec<Summary>, Vec<Summary>) {
    holders
        .into_iter()
        .partition(|s| !(s.class == Class::Expedite && expedite_max > 0))
}

/// The in-progress tickets sorted into the lanes that decide WIP.
#[derive(Debug, Clone, Default)]
pub struct Wip {
    /// Live holders counting against `[pm.wip] in_progress`.
    pub standard: Vec<Summary>,
    /// Live holders in the expedite lane, bounded by `[pm.classes] expedite_max`.
    pub expedite: Vec<Summary>,
    /// In progress with an expired lease: reported, never counted.
    pub stale: Vec<Summary>,
}

/// Sort `in_progress` into [`Wip`]: drop stale holders (`live` is the set of leased tickets; `None` takes all as live), then split lanes.
pub fn count(
    in_progress: Vec<Summary>,
    live: Option<&BTreeSet<TicketId>>,
    expedite_max: u32,
) -> Wip {
    let (held, stale): (Vec<Summary>, Vec<Summary>) = in_progress
        .into_iter()
        .partition(|s| live.is_none_or(|l| l.contains(&s.id)));
    let (standard, expedite) = split_lanes(held, expedite_max);
    tracing::debug!(
        standard = standard.len(),
        expedite = expedite.len(),
        stale = stale.len(),
        "wip counted"
    );
    Wip {
        standard,
        expedite,
        stale,
    }
}

/// Read the in-progress tickets from `ledger` and sort them with [`count`].
///
/// # Errors
///
/// Ledger read failures.
pub fn read(
    ledger: &Ledger,
    live: Option<&BTreeSet<TicketId>>,
    expedite_max: u32,
) -> std::result::Result<Wip, LedgerError> {
    Ok(count(in_progress(ledger)?, live, expedite_max))
}

/// The two knobs of the WIP policy: `[pm.wip] in_progress` and `[pm.classes] expedite_max`; 0 turns either off.
#[derive(Debug, Clone, Copy)]
pub struct WipLimits {
    /// Repository-wide limit on standard holders.
    pub in_progress: u32,
    /// Expedite tickets allowed at once; 0 closes the lane.
    pub expedite_max: u32,
}

fn holders(list: &[Summary]) -> String {
    list.iter()
        .map(|s| format!("{} ({})", s.handle, s.title))
        .collect::<Vec<_>>()
        .join(", ")
}

/// Evaluate `PM013` for sorted `wip` against `limits`: fires for standard holders over `in_progress` (0 is off) and for the expedite lane over `expedite_max`.
pub fn pm013(limits: WipLimits, wip: &Wip) -> Evaluation {
    let mut out = Evaluation {
        subjects: wip.standard.len() + wip.expedite.len(),
        ..Evaluation::default()
    };
    let limit = limits.in_progress;
    if limit > 0 && wip.standard.len() > limit as usize {
        tracing::debug!(count = wip.standard.len(), limit, "PM013: over the limit");
        out.findings.push(Finding::new(
            rule_id(),
            Severity::Warn,
            None,
            format!(
                "{} tickets are in progress, over the [pm.wip] in_progress limit of {limit}; holders: {}; finish or requeue one (frob requeue <ticket> --reason <why>) or raise the limit",
                wip.standard.len(),
                holders(&wip.standard)
            ),
            "wip:in_progress",
        ));
    }
    let max = limits.expedite_max;
    if max > 0 && wip.expedite.len() > max as usize {
        tracing::debug!(count = wip.expedite.len(), max, "PM013: expedite lane over");
        out.findings.push(Finding::new(
            rule_id(),
            Severity::Warn,
            None,
            format!(
                "{} expedite tickets are in progress, over the [pm.classes] expedite_max of {max}; holders: {}; finish or requeue one (frob requeue <ticket> --reason <why>) or raise expedite_max",
                wip.expedite.len(),
                holders(&wip.expedite)
            ),
            "wip:expedite",
        ));
    }
    out
}

/// Read the in-progress tickets from `ledger`, count them with [`count`] against `live` (`None`: all live) and run [`pm013`].
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate_with(
    ledger: &Ledger,
    limits: WipLimits,
    live: Option<&BTreeSet<TicketId>>,
) -> Result<Evaluation> {
    if limits.in_progress == 0 && limits.expedite_max == 0 {
        tracing::info!("PM013 not applicable: both WIP limits are 0");
        return Ok(Evaluation::default());
    }
    let wip = read(ledger, live, limits.expedite_max)?;
    let out = pm013(limits, &wip);
    tracing::info!(
        limit = limits.in_progress,
        expedite_max = limits.expedite_max,
        stale = wip.stale.len(),
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
    fn limits_zero_are_off() {
        // frob:tests crates/frob-pm/src/eval/wip.rs::pm013
        let off = WipLimits {
            in_progress: 0,
            expedite_max: 0,
        };
        assert!(pm013(off, &Wip::default()).findings.is_empty());
    }

    #[test]
    fn empty_input_splits_to_empty_lanes() {
        // frob:tests crates/frob-pm/src/eval/wip.rs::split_lanes
        // frob:tests crates/frob-pm/src/eval/wip.rs::count
        let wip = count(Vec::new(), Some(&BTreeSet::new()), 1);
        assert!(wip.standard.is_empty() && wip.expedite.is_empty() && wip.stale.is_empty());
    }
}
