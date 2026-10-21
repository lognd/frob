//! Persisting claim holds and reclaims (`distributed-tickets.md` section 4.7, DT14): `lease` ops `hold`, `resume` and `reclaim`.
//!
//! The rules are [`frob_ledger::claim_hold`]; this module appends the events and reads them back as a
//! [`ClaimRecord`], which `work --next` and `claim evict` use for `held_or_paused` and `since_reclaim_secs`.

// frob:ticket 01M5E0F8MC9XT2PCCB9XG6E8X3

use frob_ledger::claim_hold::{
    ClaimRecord, Hold, fold_claim_record, hold_event, reclaim_event, resume_event,
};
use frob_ledger::claim_window::ClaimWindows;
use gob_time::Day;

use crate::error::WorktreeError;
use crate::work::Workspace;

impl Workspace<'_> {
    /// The hold and reclaim record of `ticket`, folded from its `lease` events.
    ///
    /// # Errors
    /// Ledger failures, including an unknown ticket.
    pub fn claim_record(&self, ticket: &str) -> Result<ClaimRecord, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        Ok(fold_claim_record(&self.ledger.events(id)?))
    }

    /// Record a hold on `ticket` until the end of `until` (zone `utc_offset_secs` east of UTC).
    ///
    /// # Errors
    /// A usage error for an empty reason, a past date or a hold past `max_hold_days`; ledger failures.
    pub fn hold_claim(
        &self,
        ticket: &str,
        until: Day,
        reason: &str,
        now: i64,
        utc_offset_secs: i64,
        windows: &ClaimWindows,
    ) -> Result<Hold, WorktreeError> {
        let hold = Hold::new(now, until, reason, utc_offset_secs, windows)
            .map_err(|e| WorktreeError::Usage(e.to_string()))?;
        let id = self.ledger.resolve(ticket)?;
        self.ledger.append(id, hold_event(&hold))?;
        tracing::info!(ticket = %id, until = %until, "claim hold recorded");
        Ok(hold)
    }

    /// End the active hold on `ticket` early; a ticket with no active hold is left alone and `false` returned.
    ///
    /// # Errors
    /// Ledger failures.
    pub fn resume_claim(&self, ticket: &str, now: i64) -> Result<bool, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        let record = fold_claim_record(&self.ledger.events(id)?);
        if !record.held_at(now) {
            tracing::debug!(ticket = %id, "claim resume: no active hold");
            return Ok(false);
        }
        self.ledger.append(id, resume_event())?;
        tracing::info!(ticket = %id, "claim resume recorded");
        Ok(true)
    }

    /// Record that `holder` re-created the evicted claim on `ticket` by pushing its branch.
    ///
    /// # Errors
    /// Ledger failures.
    pub fn record_reclaim(&self, ticket: &str, holder: &str) -> Result<(), WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        self.ledger.append(id, reclaim_event(holder))?;
        tracing::info!(ticket = %id, holder, "claim reclaim recorded");
        Ok(())
    }
}
