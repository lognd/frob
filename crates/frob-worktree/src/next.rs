//! `frob work --next`: pick the best doable ticket and claim it in one step, retrying on a lost race (`distributed-tickets.md` section 3.3, scenarios 23 and 31).
//!
//! Each attempt is an ordinary [`Workspace::work`], whose create-only claim
//! push is the atomic step. A candidate somebody else took first (lost claim,
//! held or queued lease, no longer workable, outside the sprint) is skipped for
//! this call and the next candidate in `doable` order is tried; anything else
//! (an overdue cycle, a WIP limit, git failures) ends the call because every
//! candidate would fail the same way.

// frob:ticket 01M5CW05BZQR83F5SJTQEH8MRN

use std::collections::HashSet;

use frob_ledger::TicketId;
use frob_ledger::claim_agent::{ActivityTimes, observation_for};
use frob_ledger::claim_hold::ClaimRecord;
use frob_ledger::claim_window::{ClaimWindows, EVICT_NOTE_MARKER, HolderKind};
use frob_ledger::event::{Event, EventBody, LeaseData, LeaseOp};
use frob_ledger::guards::NoLeases;
use frob_ledger::model::Category;
use gob_diagnostics::{Refusal, RefusalClass, RemedyCommand};

use crate::activity::{DEFAULT_BOT_IDENTITIES, ObservedClaims, commit_facts, observed_path};
use crate::claim::{E_CLAIM_LOST, remote_claim, sync_settings};
use crate::cycle_gate::NOT_IN_CYCLE_CODE;
use crate::error::WorktreeError;
use crate::evict::{
    EvictContext, EvictOutcome, EvictRequest, check_evictable, evict, evictions_today,
    since_reclaim,
};
use crate::work::{Started, WorkOptions, Workspace};

/// Refusal code when `work --next` found no ticket it could claim.
pub const E_NO_DOABLE: &str = "E-NO-DOABLE-TICKET";

/// Most candidates one `work --next` tries before giving up.
pub const MAX_ATTEMPTS: usize = 8;

/// Refusal codes that mean "this candidate is taken or unsuitable, try the next".
const SKIPPABLE: [&str; 5] = [
    E_CLAIM_LOST,
    "E-LEASE-HELD",
    "E-LEASE-QUEUED",
    "E-TICKET-NOT-WORKABLE",
    NOT_IN_CYCLE_CODE,
];

/// True when a refusal with `code` only rules out one candidate, so `work --next` moves on.
#[must_use]
pub fn is_skippable(code: &str) -> bool {
    SKIPPABLE.contains(&code)
}

/// Fetch the claim branch tip into its remote-tracking ref; false when the fetch did not complete.
// frob:ticket 01M5DZJ96SRX543SR1N51DGJH0
pub(crate) fn fetch_claim_tip(
    repo: &gob_git::Repo,
    remote: &str,
    branch: &str,
    timeout: std::time::Duration,
) -> Result<bool, WorktreeError> {
    let refspec = format!("+refs/heads/{branch}:refs/remotes/{remote}/{branch}");
    Ok(matches!(
        repo.fetch_refs(remote, &[refspec], timeout)?,
        gob_git::RemoteRun::Done
    ))
}

/// One claim's inputs to [`assess_claim`].
pub(crate) struct Assessed<'a> {
    /// Observation-file key (the full ticket id).
    pub key: &'a str,
    /// The claim branch tip just fetched.
    pub tip: &'a str,
    /// The live lease on the ticket.
    pub lease: &'a frob_lease::Lease,
    /// The ticket's class, which picks the idle window.
    pub class: frob_ledger::model::Class,
    /// Current unix time.
    pub now: i64,
    /// The eviction policy.
    pub policy: &'a EvictPolicy,
    /// The ticket's hold and reclaim record.
    pub record: &'a ClaimRecord,
    /// The ticket's ledger events, whose holder-written soft activity counts.
    pub events: &'a [Event],
}

/// Record this clone's observation of a claim tip and build the [`EvictContext`] judging its idleness.
// frob:ticket 01M5DZJ96SRX543SR1N51DGJH0
pub(crate) fn assess_claim(
    repo: &gob_git::Repo,
    observed: &mut ObservedClaims,
    a: &Assessed<'_>,
) -> Result<EvictContext, WorktreeError> {
    let bots: Vec<String> = DEFAULT_BOT_IDENTITIES
        .iter()
        .map(|s| (*s).to_owned())
        .collect();
    let since = observed.claims.get(a.key).and_then(|c| c.tip.clone());
    let commits = commit_facts(repo, a.tip, since.as_deref()).map_err(WorktreeError::Config)?;
    observed.observe_tip(a.key, a.tip, &commits, &bots, a.now);
    for event in a.events {
        observed.observe_event(a.key, event, &a.lease.holder.actor, a.now);
    }
    let seen = observed.claims.get(a.key);
    let soft = [
        seen.and_then(|c| c.soft.as_ref()).map(|s| s.first_seen),
        a.lease.touched_at.map(gob_time::Stamp::unix),
    ]
    .into_iter()
    .flatten()
    .max();
    let times = ActivityTimes {
        claim_start: a.lease.acquired_at.unix(),
        hard: seen.and_then(|c| c.hard.as_ref()).map(|s| s.first_seen),
        soft,
    };
    let windows = &a.policy.windows;
    let obs = observation_for(windows, &times, a.lease.holder_kind(), a.class, None);
    let status = windows.status(&obs, a.now, a.policy.utc_offset_secs);
    Ok(EvictContext {
        online: true,
        window_secs: status.window_secs.and_then(|w| u64::try_from(w).ok()),
        idle_secs: u64::try_from(status.idle_secs).unwrap_or(0),
        held_or_paused: a.record.held_at(a.now),
        evictions_today: evictions_today(&observed.evictions, a.now, a.policy.utc_offset_secs),
        evict_rate: windows.evict_rate(),
        since_reclaim_secs: since_reclaim(a.record.reclaimed_at, a.now),
        in_ci: a.policy.in_ci,
    })
}

/// True when `holder` (claiming since `acquired`) is the holder re-creating a claim that was evicted from it and not yet recorded as reclaimed.
fn is_unrecorded_reclaim(
    events: &[Event],
    record: &ClaimRecord,
    holder: &str,
    acquired: i64,
) -> bool {
    let last_evict = events
        .iter()
        .filter_map(|e| match &e.body {
            EventBody::Lease(l) if l.op == LeaseOp::Evict => {
                Some((e.at.unix(), l.holder.as_deref()))
            }
            _ => None,
        })
        .max_by_key(|(at, _)| *at);
    last_evict.is_some_and(|(at, evicted)| {
        evicted == Some(holder) && acquired >= at && record.reclaimed_at.is_none_or(|r| r < at)
    })
}

impl Workspace<'_> {
    /// The claim record of `id`, first recording a reclaim when the evicted holder has re-pushed its claim.
    // frob:ticket 01M5E1MXHT9FNMKTH8EAYDK1H2
    pub(crate) fn note_reclaim(
        &self,
        id: TicketId,
        lease: &frob_lease::Lease,
        now: i64,
    ) -> Result<ClaimRecord, WorktreeError> {
        let key = id.to_string();
        let mut record = self.claim_record(&key)?;
        if is_unrecorded_reclaim(
            &self.ledger.events(id)?,
            &record,
            &lease.holder.actor,
            lease.acquired_at.unix(),
        ) {
            self.record_reclaim(&key, &lease.holder.actor)?;
            record.reclaimed_at = Some(now);
        }
        Ok(record)
    }

    /// Claim the first doable ticket that `work` accepts, trying at most `max_attempts` candidates.
    ///
    /// The `doable` order is the shared comparator (class, priority, age).
    /// Waiting for a blocked scope is disabled per candidate: a blocked one is
    /// skipped instead.
    ///
    /// # Errors
    ///
    /// [`E_NO_DOABLE`] when no candidate could be claimed; the first
    /// non-skippable refusal or failure from `work` otherwise.
    pub fn work_next(
        &self,
        opts: &WorkOptions,
        max_attempts: usize,
    ) -> Result<Started, WorktreeError> {
        let per_candidate = WorkOptions {
            wait_secs: 0,
            ..opts.clone()
        };
        let mut skipped: HashSet<TicketId> = HashSet::new();
        let mut lost = Vec::new();
        for attempt in 1..=max_attempts {
            let candidate = self
                .ledger
                .doable(&NoLeases)?
                .into_iter()
                .find(|s| !skipped.contains(&s.id));
            let Some(candidate) = candidate else { break };
            tracing::info!(attempt, ticket = %candidate.id, "work --next: trying candidate");
            match self.work(&candidate.handle, &per_candidate) {
                Ok(started) => return Ok(started),
                Err(WorktreeError::Refused(r)) if is_skippable(&r.code) => {
                    tracing::warn!(attempt, ticket = %candidate.id, code = %r.code, "work --next: candidate unavailable; trying the next");
                    skipped.insert(candidate.id);
                    lost.push(format!("{} ({})", candidate.handle, r.code));
                }
                Err(e) => return Err(e),
            }
        }
        tracing::warn!(tried = lost.len(), "work --next: nothing claimable");
        let message = if lost.is_empty() {
            "no doable ticket is available to claim".to_owned()
        } else {
            format!("every doable ticket tried was taken: {}", lost.join(", "))
        };
        Err(WorktreeError::Refused(
            Refusal::new(E_NO_DOABLE, RefusalClass::GuardRetryByWaiting, message)
                .with_command(RemedyCommand::new("frob", "ticket doable")),
        ))
    }
}

/// What `work --next` needs to evict an idle agent claim (`[claims] evict_agent = "auto"`).
// frob:ticket 01M5DJW52ZBQRYN9ZSTGSJJYF3
#[derive(Debug, Clone)]
pub struct EvictPolicy {
    /// The `[claims]` windows, `evict_agent` and `evict_rate`.
    pub windows: ClaimWindows,
    /// Offset of the local timezone from UTC, for the daily eviction count.
    pub utc_offset_secs: i64,
    /// True when running in CI, where eviction never happens.
    pub in_ci: bool,
}

/// A claim `work --next` evicted to make room for itself.
// frob:ticket 01M5DJW52ZBQRYN9ZSTGSJJYF3
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Evicted {
    /// Handle of the evicted ticket.
    pub handle: String,
    /// The previous holder.
    pub holder: String,
    /// The parked ref that preserves the holder's work.
    pub parked: String,
}

impl Workspace<'_> {
    /// [`Workspace::work_next`], and when nothing is claimable and the policy allows it, evict one idle agent claim and claim that ticket.
    ///
    /// # Errors
    ///
    /// As [`Workspace::work_next`]; eviction trouble is logged and ends in the
    /// original [`E_NO_DOABLE`] refusal.
    // frob:ticket 01M5DJW52ZBQRYN9ZSTGSJJYF3
    pub fn work_next_evicting(
        &self,
        opts: &WorkOptions,
        max_attempts: usize,
        policy: Option<&EvictPolicy>,
    ) -> Result<Started, WorktreeError> {
        let first = self.work_next(opts, max_attempts);
        let (Err(WorktreeError::Refused(r)), Some(policy)) = (&first, policy) else {
            return first;
        };
        if r.code != E_NO_DOABLE || !policy.windows.evict_agent_auto() {
            return first;
        }
        match self.evict_one_idle_agent(policy) {
            Ok(Some(done)) => {
                tracing::info!(handle = %done.handle, holder = %done.holder, parked = %done.parked, "work --next: evicted an idle agent claim");
                self.work_next(opts, max_attempts)
            }
            Ok(None) => first,
            Err(e) => {
                tracing::warn!(error = %e, "work --next: eviction failed; reporting nothing claimable");
                first
            }
        }
    }

    /// Evict the first agent-held in-progress claim whose idle window has elapsed, if any qualifies.
    ///
    /// Preconditions are those of `check_evictable`: online, window elapsed
    /// by this clone's own observation, under `evict_rate`, not in CI.
    ///
    /// # Errors
    ///
    /// [`WorktreeError`] from the ledger, the lease store or git.
    // frob:ticket 01M5DJW52ZBQRYN9ZSTGSJJYF3
    #[allow(clippy::too_many_lines)]
    pub fn evict_one_idle_agent(
        &self,
        policy: &EvictPolicy,
    ) -> Result<Option<Evicted>, WorktreeError> {
        let repo = self.ledger.repo();
        let (remote, timeout) = sync_settings(repo);
        let path = observed_path(repo);
        let mut observed = ObservedClaims::load(&path);
        let now = self.ledger.clock().now().unix();
        let evictor = self.ledger.actor()?;
        for lease in self.leases.live_snapshot()? {
            if lease.queued || lease.holder_kind() != HolderKind::Agent {
                continue;
            }
            let view = self.ledger.show(lease.ticket)?;
            if view.summary.category != Category::InProgress {
                continue;
            }
            let handle = view.summary.handle.clone();
            let branch = format!("ticket/{}", handle.trim_start_matches('~'));
            let tip = match remote_claim(repo, &remote, &branch, timeout)? {
                Ok(Some(tip)) => tip,
                Ok(None) => {
                    tracing::debug!(%handle, "no remote claim; not evictable");
                    continue;
                }
                Err(why) => {
                    tracing::warn!(%why, "remote unreachable; eviction never happens offline");
                    return Ok(None);
                }
            };
            let key = lease.ticket.to_string();
            if !fetch_claim_tip(repo, &remote, &branch, timeout)? {
                tracing::warn!(%handle, "could not fetch the claim tip; skipping");
                continue;
            }
            let record = self.note_reclaim(lease.ticket, &lease, now)?;
            let ctx = assess_claim(
                repo,
                &mut observed,
                &Assessed {
                    key: &key,
                    tip: &tip,
                    lease: &lease,
                    class: view.summary.class,
                    now,
                    policy,
                    record: &record,
                    events: &self.ledger.events(lease.ticket)?,
                },
            )?;
            if let Err(refusal) = check_evictable(&ctx) {
                tracing::debug!(%handle, refusal = ?refusal, "claim not evictable");
                continue;
            }
            let req = EvictRequest {
                handle: handle.trim_start_matches('~').to_owned(),
                holder: lease.holder.actor.clone(),
                evictor: evictor.clone(),
                observed: tip,
                idle_secs: ctx.idle_secs,
                window_secs: ctx.window_secs.unwrap_or(0),
                reason: "idle agent claim evicted by work --next".to_owned(),
            };
            match evict(repo, &req)? {
                EvictOutcome::Evicted { parked } => {
                    observed.evictions.push(now);
                    observed.claims.remove(&key);
                    if let Err(e) = observed.save(&path) {
                        tracing::warn!(error = %e, "could not save the observation file");
                    }
                    self.leases.release(lease.ticket, None)?;
                    self.ledger.append(
                        lease.ticket,
                        EventBody::Lease(LeaseData {
                            op: LeaseOp::Evict,
                            holder: Some(lease.holder.actor.clone()),
                            observed: Some(req.observed.clone()),
                            parked: Some(parked.clone()),
                            tip: None,
                            idle_secs: Some(ctx.idle_secs),
                            window_secs: Some(req.window_secs),
                            reason: Some(req.reason.clone()),
                        }),
                    )?;
                    let note = format!(
                        "{EVICT_NOTE_MARKER}{} after {}s idle; work parked at {parked} (frob work {handle} --from {parked})",
                        lease.holder.actor, ctx.idle_secs
                    );
                    self.ledger
                        .transition(lease.ticket, Category::Todo, None, Some(note))?;
                    return Ok(Some(Evicted {
                        handle,
                        holder: lease.holder.actor,
                        parked,
                    }));
                }
                other => tracing::info!(%handle, outcome = ?other, "eviction did not happen"),
            }
        }
        if let Err(e) = observed.save(&path) {
            tracing::warn!(error = %e, "could not save the observation file");
        }
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_ledger::claim_hold::reclaim_event;
    use gob_time::Stamp;

    fn lease_ev(at: i64, body: EventBody) -> Event {
        Event {
            id: "01M5DYSEK61W37DS2C48FYT158".parse().unwrap(),
            at: Stamp::from_unix(at),
            rev: 1,
            actor: "x".to_owned(),
            kind: "lease".to_owned(),
            body,
        }
    }

    fn evict_body(holder: &str) -> EventBody {
        EventBody::Lease(LeaseData {
            op: LeaseOp::Evict,
            holder: Some(holder.to_owned()),
            observed: None,
            parked: None,
            tip: None,
            idle_secs: None,
            window_secs: None,
            reason: None,
        })
    }

    // frob:tests is_unrecorded_reclaim
    #[test]
    fn reclaim_needs_the_evicted_holder_after_the_eviction() {
        let events = [lease_ev(100, evict_body("agent-a"))];
        let none = ClaimRecord::default();
        assert!(is_unrecorded_reclaim(&events, &none, "agent-a", 150));
        assert!(!is_unrecorded_reclaim(&events, &none, "agent-b", 150));
        assert!(!is_unrecorded_reclaim(&events, &none, "agent-a", 50));
        assert!(!is_unrecorded_reclaim(&[], &none, "agent-a", 150));
        let done = [events[0].clone(), lease_ev(120, reclaim_event("agent-a"))];
        let rec = frob_ledger::claim_hold::fold_claim_record(&done);
        assert!(!is_unrecorded_reclaim(&done, &rec, "agent-a", 150));
    }
}
