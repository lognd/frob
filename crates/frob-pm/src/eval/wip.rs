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
//! - an in-progress ticket that is *ready to land* (every acceptance criterion
//!   bound and its latest evidence per reference passing, see [`is_ready`]) is
//!   finished work waiting its turn on the serial land train: it leaves both
//!   lanes for [`Wip::ready`], bounded by the optional `[pm.wip] ready` limit.
//!
//! Liveness is passed in as a set of ticket ids (the caller reads the lease
//! store), so this crate stays free of the lease dependency. `None` means the
//! leases could not be read: every in-progress ticket is then taken as live.

// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
// frob:ticket 01M416Z11V5GR012FR47HWFTBP
// frob:ticket 01M4H5Y68GYFTMG9Y73F696589

use std::collections::BTreeSet;

use frob_ledger::event::{Event, EventBody};
use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::{Acceptance, Category, Class};
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
    /// Live holders that are finished and wait to land: counted against `[pm.wip] ready`, not `in_progress`.
    pub ready: Vec<Summary>,
}

/// True when finished work is waiting to land: every acceptance criterion is bound and, per reference, the latest evidence passed and was measured.
///
/// A ticket with no evidence at all is not ready; one with no criteria is judged on its evidence alone.
pub fn is_ready(acceptance: &[Acceptance], events: &[Event]) -> bool {
    use std::collections::BTreeMap;
    if !acceptance.iter().all(|a| a.bound) {
        return false;
    }
    let mut latest: BTreeMap<String, bool> = BTreeMap::new();
    for event in events {
        let EventBody::Evidence(data) = &event.body else {
            continue;
        };
        let key = format!(
            "{}\u{0}{}",
            data.record
                .get("provider")
                .and_then(toml::Value::as_str)
                .unwrap_or_default(),
            data.record
                .get("ref")
                .and_then(toml::Value::as_str)
                .unwrap_or_default()
        );
        let passed = data
            .record
            .get("passed")
            .and_then(toml::Value::as_bool)
            .unwrap_or(true)
            && data
                .record
                .get("status")
                .and_then(toml::Value::as_str)
                .is_none_or(|st| st != "unmeasured");
        latest.insert(key, passed);
    }
    !latest.is_empty() && latest.values().all(|p| *p)
}

/// The ids among `held` that are [`is_ready`], read from the ledger.
///
/// # Errors
///
/// Ledger read failures.
pub fn ready_ids(
    ledger: &Ledger,
    held: &[Summary],
) -> std::result::Result<BTreeSet<TicketId>, LedgerError> {
    let mut out = BTreeSet::new();
    for s in held {
        let view = ledger.show(s.id)?;
        if is_ready(&view.ticket.front.acceptance, &ledger.events(s.id)?) {
            out.insert(s.id);
        }
    }
    tracing::debug!(
        ready = out.len(),
        held = held.len(),
        "ready-to-land tickets read"
    );
    Ok(out)
}

/// Sort `in_progress` into [`Wip`]: drop stale holders (`live` is the set of leased tickets; `None` takes all as live), then split lanes.
pub fn count(
    in_progress: Vec<Summary>,
    live: Option<&BTreeSet<TicketId>>,
    expedite_max: u32,
) -> Wip {
    count_ready(in_progress, live, &BTreeSet::new(), expedite_max)
}

/// Like [`count`], but live holders in `ready` (see [`ready_ids`]) go to [`Wip::ready`] instead of a lane.
pub fn count_ready(
    in_progress: Vec<Summary>,
    live: Option<&BTreeSet<TicketId>>,
    ready: &BTreeSet<TicketId>,
    expedite_max: u32,
) -> Wip {
    let (held, stale): (Vec<Summary>, Vec<Summary>) = in_progress
        .into_iter()
        .partition(|s| live.is_none_or(|l| l.contains(&s.id)));
    let (ready, held): (Vec<Summary>, Vec<Summary>) =
        held.into_iter().partition(|s| ready.contains(&s.id));
    let (standard, expedite) = split_lanes(held, expedite_max);
    tracing::debug!(
        standard = standard.len(),
        expedite = expedite.len(),
        ready = ready.len(),
        stale = stale.len(),
        "wip counted"
    );
    Wip {
        standard,
        expedite,
        stale,
        ready,
    }
}

/// Read the in-progress tickets from `ledger` and sort them with [`count_ready`], ready-to-land ones included.
///
/// # Errors
///
/// Ledger read failures.
pub fn read(
    ledger: &Ledger,
    live: Option<&BTreeSet<TicketId>>,
    expedite_max: u32,
) -> std::result::Result<Wip, LedgerError> {
    let held = in_progress(ledger)?;
    let ready = ready_ids(ledger, &held)?;
    Ok(count_ready(held, live, &ready, expedite_max))
}

/// The two knobs of the WIP policy: `[pm.wip] in_progress` and `[pm.classes] expedite_max`; 0 turns either off.
#[derive(Debug, Clone, Copy, Default)]
pub struct WipLimits {
    /// Repository-wide limit on standard holders.
    pub in_progress: u32,
    /// Expedite tickets allowed at once; 0 closes the lane.
    pub expedite_max: u32,
    /// Ready-to-land tickets allowed at once; 0 leaves the column unlimited.
    pub ready: u32,
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
        subjects: wip.standard.len() + wip.expedite.len() + wip.ready.len(),
        ..Evaluation::default()
    };
    let limit = limits.in_progress;
    if limit > 0 && wip.standard.len() > limit as usize {
        tracing::debug!(count = wip.standard.len(), limit, "PM013: over the limit");
        out.findings.push(Finding::new(
            rule_id(),
            Severity::Error,
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
            Severity::Error,
            None,
            format!(
                "{} expedite tickets are in progress, over the [pm.classes] expedite_max of {max}; holders: {}; finish or requeue one (frob requeue <ticket> --reason <why>) or raise expedite_max",
                wip.expedite.len(),
                holders(&wip.expedite)
            ),
            "wip:expedite",
        ));
    }
    if limits.ready > 0 && wip.ready.len() > limits.ready as usize {
        tracing::debug!(
            count = wip.ready.len(),
            limit = limits.ready,
            "PM013: ready column over"
        );
        out.findings.push(Finding::new(
            rule_id(),
            Severity::Error,
            None,
            format!(
                "{} tickets are ready to land, over the [pm.wip] ready limit of {}; waiting: {}; land them (frob land <ticket>) or raise the limit",
                wip.ready.len(),
                limits.ready,
                holders(&wip.ready)
            ),
            "wip:ready",
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
    if limits.in_progress == 0 && limits.expedite_max == 0 && limits.ready == 0 {
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
            ready: 0,
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

    fn evidence(reference: &str, passed: bool) -> Event {
        let mut record = toml::Table::new();
        record.insert("provider".into(), "nextest".into());
        record.insert("ref".into(), reference.into());
        record.insert("passed".into(), passed.into());
        Event::new(
            frob_ledger::model::Stamp::from_unix(0),
            "t",
            EventBody::Evidence(frob_ledger::event::EvidenceData {
                accepts: vec![1],
                record,
            }),
        )
    }

    fn summary(n: u8) -> Summary {
        let at = frob_ledger::model::Stamp::from_unix(0);
        Summary {
            id: format!("01M4069W45P08YPC4YH4XZVM{n:02}")
                .parse()
                .expect("ulid"),
            handle: format!("~4XZVM{n:02}"),
            title: "t".to_owned(),
            ty: "task".parse().expect("type"),
            category: "in-progress".parse().expect("category"),
            outcome: None,
            priority: "medium".parse().expect("priority"),
            class: "standard".parse().expect("class"),
            due: None,
            points: None,
            parent: None,
            created: at,
            updated: at,
            blocked: false,
        }
    }

    fn criterion(bound: bool) -> Acceptance {
        Acceptance {
            text: "c".into(),
            bound,
        }
    }

    #[test]
    fn ready_needs_bound_criteria_and_passing_latest_evidence() {
        // frob:tests crates/frob-pm/src/eval/wip.rs::is_ready
        let pass = evidence("-p x", true);
        let fail = evidence("-p x", false);
        assert!(is_ready(&[criterion(true)], std::slice::from_ref(&pass)));
        assert!(!is_ready(&[criterion(false)], std::slice::from_ref(&pass)));
        assert!(
            !is_ready(&[criterion(true)], &[]),
            "no evidence is not ready"
        );
        assert!(!is_ready(&[criterion(true)], &[pass.clone(), fail.clone()]));
        assert!(
            is_ready(&[criterion(true)], &[fail, pass]),
            "a later passing run supersedes a failure of the same ref"
        );
    }

    #[test]
    fn ready_holders_leave_the_in_progress_count() {
        // frob:tests crates/frob-pm/src/eval/wip.rs::count_ready
        // frob:tests crates/frob-pm/src/eval/wip.rs::pm013
        let all: Vec<Summary> = (1..=16).map(summary).collect();
        let ready: BTreeSet<TicketId> = all[..9].iter().map(|s| s.id).collect();
        let wip = count_ready(all, None, &ready, 0);
        assert_eq!((wip.standard.len(), wip.ready.len()), (7, 9));
        let limits = WipLimits {
            in_progress: 7,
            expedite_max: 0,
            ready: 8,
        };
        let out = pm013(limits, &wip);
        assert_eq!(out.findings.len(), 1, "only the ready limit is exceeded");
        assert!(out.findings[0].message.contains("ready to land"));
    }
}
