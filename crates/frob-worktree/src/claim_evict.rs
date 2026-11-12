//! `frob claim evict ~X --reason TEXT [--yes]`: end an idle claim by hand (`distributed-tickets.md` sections 4.5 and 4.7).
//!
//! The decision is [`crate::evict::check_evictable`] plus the flap review
//! ([`crate::evict::flap_review`]); the push is [`crate::evict::evict`]. This
//! module gathers the inputs (remote tip, this clone's own idle observation,
//! the day's eviction count, earlier evictions of the holder on the ticket),
//! maps every refusal to a coded [`WorktreeError`], reports the remaining
//! daily `evict_rate`, and records the eviction on the ticket.

// frob:ticket 01M5DTGG9XWMEBRA51PA6CYWAE

use frob_ledger::TicketId;
use frob_ledger::claim_window::{EVICT_NOTE_MARKER, HolderKind};
use frob_ledger::event::{Event, EventBody, LeaseData, LeaseOp};
use frob_ledger::model::Category;
use gob_diagnostics::{Refusal, RefusalClass, RemedyCommand};

use crate::activity::{ObservedClaims, observed_path};
use crate::claim::{remote_claim, sync_settings};
use crate::error::WorktreeError;
use crate::evict::{
    EvictOutcome, EvictRefusal, EvictRequest, FlapReview, ParkRecord, check_evictable, evict,
    flap_review, needs_completion, newest_parked, parked_refs, rate_left, read_park_record,
};
use crate::next::{Assessed, EvictPolicy, assess_claim, fetch_claim_tip};
use crate::work::Workspace;

/// Refusal code when the ticket has no live in-progress claim to evict.
pub const E_EVICT_NO_CLAIM: &str = "E-EVICT-NO-CLAIM";

/// Refusal code when a repeat eviction of the same holder needs `--yes`.
pub const E_EVICT_CONFIRM: &str = "E-CLAIM-CONFIRM";

/// Refusal code when the holder pushed after this clone's observation.
pub const E_EVICT_ACTIVE: &str = "E-CLAIM-ACTIVE";

/// Refusal code when another evictor got there first.
pub const E_EVICT_GONE: &str = "E-EVICT-GONE";

/// What a successful eviction did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvictedClaim {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The previous holder.
    pub holder: String,
    /// The `parked/<handle>-<n>` ref preserving the holder's work.
    pub parked: String,
    /// Idle seconds this clone measured.
    pub idle_secs: u64,
    /// Evictions this actor may still perform today.
    pub rate_left: u32,
    /// The eviction repeated one of the same holder inside the flap window and was confirmed.
    pub flapped: bool,
}

/// The coded refusal for a failed [`check_evictable`] precondition on `handle`.
fn precondition_refusal(why: EvictRefusal, handle: &str) -> WorktreeError {
    let (code, text) = why.describe();
    WorktreeError::Refused(
        Refusal::new(
            code,
            RefusalClass::GuardNeedsAction,
            format!("cannot evict {handle}: {text}"),
        )
        .with_remedy("wait for the window and the daily rate, or leave the claim alone"),
    )
}

/// The refusal for an unreachable remote: eviction never happens offline.
fn offline_refusal(handle: &str, why: &str) -> WorktreeError {
    let (code, text) = EvictRefusal::Offline.describe();
    WorktreeError::Refused(
        Refusal::new(
            code,
            RefusalClass::GuardNeedsAction,
            format!("cannot evict {handle}: {text} ({why})"),
        )
        .with_command(
            RemedyCommand::new("frob", "claim evict")
                .arg(handle)
                .flag("reason", "<why>"),
        ),
    )
}

/// The transition reason recording that `holder`'s claim was evicted.
fn note_body(holder: &str, idle_secs: u64, parked: &str, handle: &str, reason: &str) -> String {
    format!(
        "{EVICT_NOTE_MARKER}{holder} after {idle_secs}s idle: {reason}; work parked at {parked} (frob work {handle} --from {parked})"
    )
}

/// The `lease` op `evict` event body recording `record`'s eviction into `parked`.
fn evict_event(record: &ParkRecord, parked: &str) -> EventBody {
    EventBody::Lease(LeaseData {
        op: LeaseOp::Evict,
        holder: Some(record.holder.clone()),
        observed: Some(record.observed.clone()),
        parked: Some(parked.to_owned()),
        tip: None,
        idle_secs: Some(record.idle_secs),
        window_secs: Some(record.window_secs),
        reason: Some(record.reason.clone()),
        clone_id: None,
        agent: None,
        branch: None,
    })
}

/// Ages in seconds at `now` of the earlier evictions of `holder` recorded in `events`.
#[must_use]
pub fn prior_eviction_ages(events: &[Event], holder: &str, now: i64) -> Vec<u64> {
    let prefix = format!("{EVICT_NOTE_MARKER}{holder} ");
    events
        .iter()
        .filter_map(|e| match &e.body {
            EventBody::Transition(t)
                if t.reason.as_deref().is_some_and(|r| r.starts_with(&prefix)) =>
            {
                Some(u64::try_from(now.saturating_sub(e.at.unix())).unwrap_or(0))
            }
            _ => None,
        })
        .collect()
}

impl Workspace<'_> {
    /// Write the ledger side of an eviction: the `lease` op `evict` event, then in-progress to todo with a note naming the previous holder.
    fn record_eviction(
        &self,
        id: TicketId,
        handle: &str,
        record: &ParkRecord,
        parked: &str,
        reason: &str,
    ) -> Result<(), WorktreeError> {
        self.ledger.append(id, evict_event(record, parked))?;
        let note = note_body(&record.holder, record.idle_secs, parked, handle, reason);
        self.ledger
            .transition(id, Category::Todo, None, Some(note))?;
        tracing::info!(ticket = %id, holder = %record.holder, %parked, "eviction recorded");
        Ok(())
    }

    /// Finish an eviction that crashed between the claim delete and the ledger record.
    ///
    /// Recognises "in progress, branch absent, parked ref present" ([`needs_completion`]),
    /// reads the park commit ([`read_park_record`]), releases any lease and records the
    /// eviction. Returns the parked ref when it completed one, `None` when nothing was pending.
    ///
    /// # Errors
    /// Ledger, lease and git failures,.
    // frob:ticket 01M5DFKY3FZKR6EWYR83J8MJQ7
    pub fn complete_crashed_eviction(&self, ticket: &str) -> Result<Option<String>, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        let view = self.ledger.show(id)?;
        let handle = view.summary.handle.clone();
        let in_progress = view.summary.category == Category::InProgress;
        let bare = handle.trim_start_matches('~');
        let repo = self.ledger.repo();
        let (remote, timeout) = sync_settings(repo);
        let branch_present = match remote_claim(repo, &remote, &format!("ticket/{bare}"), timeout)?
        {
            Ok(tip) => tip.is_some(),
            Err(why) => {
                tracing::debug!(%handle, %why, "crash completion skipped: remote unreachable");
                return Ok(None);
            }
        };
        let parked = match parked_refs(repo, &remote, bare, timeout)? {
            Ok(refs) => refs,
            Err(why) => {
                tracing::debug!(%handle, %why, "crash completion skipped: parked refs unknown");
                return Ok(None);
            }
        };
        if !needs_completion(in_progress, branch_present, &parked, bare) {
            return Ok(None);
        }
        let Some(full) = newest_parked(&parked, bare) else {
            return Ok(None);
        };
        let short = full.strip_prefix("refs/heads/").unwrap_or(full).to_owned();
        let local = format!("refs/remotes/{remote}/{short}");
        let refspec = format!("+refs/heads/{short}:{local}");
        if !matches!(
            repo.fetch_refs(&remote, &[refspec], timeout)?,
            gob_git::RemoteRun::Done
        ) {
            tracing::warn!(%handle, parked = %short, "crash completion skipped: park fetch failed");
            return Ok(None);
        }
        let Some(record) = read_park_record(repo, &local)? else {
            tracing::warn!(%handle, parked = %short, "crash completion skipped: no park record");
            return Ok(None);
        };
        self.leases.release(id, None)?;
        let reason = format!(
            "{} (completed after a crash; evicted by {})",
            record.reason, record.evictor
        );
        self.record_eviction(id, &handle, &record, &short, &reason)?;
        tracing::info!(ticket = %id, parked = %short, "crashed eviction completed");
        Ok(Some(short))
    }

    /// Evict the idle in-progress claim of `ticket` for `reason`, park its work and return the ticket to todo.
    ///
    /// A repeat eviction of the same holder inside the flap window needs `yes`.
    ///
    /// # Errors
    /// A usage error without a reason; [`E_EVICT_NO_CLAIM`], [`E_EVICT_CONFIRM`],
    /// [`E_EVICT_ACTIVE`], [`E_EVICT_GONE`] and the `check_evictable` refusals;
    /// ledger, lease and git failures.
    // frob:ticket 01M5DTGG9XWMEBRA51PA6CYWAE
    pub fn evict_claim(
        &self,
        ticket: &str,
        reason: &str,
        yes: bool,
        policy: &EvictPolicy,
    ) -> Result<EvictedClaim, WorktreeError> {
        self.evict_claim_confirming(ticket, reason, policy, &mut |_| yes)
    }

    /// [`Self::evict_claim`] with a confirmation callback in place of `--yes`.
    ///
    /// `confirm` receives the one-line question when a human holder or a repeat eviction needs a
    /// human to confirm; `true` proceeds, `false` refuses with [`E_EVICT_CONFIRM`].
    ///
    /// # Errors
    /// Same as [`Self::evict_claim`].
    // frob:ticket 01M5DZJ99WRFPNK6WS3KZWDC0G
    #[allow(clippy::too_many_lines)]
    pub fn evict_claim_confirming(
        &self,
        ticket: &str,
        reason: &str,
        policy: &EvictPolicy,
        confirm: &mut dyn FnMut(&str) -> bool,
    ) -> Result<EvictedClaim, WorktreeError> {
        if reason.trim().is_empty() {
            return Err(WorktreeError::Usage(
                "claim evict needs a non-empty --reason".to_owned(),
            ));
        }
        let id = self.ledger.resolve(ticket)?;
        let view = self.ledger.show(id)?;
        let handle = view.summary.handle.clone();
        let no_claim = |text: &str| {
            WorktreeError::Refused(
                Refusal::new(
                    E_EVICT_NO_CLAIM,
                    RefusalClass::GuardNeedsAction,
                    format!("cannot evict {handle}: {text}"),
                )
                .with_remedy("only an in-progress ticket with a live claim can be evicted"),
            )
        };
        let Some(lease) = self.leases.live_lease(id)? else {
            return Err(no_claim("no live lease"));
        };
        if view.summary.category != Category::InProgress {
            return Err(no_claim("the ticket is not in progress"));
        }
        let bare = handle.trim_start_matches('~');
        let branch = format!("ticket/{bare}");
        let repo = self.ledger.repo();
        let (remote, timeout) = sync_settings(repo);
        let offline = |why: &str| offline_refusal(&handle, why);
        let tip = match remote_claim(repo, &remote, &branch, timeout)? {
            Ok(Some(tip)) => tip,
            Ok(None) => return Err(no_claim("no claim branch on the remote")),
            Err(why) => return Err(offline(&why)),
        };
        if !fetch_claim_tip(repo, &remote, &branch, timeout)? {
            return Err(offline("could not fetch the claim tip"));
        }
        let path = observed_path(repo);
        let mut observed = ObservedClaims::load(&path);
        let now = self.ledger.clock().now().unix();
        let key = id.to_string();
        let record = self.note_reclaim(id, &lease, now)?;
        let events = self.ledger.events(id)?;
        let ctx = assess_claim(
            repo,
            &mut observed,
            &Assessed {
                key: &key,
                tip: &tip,
                lease: &lease,
                class: view.summary.class,
                ticket_days: view.ticket.front.claim_idle_days,
                now,
                policy,
                record: &record,
                events: &events,
                pauses: &Self::claim_pauses(&view, &lease, &events),
            },
        )?;
        let today = ctx.evictions_today;
        let holder = lease.holder.actor.clone();
        let checked = check_evictable(&ctx);
        // The observation is this clone's evidence; keep it even when the eviction is refused.
        if let Err(e) = observed.save(&path) {
            tracing::warn!(error = %e, "could not save the observation file");
        }
        checked.map_err(|why| precondition_refusal(why, &handle))?;
        let ages = prior_eviction_ages(&self.ledger.events(id)?, &holder, now);
        let flap_days = policy.windows.flap_repeat_days();
        let flapped = flap_review(&ages, flap_days) == FlapReview::NeedsHuman;
        let confirm_human =
            lease.holder_kind() == HolderKind::Human && !policy.windows.evict_human_auto();
        let needs_confirm = flapped || confirm_human;
        let confirmed = needs_confirm && {
            let question = format!("Evict {holder}'s claim on {handle}?");
            let ok = confirm(&question);
            tracing::info!(%holder, flapped, confirm_human, ok, "claim evict confirmation asked");
            ok
        };
        if needs_confirm && !confirmed {
            let why = if flapped {
                format!(
                    "was already evicted in the last {flap_days} days; a repeat needs a human to confirm"
                )
            } else {
                "is held by a human and `[claims] evict_human = \"confirm\"`".to_owned()
            };
            tracing::info!(%holder, flapped, confirm_human, "claim evict needs confirmation");
            return Err(WorktreeError::Refused(
                Refusal::new(
                    E_EVICT_CONFIRM,
                    RefusalClass::GuardNeedsAction,
                    format!("{holder}'s claim on {handle} {why}"),
                )
                .with_command(
                    RemedyCommand::new("frob", "claim evict")
                        .arg(handle)
                        .flag("reason", "<why>")
                        .switch("yes"),
                ),
            ));
        }
        let req = EvictRequest {
            handle: bare.to_owned(),
            holder: holder.clone(),
            evictor: self.ledger.actor()?,
            observed: tip,
            idle_secs: ctx.idle_secs,
            window_secs: ctx.window_secs.unwrap_or(0),
            reason: reason.to_owned(),
        };
        match evict(repo, &req)? {
            EvictOutcome::Evicted { parked } => {
                observed.evictions.push(now);
                observed.claims.remove(&key);
                if let Err(e) = observed.save(&path) {
                    tracing::warn!(error = %e, "could not save the observation file");
                }
                self.leases.release(id, None)?;
                let parked_record = ParkRecord {
                    handle: bare.to_owned(),
                    evictor: req.evictor.clone(),
                    holder: holder.clone(),
                    observed: req.observed.clone(),
                    idle_secs: ctx.idle_secs,
                    window_secs: req.window_secs,
                    reason: reason.to_owned(),
                };
                self.record_eviction(id, &handle, &parked_record, &parked, reason)?;
                let left = rate_left(ctx.evict_rate, today + 1);
                tracing::info!(ticket = %id, %holder, %parked, left, flapped, "claim evicted");
                Ok(EvictedClaim {
                    id,
                    handle,
                    holder,
                    parked,
                    idle_secs: ctx.idle_secs,
                    rate_left: left,
                    flapped,
                })
            }
            EvictOutcome::Active { tip } => Err(WorktreeError::Refused(
                Refusal::new(
                    E_EVICT_ACTIVE,
                    RefusalClass::GuardNeedsAction,
                    format!(
                        "{holder} pushed {tip} to {handle} since this clone looked; not evicted"
                    ),
                )
                .with_remedy("rerun later: the idle clock restarts from the new push"),
            )),
            EvictOutcome::AlreadyEvicted => Err(WorktreeError::Refused(
                Refusal::new(
                    E_EVICT_GONE,
                    RefusalClass::GuardNeedsAction,
                    format!("another clone already evicted {handle}"),
                )
                .with_command(RemedyCommand::new("frob", "work").arg(handle)),
            )),
            EvictOutcome::Offline(why) => Err(offline(&why)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_ledger::event::TransitionData;
    use gob_time::Stamp;

    fn ev(at: i64, reason: Option<&str>) -> Event {
        Event {
            id: "01M5DYSEK61W37DS2C48FYT158".parse().unwrap(),
            at: Stamp::from_unix(at),
            rev: 1,
            actor: "x".to_owned(),
            kind: "transition".to_owned(),
            body: EventBody::Transition(TransitionData {
                from: Category::InProgress,
                to: Category::Todo,
                outcome: None,
                reason: reason.map(str::to_owned),
            }),
        }
    }

    // frob:tests crates/frob-worktree/src/claim_evict.rs::evict_event
    #[test]
    fn evict_event_names_holder_and_parked_ref() {
        let rec = ParkRecord {
            handle: "X".to_owned(),
            evictor: "bob".to_owned(),
            holder: "alice".to_owned(),
            observed: "abc".to_owned(),
            idle_secs: 7,
            window_secs: 9,
            reason: "away".to_owned(),
        };
        let EventBody::Lease(d) = evict_event(&rec, "parked/X-1") else {
            panic!("not a lease event");
        };
        assert_eq!(d.op, LeaseOp::Evict);
        assert_eq!(d.holder.as_deref(), Some("alice"));
        assert_eq!(d.parked.as_deref(), Some("parked/X-1"));
        assert_eq!(d.idle_secs, Some(7));
    }

    // frob:tests prior_eviction_ages
    #[test]
    fn prior_ages_count_only_this_holders_evictions() {
        let mine = note_body("agent-a", 10, "parked/X-1", "~X", "idle");
        let theirs = note_body("agent-b", 10, "parked/X-1", "~X", "idle");
        let events = [
            ev(1_000, Some(&mine)),
            ev(2_000, Some(&theirs)),
            ev(3_000, Some("requeued")),
            ev(4_000, None),
        ];
        assert_eq!(prior_eviction_ages(&events, "agent-a", 10_000), vec![9_000]);
        assert!(prior_eviction_ages(&events, "nobody", 10_000).is_empty());
    }

    // frob:tests precondition_refusal
    #[test]
    fn preconditions_keep_their_describe_codes() {
        match precondition_refusal(EvictRefusal::RateLimited, "~X") {
            WorktreeError::Refused(r) => assert_eq!(r.code, "E-CLAIM-RATE"),
            other => panic!("unexpected {other}"),
        }
    }
}
