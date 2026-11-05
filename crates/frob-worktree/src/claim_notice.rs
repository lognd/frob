//! Idle-window notices for live claims (`distributed-tickets.md` section 4.4): what the holder is told and what everyone else sees.
//!
//! Reads only this clone's observation file and the lease store: no fetch, no push, so it is cheap
//! enough to run at the end of any verb.

// frob:ticket 01M5DCZ3PVHP2ZNP9SVYFFQSVP

use frob_ledger::claim_window::{IdleStatus, holder_notice, others_notice};
use frob_ledger::model::Category;

use crate::activity::{ObservedClaims, observed_path};
use crate::error::WorktreeError;
use crate::next::{Assessed, EvictPolicy, claim_status};
use crate::work::Workspace;

/// One live claim's idle state and the lines it earns.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimNotice {
    /// Handle of the claimed ticket.
    pub handle: String,
    /// True when the current actor holds the claim.
    pub mine: bool,
    /// The idle clock as this clone sees it.
    pub status: IdleStatus,
    /// The line for the holder, `None` when the claim is quiet.
    pub holder_line: Option<String>,
    /// The rank the holder acknowledged, `None` for never or once the claim went quiet again.
    pub acked_rank: Option<usize>,
    /// The line for everybody else, `None` before the last warning fraction.
    pub others_line: Option<String>,
}

impl ClaimNotice {
    /// The line the current actor should see: the holder line on their own claims, the others line otherwise.
    #[must_use]
    pub fn line(&self) -> Option<&str> {
        if self.mine {
            self.status
                .needs_notice(self.acked_rank)
                .then_some(self.holder_line.as_deref())
                .flatten()
        } else {
            self.others_line.as_deref()
        }
    }
}

impl Workspace<'_> {
    /// The idle notice of every live in-progress claim, from this clone's observations alone.
    ///
    /// # Errors
    ///
    /// [`WorktreeError`] from the ledger or the lease store.
    // frob:ticket 01M5DCZ3PVHP2ZNP9SVYFFQSVP
    pub fn claim_idle_notices(
        &self,
        policy: &EvictPolicy,
    ) -> Result<Vec<ClaimNotice>, WorktreeError> {
        let (ws, ledger) = (self, self.ledger);
        let path = observed_path(ledger.repo());
        let mut observed = ObservedClaims::load(&path);
        let mut cleared = false;
        let now = ledger.clock().now().unix();
        let me = ledger.actor()?;
        let mut out = Vec::new();
        for lease in ws.leases.live_snapshot()? {
            if lease.queued {
                continue;
            }
            let view = ledger.show(lease.ticket)?;
            if view.summary.category != Category::InProgress {
                continue;
            }
            let key = lease.ticket.to_string();
            let events = ledger.events(lease.ticket)?;
            let record = ws.claim_record(&key)?;
            let pauses = Workspace::claim_pauses(&view, &lease, &events);
            let status = claim_status(
                &observed,
                &Assessed {
                    key: &key,
                    tip: "",
                    lease: &lease,
                    class: view.summary.class,
                    now,
                    policy,
                    record: &record,
                    events: &events,
                    pauses: &pauses,
                },
            );
            let handle = view.summary.handle.clone();
            let mut acked_rank = observed.claims.get(&key).and_then(|c| c.acked_rank);
            if acked_rank.is_some_and(|a| a > status.rank()) {
                // The claim went quiet again (a touch or push): the old acknowledgement must not mute the next climb.
                observed.set_acked_rank(&key, None);
                acked_rank = None;
                cleared = true;
            }
            tracing::debug!(%handle, rank = status.rank(), "claim idle notice assessed");
            out.push(ClaimNotice {
                mine: lease.holder.actor == me,
                holder_line: holder_notice(&handle, &status),
                others_line: others_notice(&handle, &status),
                acked_rank,
                handle,
                status,
            });
        }
        if cleared && let Err(e) = observed.save(&path) {
            tracing::warn!(error = %e, "stale claim acknowledgements could not be cleared");
        }
        tracing::info!(claims = out.len(), "claim idle notices built");
        Ok(out)
    }

    /// Acknowledge the current idle rank of every claim the actor holds, silencing their holder lines until a higher threshold; returns the claims acknowledged.
    ///
    /// # Errors
    ///
    /// [`WorktreeError`] from building the notices or writing the observation file.
    // frob:ticket 01M5DCZ3PVHP2ZNP9SVYFFQSVP
    pub fn ack_claim_notices(&self, policy: &EvictPolicy) -> Result<Vec<String>, WorktreeError> {
        let notices = self.claim_idle_notices(policy)?;
        let path = observed_path(self.ledger.repo());
        let mut observed = ObservedClaims::load(&path);
        let mut acked = Vec::new();
        for n in notices.iter().filter(|n| n.mine && n.holder_line.is_some()) {
            let Some(ticket) = self.ledger.resolve(&n.handle).ok().map(|t| t.to_string()) else {
                continue;
            };
            observed.set_acked_rank(&ticket, Some(n.status.rank()));
            acked.push(n.handle.clone());
        }
        observed.save(&path).map_err(WorktreeError::Config)?;
        tracing::info!(claims = acked.len(), "claim notices acknowledged");
        Ok(acked)
    }
}
