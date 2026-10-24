//! Bounded waiting for a scope change that another live lease blocks.
// frob:ticket 01M4HW9J243ZJRMVYW51K18GCM
//!
//! `ticket update --add-scope --wait SECS` and `lease widen --wait SECS` retry
//! [`LeaseStore::rescope`] while a different ticket's live lease overlaps the
//! new scope. Each attempt re-reads the lease directory under the lock, so a
//! holder that releases (or whose lease expires) mid-wait unblocks the caller on
//! the next poll. On expiry the first refusal is returned unchanged.

use std::time::{Duration, Instant};

use frob_ledger::TicketId;

use crate::{Holder, Lease, LeaseConfig, LeaseError, LeaseStore};

/// How often the blocking holder is reported while waiting.
pub const REPORT_EVERY: Duration = Duration::from_secs(10);

/// How often a blocked rescope is retried.
pub const POLL: Duration = Duration::from_millis(250);

impl LeaseStore {
    /// Rescope `holder`'s lease on `ticket`, waiting up to `wait` for overlapping leases to go away.
    ///
    /// `wait` of zero is a single attempt. Only an overlap with another ticket's lease
    /// is waited on; every other refusal returns at once. `on_wait` is called with the
    /// blocking error on the first block and then at most every [`REPORT_EVERY`].
    ///
    /// # Errors
    ///
    /// As [`LeaseStore::rescope`]; on timeout, the first [`LeaseError::Held`] seen.
    pub fn rescope_waiting(
        &self,
        ticket: TicketId,
        holder: &Holder,
        new_scope: &[String],
        cfg: &LeaseConfig,
        wait: Duration,
        mut on_wait: impl FnMut(&LeaseError),
    ) -> Result<Lease, LeaseError> {
        let start = Instant::now();
        let mut first: Option<LeaseError> = None;
        let mut last_report: Option<Instant> = None;
        loop {
            let err = match self.rescope(ticket, holder, new_scope, cfg) {
                Ok(l) => {
                    if first.is_some() {
                        tracing::info!(%ticket, waited = ?start.elapsed(), "wait over: lease rescoped");
                    }
                    return Ok(l);
                }
                Err(e) => e,
            };
            let blocked =
                matches!(&err, LeaseError::Held { ticket: other, .. } if *other != ticket);
            if !blocked || start.elapsed() >= wait {
                if blocked {
                    tracing::warn!(%ticket, waited = ?start.elapsed(), "wait expired: still blocked");
                }
                return Err(if blocked { first.unwrap_or(err) } else { err });
            }
            if last_report.is_none_or(|t| t.elapsed() >= REPORT_EVERY) {
                tracing::info!(%ticket, blocker = %err, "waiting for an overlapping lease");
                on_wait(&err);
                last_report = Some(Instant::now());
            }
            first.get_or_insert(err);
            std::thread::sleep(POLL.min(wait.saturating_sub(start.elapsed())));
        }
    }
}
