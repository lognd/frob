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
use frob_ledger::event::{Event, EventBody};
use frob_ledger::model::Category;
use gob_diagnostics::{Refusal, RefusalClass};

use crate::activity::{ObservedClaims, observed_path};
use crate::claim::{remote_claim, sync_settings};
use crate::error::WorktreeError;
use crate::evict::{
    EvictOutcome, EvictRefusal, EvictRequest, FlapReview, check_evictable, evict, flap_review,
    rate_left,
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
        .with_remedy("reconnect and rerun `frob claim evict`"),
    )
}

/// The transition reason recording that `holder`'s claim was evicted.
fn note_body(holder: &str, idle_secs: u64, parked: &str, handle: &str, reason: &str) -> String {
    format!(
        "{EVICT_NOTE_MARKER}{holder} after {idle_secs}s idle: {reason}; work parked at {parked} (frob work {handle} --from {parked})"
    )
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
                events: &self.ledger.events(id)?,
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
        let flapped = flap_review(&ages) == FlapReview::NeedsHuman;
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
                    "was already evicted in the last {} days; a repeat needs a human to confirm",
                    crate::evict::FLAP_REPEAT_DAYS
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
                .with_remedy(format!(
                    "rerun `frob claim evict {handle} --reason <why> --yes` to confirm"
                )),
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
                let note = note_body(&holder, ctx.idle_secs, &parked, &handle, reason);
                self.ledger
                    .transition(id, Category::Todo, None, Some(note))?;
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
                .with_remedy("refresh with `frob ticket show` and claim it with `frob work`"),
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
