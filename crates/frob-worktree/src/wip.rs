//! The repository WIP limit (`[pm.wip] in_progress`): who holds the slots and when `work` and `start` must refuse.
//!
//! Only in-progress tickets with a live lease count, and expedite tickets
//! count in their own lane, not against the repository limit. An in-progress ticket whose
//! lease expired is stale: it is named in the refusal (with a requeue hint) but
//! never occupies a slot. The decision is a pure function over those two lists
//! so it can be tested without a repository. The expedite lane of
//! `releases.md` section 2 is the one exception: an expedite ticket may exceed
//! the repository limit, at most `[pm.classes] expedite_max` at a time. What
//! counts is defined once in `frob_pm::rules::wip::count`, shared with `PM013`.

// frob:ticket 01M4069T76A6WSNHT3NZERXHAH
// frob:ticket 01M4069VZVMHVZ15RSPZQRNCXY
// frob:ticket 01M416Z11V5GR012FR47HWFTBP
// frob:ticket 01M40Q3S4T9QTYX0Z1MPAZP9JM

use std::collections::BTreeSet;
use std::fmt::Write;

use frob_lease::Lease;
use frob_ledger::index::Summary;
use frob_ledger::model::Stamp;
use frob_ledger::model::{Category, Class};
use frob_ledger::{Ledger, LedgerError, TicketId};
use gob_diagnostics::{Refusal, RefusalClass};

use crate::error::WorktreeError;

/// The refusal code of a repository WIP breach.
pub const CODE: &str = "E-WIP-REPO";

/// The refusal code of taking an expedite ticket past `[pm.classes] expedite_max`.
pub const EXPEDITE_CODE: &str = "E-WIP-EXPEDITE";

/// One in-progress ticket holding a WIP slot: its live lease.
#[derive(Debug, Clone)]
pub struct Holding {
    /// Handle with `~`.
    pub handle: String,
    /// Ticket title.
    pub title: String,
    /// The live lease (holder, worktree, since).
    pub lease: Lease,
    /// Class of service of the held ticket.
    pub class: Class,
}

/// One in-progress ticket whose lease expired: reported, not counted.
#[derive(Debug, Clone)]
pub struct Stale {
    /// Handle with `~`.
    pub handle: String,
    /// Ticket title.
    pub title: String,
    /// Time of the ticket's latest event.
    pub since: Stamp,
}

/// Append one line per holder to `msg`.
fn write_holders<'a>(msg: &mut String, holdings: impl Iterator<Item = &'a Holding>) {
    for h in holdings {
        let _ = write!(
            msg,
            "\n  {} {} - holder {}, worktree {}, since {}",
            h.handle,
            h.title,
            h.lease.holder.actor,
            h.lease.holder.worktree.display(),
            h.lease.acquired_at
        );
    }
}

/// The refusal for taking one more expedite ticket when `max` are already running; `None` when the lane is closed (0) or has room.
pub fn expedite_refusal(max: u32, holdings: &[Holding], handle: &str) -> Option<Refusal> {
    let running: Vec<&Holding> = holdings
        .iter()
        .filter(|h| h.class == Class::Expedite)
        .collect();
    if max == 0 || running.len() < max as usize {
        return None;
    }
    let mut msg = format!(
        "the expedite lane is full ({} of {max}); taking {handle} would exceed [pm.classes] expedite_max. Running expedite tickets:",
        running.len()
    );
    write_holders(&mut msg, running.into_iter());
    let remedy = "finish or requeue the running expedite ticket (frob requeue <ticket> --reason <why>), or raise [pm.classes] expedite_max in frob.toml";
    Some(Refusal::new(EXPEDITE_CODE, RefusalClass::GuardNeedsAction, msg).with_remedy(remedy))
}

/// The refusal for taking one more ticket when `holdings` already fill `ceiling` slots; `None` when there is room or the limit is off (0).
pub fn refusal(
    ceiling: u32,
    holdings: &[Holding],
    stale: &[Stale],
    handle: &str,
) -> Option<Refusal> {
    if ceiling == 0 || holdings.len() < ceiling as usize {
        return None;
    }
    let mut msg = format!(
        "the repository is at its in-progress limit ({} of {ceiling}); taking {handle} would exceed [pm.wip] in_progress. Current holders:",
        holdings.len()
    );
    write_holders(&mut msg, holdings.iter());
    if !stale.is_empty() {
        msg.push_str("\nStale (in progress, lease expired; not counted):");
        for s in stale {
            let _ = write!(
                msg,
                "\n  {} {} - since {}; requeue it with: frob requeue {} --reason stale",
                s.handle, s.title, s.since, s.handle
            );
        }
    }
    let remedy = "finish or requeue one of the holders (frob requeue <ticket> --reason <why>), or raise [pm.wip] in_progress in frob.toml";
    Some(Refusal::new(CODE, RefusalClass::GuardNeedsAction, msg).with_remedy(remedy))
}

/// The slot request of one ticket: its id, handle and class of service.
#[derive(Debug, Clone, Copy)]
pub struct Taking<'a> {
    /// The ticket being taken.
    pub id: TicketId,
    /// Its handle with `~`.
    pub handle: &'a str,
    /// Its class of service.
    pub class: Class,
}

/// The two knobs of the WIP policy: `[pm.wip] in_progress` and `[pm.classes] expedite_max`; 0 turns either off.
#[derive(Debug, Clone, Copy)]
pub struct Limits {
    /// Repository-wide in-progress limit.
    pub repo: u32,
    /// Expedite tickets allowed at once.
    pub expedite_max: u32,
}

/// The in-progress tickets plus every ticket holding a live lease, so a holder that is mid-start (lease taken, transition not yet recorded) still counts.
fn holders(ledger: &Ledger, live: &[Lease], id: TicketId) -> Result<Vec<Summary>, WorktreeError> {
    let mut all = frob_pm::rules::wip::in_progress(ledger)?;
    for lease in live.iter().filter(|l| l.ticket != id) {
        if all.iter().any(|s| s.id == lease.ticket) {
            continue;
        }
        match ledger.show(lease.ticket) {
            Ok(view) if view.summary.category != Category::Done => {
                tracing::debug!(ticket = %lease.ticket, "live lease on a ticket not yet in progress counts as a holder");
                all.push(view.summary);
            }
            Ok(_) => tracing::debug!(ticket = %lease.ticket, "live lease on a done ticket ignored"),
            Err(LedgerError::NotFound { .. }) => {
                tracing::warn!(ticket = %lease.ticket, "live lease on an unknown ticket ignored");
            }
            Err(e) => return Err(e.into()),
        }
    }
    Ok(all)
}

/// Check that taking `taking` fits the WIP policy, given the `live` leases read under the lease-store lock.
///
/// Called from [`frob_lease::LeaseStore::acquire_admitting`], so the count and
/// the lease write are one critical section; the live leases (not the ledger's
/// in-progress state, which lags the lease) are the source of truth for holders.
///
/// An expedite ticket skips the repository limit while the lane has room
/// (`expedite_max` of 0 closes the lane: it is then treated like any ticket);
/// everyone else counts every live holder, expedite included.
///
/// # Errors
///
/// `E-WIP-EXPEDITE` when the lane is full, `E-WIP-REPO` naming every holder when the repository is at its limit; ledger and lease failures.
pub fn check(
    ledger: &Ledger,
    live: &[Lease],
    limits: Limits,
    taking: Taking<'_>,
) -> Result<(), WorktreeError> {
    let Taking { id, handle, class } = taking;
    let lane = class == Class::Expedite && limits.expedite_max > 0;
    if limits.repo == 0 && !lane {
        tracing::debug!(%id, "repository wip limit off");
        return Ok(());
    }
    let live_ids: BTreeSet<TicketId> = live.iter().map(|l| l.ticket).collect();
    let mut wip = frob_pm::rules::wip::count(
        holders(ledger, live, id)?,
        Some(&live_ids),
        limits.expedite_max,
    );
    for list in [&mut wip.standard, &mut wip.expedite, &mut wip.stale] {
        list.retain(|s| s.id != id);
    }
    let holding = |s: Summary| {
        let lease = live.iter().find(|l| l.ticket == s.id)?.clone();
        Some(Holding {
            handle: s.handle,
            title: s.title,
            lease,
            class: s.class,
        })
    };
    let holdings: Vec<Holding> = wip.standard.into_iter().filter_map(holding).collect();
    let expedite: Vec<Holding> = wip.expedite.into_iter().filter_map(holding).collect();
    let stale: Vec<Stale> = wip
        .stale
        .into_iter()
        .map(|s| Stale {
            handle: s.handle,
            title: s.title,
            since: s.updated,
        })
        .collect();
    tracing::debug!(%id, %class, repo = limits.repo, holders = holdings.len(), expedite = expedite.len(), stale = stale.len(), "repository wip counted");
    if lane {
        if let Some(r) = expedite_refusal(limits.expedite_max, &expedite, handle) {
            tracing::info!(%id, max = limits.expedite_max, "work refused: expedite lane full");
            return Err(WorktreeError::Refused(r));
        }
        tracing::info!(%id, "expedite ticket takes the lane, repository limit not applied");
        return Ok(());
    }
    match refusal(limits.repo, &holdings, &stale, handle) {
        Some(r) => {
            tracing::info!(%id, limit = limits.repo, holders = holdings.len(), "work refused: repository wip limit");
            Err(WorktreeError::Refused(r))
        }
        None => Ok(()),
    }
}
