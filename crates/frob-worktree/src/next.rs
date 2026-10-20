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
use frob_ledger::guards::NoLeases;
use gob_diagnostics::{Refusal, RefusalClass};

use crate::claim::E_CLAIM_LOST;
use crate::cycle_gate::NOT_IN_CYCLE_CODE;
use crate::error::WorktreeError;
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
                .with_remedy("frob ticket doable"),
        ))
    }
}
