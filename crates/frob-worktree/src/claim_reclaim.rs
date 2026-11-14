//! `frob work ~X --reclaim` and the returning holder's notice (`distributed-tickets.md` sections 4.6 and 4.7).
//!
//! The decisions are [`crate::evict::reclaim_plan`] (take the evicted work back)
//! and [`crate::evict::holder_return`] (the `W-CLAIM-EVICTED` warning and the
//! next parked ref). This module gathers their inputs from the remote, the
//! lease store and the ledger events, maps refusals to coded [`WorktreeError`]s,
//! and offers the notice scan `frob refresh` runs for the claims of this clone.

// frob:ticket 01M5DFKY6K8AH7K75XGTQMVAVA

use frob_lease::LeaseStore;
use frob_ledger::event::{Event, EventBody, LeaseOp};
use frob_ledger::{Ledger, TicketId};
use gob_diagnostics::{Refusal, RefusalClass, RemedyCommand};
use gob_time::Stamp;

use crate::claim::{remote_claim, sync_settings};
use crate::error::WorktreeError;
use crate::evict::{
    ParkRecord, ReclaimRefusal, RestoreOutcome, holder_return, parked_refs, reclaim_plan, restore,
};
use crate::work::{Started, WorkOptions, Workspace};

/// Refusal code when someone else holds the ticket, so the evicted work cannot be reclaimed.
pub const E_RECLAIM_TAKEN: &str = "E-RECLAIM-TAKEN";

/// Refusal code when no parked work exists for the ticket.
pub const E_RECLAIM_NOTHING: &str = "E-RECLAIM-NOTHING";

/// Refusal code when the remote cannot be reached; a reclaim needs it online.
pub const E_RECLAIM_OFFLINE: &str = "E-RECLAIM-OFFLINE";

/// The reason recorded on the `restore` event a reclaim writes.
const RECLAIM_REASON: &str = "reclaimed by work --reclaim";

/// The refusal for a [`ReclaimRefusal`] on `handle`.
fn plan_refusal(why: ReclaimRefusal, handle: &str) -> WorktreeError {
    match why {
        ReclaimRefusal::HeldBy(by) => WorktreeError::Refused(
            Refusal::new(
                E_RECLAIM_TAKEN,
                RefusalClass::GuardNeedsAction,
                format!("{handle} is held by {by} now; coordinate with them before reclaiming"),
            )
            .with_command(
                RemedyCommand::new("frob", "requeue")
                    .arg(handle)
                    .flag("reason", "<why>"),
            ),
        ),
        ReclaimRefusal::NothingParked => WorktreeError::Refused(
            Refusal::new(
                E_RECLAIM_NOTHING,
                RefusalClass::GuardNeedsAction,
                format!("{handle} has no parked work to reclaim"),
            )
            .with_command(RemedyCommand::new("frob", "work").arg(handle)),
        ),
    }
}

/// The refusal for an unreachable remote.
fn offline(handle: &str, why: &str) -> WorktreeError {
    WorktreeError::Refused(
        Refusal::new(
            E_RECLAIM_OFFLINE,
            RefusalClass::GuardNeedsAction,
            format!("cannot reclaim {handle} offline: {why}"),
        )
        .with_command(
            RemedyCommand::new("frob", "work")
                .arg(handle)
                .flag("reclaim", ""),
        ),
    )
}

/// The park record an `evict` event carries, `None` when `event` is not an eviction of a parked claim.
fn record_of(event: &Event, handle: &str) -> Option<ParkRecord> {
    let EventBody::Lease(l) = &event.body else {
        return None;
    };
    if l.op != LeaseOp::Evict {
        return None;
    }
    Some(ParkRecord {
        handle: handle.to_owned(),
        evictor: event.actor.clone(),
        holder: l.holder.clone()?,
        observed: l.observed.clone().unwrap_or_default(),
        idle_secs: l.idle_secs.unwrap_or(0),
        window_secs: l.window_secs.unwrap_or(0),
        reason: l.reason.clone().unwrap_or_default(),
    })
}

/// The newest eviction of `holder` after `acquired` that no `restore` or `reclaim` answered, with its time.
fn unanswered_eviction(
    events: &[Event],
    handle: &str,
    holder: &str,
    acquired: i64,
) -> Option<(Stamp, ParkRecord)> {
    let (stamp, record) = events
        .iter()
        .filter_map(|e| record_of(e, handle).map(|r| (e.at, r)))
        .max_by_key(|(at, _)| at.unix())?;
    let at = stamp.unix();
    if record.holder != holder || at < acquired {
        return None;
    }
    let answered = events.iter().any(|e| {
        matches!(&e.body, EventBody::Lease(l)
            if matches!(l.op, LeaseOp::Restore | LeaseOp::Reclaim) && e.at.unix() >= at)
    });
    if answered {
        tracing::debug!(
            handle,
            holder,
            "eviction already answered by restore or reclaim"
        );
        return None;
    }
    Some((stamp, record))
}

/// The parked ref names every `evict` event in `events` recorded, oldest first.
fn parked_names(events: &[Event]) -> Vec<String> {
    events
        .iter()
        .filter_map(|e| match &e.body {
            EventBody::Lease(l) if l.op == LeaseOp::Evict => l.parked.clone(),
            _ => None,
        })
        .collect()
}

/// The `W-CLAIM-EVICTED` notice for `holder` on a ticket whose claim began at `acquired`, from its `events`.
///
/// `None` unless the newest eviction names `holder`, came after `acquired`, and no `restore`
/// or `reclaim` followed it. The parked refs named by earlier evictions pick the next parked ref.
#[must_use]
pub fn return_notice(
    events: &[Event],
    handle: &str,
    holder: &str,
    acquired: i64,
) -> Option<String> {
    let bare = handle.trim_start_matches('~');
    let (stamp, record) = unanswered_eviction(events, bare, holder, acquired)?;
    let date = stamp.precise().chars().take(10).collect::<String>();
    let ret = holder_return(&record, &parked_names(events), &date);
    tracing::info!(handle, holder, push_to = %ret.push_to, "evicted holder returned");
    Some(ret.warning)
}

/// The `W-CLAIM-EVICTED` notices for every live claim of this clone whose holder was evicted since it began.
///
/// Best effort per claim: a ticket that cannot be read is logged and skipped.
///
/// # Errors
/// Lease store read failures.
// frob:ticket 01M5DFKY6K8AH7K75XGTQMVAVA
pub fn holder_return_notices(
    ledger: &Ledger,
    leases: &LeaseStore,
) -> Result<Vec<String>, WorktreeError> {
    let mut out = Vec::new();
    for lease in leases.live_snapshot()? {
        let id: TicketId = lease.ticket;
        let handle = match ledger.show(id) {
            Ok(v) => v.summary.handle,
            Err(e) => {
                tracing::debug!(ticket = %id, error = %e, "return notice skipped: ticket unreadable");
                continue;
            }
        };
        let events = match ledger.events(id) {
            Ok(e) => e,
            Err(e) => {
                tracing::debug!(ticket = %id, error = %e, "return notice skipped: events unreadable");
                continue;
            }
        };
        let acquired = lease.acquired_at.unix();
        if let Some(n) = return_notice(&events, &handle, &lease.holder.actor, acquired) {
            out.push(n);
        }
    }
    tracing::info!(notices = out.len(), "holder return scan done");
    Ok(out)
}

impl Workspace<'_> {
    /// `work ~X --reclaim`: put the newest parked work back as `ticket/<handle>` and claim the ticket over it.
    ///
    /// Refuses while someone else holds the ticket or nothing is parked. When the claim branch
    /// already exists on the remote the restore is skipped and `work` proceeds.
    ///
    /// # Errors
    /// [`E_RECLAIM_TAKEN`], [`E_RECLAIM_NOTHING`] and [`E_RECLAIM_OFFLINE`] refusals, plus the
    /// refusals, ledger, lease and git failures of [`Workspace::work`].
    // frob:ticket 01M5DFKY6K8AH7K75XGTQMVAVA
    pub fn work_reclaiming(
        &self,
        ticket: &str,
        opts: &WorkOptions,
    ) -> Result<Started, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        let handle = self.ledger.show(id)?.summary.handle;
        let bare = handle.trim_start_matches('~');
        let actor = self.ledger.actor()?;
        let other = self
            .leases
            .live_lease(id)?
            .map(|l| l.holder.actor)
            .filter(|a| *a != actor);
        let repo = self.ledger.repo();
        let (remote, timeout) = sync_settings(repo);
        let parked =
            parked_refs(repo, &remote, bare, timeout)?.map_err(|why| offline(&handle, &why))?;
        let name = reclaim_plan(other.as_deref(), &parked, bare)
            .map_err(|why| plan_refusal(why, &handle))?;
        let present = remote_claim(repo, &remote, &format!("ticket/{bare}"), timeout)?
            .map_err(|why| offline(&handle, &why))?
            .is_some();
        if present {
            tracing::info!(ticket = %id, "reclaim: claim branch already on the remote; skipping restore");
        } else {
            match restore(repo, bare, &name)? {
                RestoreOutcome::Restored { tip } => {
                    self.ledger.append(
                        id,
                        crate::claim_restore::restore_event(&name, &tip, RECLAIM_REASON),
                    )?;
                    tracing::info!(ticket = %id, parked = %name, "reclaim: parked work restored");
                }
                RestoreOutcome::Taken => {
                    tracing::warn!(ticket = %id, "reclaim: another clone created the claim first");
                }
                RestoreOutcome::Offline(why) => return Err(offline(&handle, &why)),
            }
        }
        self.work(ticket, opts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_ledger::event::LeaseData;

    fn lease_ev(
        at: i64,
        actor: &str,
        op: LeaseOp,
        holder: Option<&str>,
        parked: Option<&str>,
    ) -> Event {
        Event::new(
            Stamp::from_unix(at),
            actor,
            EventBody::Lease(LeaseData {
                op,
                holder: holder.map(str::to_owned),
                observed: Some("abc".to_owned()),
                parked: parked.map(str::to_owned),
                tip: None,
                idle_secs: Some(172_800),
                window_secs: Some(86_400),
                reason: Some("idle".to_owned()),
                clone_id: None,
                agent: None,
                branch: None,
            }),
        )
    }

    // frob:tests crates/frob-worktree/src/claim_reclaim.rs::plan_refusal
    #[test]
    fn refusals_carry_their_codes() {
        let code = |why| match plan_refusal(why, "~X") {
            WorktreeError::Refused(r) => r.code.clone(),
            other => other.to_string(),
        };
        assert_eq!(code(ReclaimRefusal::NothingParked), E_RECLAIM_NOTHING);
        assert_eq!(code(ReclaimRefusal::HeldBy("b".into())), E_RECLAIM_TAKEN);
    }

    // frob:tests crates/frob-worktree/src/claim_reclaim.rs::return_notice
    #[test]
    fn notice_names_the_next_parked_ref_for_the_evicted_holder() {
        let events = [lease_ev(
            1_000,
            "bob",
            LeaseOp::Evict,
            Some("ann"),
            Some("parked/X-1"),
        )];
        let n = return_notice(&events, "~X", "ann", 500).expect("notice");
        assert!(n.contains("W-CLAIM-EVICTED"), "{n}");
        assert!(n.contains("parked/X-2"), "{n}");
        assert!(n.contains("evicted by bob"), "{n}");
    }

    // frob:tests crates/frob-worktree/src/claim_reclaim.rs::return_notice
    #[test]
    fn notice_is_absent_for_other_holders_old_evictions_and_answered_ones() {
        let evict = lease_ev(
            1_000,
            "bob",
            LeaseOp::Evict,
            Some("ann"),
            Some("parked/X-1"),
        );
        assert!(return_notice(std::slice::from_ref(&evict), "~X", "carl", 500).is_none());
        assert!(return_notice(std::slice::from_ref(&evict), "~X", "ann", 2_000).is_none());
        let back = lease_ev(1_500, "ann", LeaseOp::Reclaim, Some("ann"), None);
        assert!(return_notice(&[evict, back], "~X", "ann", 500).is_none());
        assert!(return_notice(&[], "~X", "ann", 0).is_none());
    }

    // frob:tests crates/frob-worktree/src/claim_reclaim.rs::record_of
    #[test]
    fn record_of_reads_only_evictions() {
        let evict = lease_ev(1, "bob", LeaseOp::Evict, Some("ann"), Some("parked/X-1"));
        let rec = record_of(&evict, "X").expect("record");
        assert_eq!((rec.holder.as_str(), rec.evictor.as_str()), ("ann", "bob"));
        assert!(record_of(&lease_ev(1, "bob", LeaseOp::Restore, None, None), "X").is_none());
    }
}
