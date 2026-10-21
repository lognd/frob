//! Local lands origin has not seen (distributed-tickets.md row 52, DT21): the count behind `refresh`'s one-line summary.
//!
//! After weeks offline the local base holds `land` events whose commits are not
//! on `<remote>/<base>`. [`diverged_lands`] finds them from the ledger and git
//! alone (no network); [`summary`] words them with the evicted-claim and
//! conflict counts. `frob land --relaunch ~X` is the repair for each.

use std::collections::BTreeSet;

use frob_ledger::event::{EventBody, LeaseOp};
use frob_ledger::index::ListFilter;
use frob_ledger::model::Category;
use frob_ledger::{Ledger, TicketId};

use crate::error::LandError;

/// A done ticket whose land commit is not on the remote base.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocalLand {
    /// The ticket.
    pub id: TicketId,
    /// Its handle, for messages.
    pub handle: String,
    /// The recorded land commit.
    pub commit: String,
}

/// What a reconnect has to say about the offline work (the three numbers of the row 52 summary).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Divergence {
    /// Lands origin's base does not contain.
    pub lands: Vec<LocalLand>,
    /// Tickets whose latest lease event is an eviction (their work is parked).
    pub evicted: usize,
    /// Ledger paths the last union could not resolve.
    pub conflicts: usize,
}

/// The done tickets whose last `land` commit is not an ancestor of `remote_base`, plus the evicted-claim count; empty when the ref is absent. `conflicts` is left 0 for the caller.
///
/// # Errors
///
/// Ledger and git read failures.
// frob:ticket 01M5DRXH9KKWX3W0A99VESJVC8
pub fn diverged_lands(ledger: &Ledger, remote_base: &str) -> Result<Divergence, LandError> {
    let repo = ledger.repo();
    if repo.rev_parse(remote_base).is_err() {
        tracing::debug!(
            remote_base,
            "no remote base ref; nothing to compare lands with"
        );
        return Ok(Divergence::default());
    }
    let all = ledger.list(&ListFilter::default())?;
    let ids: BTreeSet<TicketId> = all.iter().map(|s| s.id).collect();
    let events = ledger.events_many(&ids)?;
    let mut lands = Vec::new();
    let mut evicted = 0;
    for s in all {
        let evs = events.get(&s.id).map_or(&[][..], Vec::as_slice);
        let last_lease = evs.iter().rev().find_map(|e| match &e.body {
            EventBody::Lease(d) => Some(d.op),
            _ => None,
        });
        if last_lease == Some(LeaseOp::Evict) {
            evicted += 1;
        }
        if s.category != Category::Done {
            continue;
        }
        let Some(land) = evs.iter().rev().find_map(|e| match &e.body {
            EventBody::Land(d) => Some(d),
            _ => None,
        }) else {
            continue;
        };
        let Ok(commit) = repo.rev_parse(&land.commit) else {
            tracing::warn!(ticket = %s.handle, commit = %land.commit, "recorded land commit is not in this clone");
            continue;
        };
        if repo.merge_base(&land.commit, remote_base)? != Some(commit) {
            lands.push(LocalLand {
                id: s.id,
                handle: s.handle,
                commit: land.commit.clone(),
            });
        }
    }
    tracing::info!(
        lands = lands.len(),
        evicted,
        "local lands not on the remote base"
    );
    Ok(Divergence {
        lands,
        evicted,
        conflicts: 0,
    })
}

/// The row 52 line `N local lands not on origin; M claims evicted; K conflicts`, or `None` when all three are zero.
#[must_use]
// frob:ticket 01M5DRXH9KKWX3W0A99VESJVC8
pub fn summary(d: &Divergence, remote: &str) -> Option<String> {
    if d.lands.is_empty() && d.evicted == 0 && d.conflicts == 0 {
        return None;
    }
    Some(format!(
        "{} local lands not on {remote}; {} claims evicted; {} conflicts",
        d.lands.len(),
        d.evicted,
        d.conflicts
    ))
}
