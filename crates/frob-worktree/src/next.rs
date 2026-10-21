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
use frob_ledger::claim_window::{ClaimWindows, HolderKind};
use frob_ledger::event::{EventBody, LeaseData, LeaseOp};
use frob_ledger::guards::NoLeases;
use frob_ledger::model::Category;
use gob_diagnostics::{Refusal, RefusalClass, RemedyCommand};

use crate::activity::{DEFAULT_BOT_IDENTITIES, ObservedClaims, commit_facts, observed_path};
use crate::claim::{E_CLAIM_LOST, remote_claim, sync_settings};
use crate::cycle_gate::NOT_IN_CYCLE_CODE;
use crate::error::WorktreeError;
use crate::evict::{
    EvictContext, EvictOutcome, EvictRequest, check_evictable, evict, evictions_today,
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

impl Workspace<'_> {
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
        let bots: Vec<String> = DEFAULT_BOT_IDENTITIES
            .iter()
            .map(|s| (*s).to_owned())
            .collect();
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
            let tracking = format!("refs/remotes/{remote}/{branch}");
            let refspec = format!("+refs/heads/{branch}:{tracking}");
            if !matches!(
                repo.fetch_refs(&remote, &[refspec], timeout)?,
                gob_git::RemoteRun::Done
            ) {
                tracing::warn!(%handle, "could not fetch the claim tip; skipping");
                continue;
            }
            let since = observed.claims.get(&key).and_then(|c| c.tip.clone());
            let commits =
                commit_facts(repo, &tip, since.as_deref()).map_err(WorktreeError::Config)?;
            observed.observe_tip(&key, &tip, &commits, &bots, now);
            let seen = observed.claims.get(&key);
            let soft = [
                seen.and_then(|c| c.soft.as_ref()).map(|s| s.first_seen),
                lease.touched_at.map(gob_time::Stamp::unix),
            ]
            .into_iter()
            .flatten()
            .max();
            let times = ActivityTimes {
                claim_start: lease.acquired_at.unix(),
                hard: seen.and_then(|c| c.hard.as_ref()).map(|s| s.first_seen),
                soft,
            };
            let obs = observation_for(
                &policy.windows,
                &times,
                HolderKind::Agent,
                view.summary.class,
                None,
            );
            let status = policy.windows.status(&obs, now, policy.utc_offset_secs);
            let ctx = EvictContext {
                online: true,
                window_secs: status.window_secs.and_then(|w| u64::try_from(w).ok()),
                idle_secs: u64::try_from(status.idle_secs).unwrap_or(0),
                held_or_paused: false,
                evictions_today: evictions_today(&observed.evictions, now, policy.utc_offset_secs),
                evict_rate: policy.windows.evict_rate(),
                since_reclaim_secs: None,
                in_ci: policy.in_ci,
            };
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
                        "claim evicted from {} after {}s idle; work parked at {parked} (frob work {handle} --from {parked})",
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
