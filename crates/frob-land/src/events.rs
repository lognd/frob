//! The `land` ledger event: written beside the ticket's other events, committed on the ledger ref.
//!
//! The ledger owns the kind ([`frob_ledger::event::EventBody::Land`]) and
//! [`Ledger::append`] writes, re-folds and commits; this only builds the body.

use frob_ledger::event::{EventBody, LandData};
use frob_ledger::{Ledger, TicketId};
use gob_git::Oid;

use crate::error::LandError;

/// The event `kind` recording a land.
pub const KIND_LAND: &str = "land";

/// The body of a `land` event.
#[derive(Debug, Clone)]
pub struct LandEvent<'a> {
    /// Full name of the ref that advanced.
    pub base_ref: &'a str,
    /// The commit the base ref was advanced to.
    pub commit: &'a str,
    /// The ticket branch that was landed.
    pub branch: &'a str,
    /// Whether the base branch was pushed.
    pub pushed: bool,
}

/// True when ticket `id` already carries a `land` event for the same ref, commit and branch as `body`.
///
/// # Errors
///
/// Ledger lookup or fold failures.
pub(crate) fn land_recorded(
    ledger: &Ledger,
    id: TicketId,
    body: &LandEvent<'_>,
) -> Result<bool, LandError> {
    Ok(ledger.events(id)?.iter().any(|e| {
        matches!(&e.body, EventBody::Land(d)
            if d.base_ref == body.base_ref && d.commit == body.commit && d.branch == body.branch)
    }))
}

/// Append a `land` event to ticket `id` and commit it on the ledger ref; returns the ledger commit.
///
/// Idempotent: an identical earlier `land` event (same ref, commit and branch) is kept and the ledger tip returned.
///
/// # Errors
///
/// Ledger lookup, fold, git or format failures.
pub fn append_land(ledger: &Ledger, id: TicketId, body: &LandEvent<'_>) -> Result<Oid, LandError> {
    // frob:ticket 01M4CXTP6NCCZ7YNQCER0RXNYF
    // A retry after a failed close must not record the same land twice.
    if land_recorded(ledger, id, body)? {
        tracing::info!(ticket = %id, commit = body.commit, "land event already recorded; not appending again");
        return Ok(ledger.repo().rev_parse(&ledger.ledger_ref()?)?);
    }
    let applied = ledger.append(
        id,
        EventBody::Land(LandData {
            base_ref: body.base_ref.to_owned(),
            commit: body.commit.to_owned(),
            branch: body.branch.to_owned(),
            pushed: body.pushed,
        }),
    )?;
    let commit = applied
        .commit
        .ok_or_else(|| LandError::Config("the land event was not committed".to_owned()))?;
    tracing::info!(ticket = %id, kind = KIND_LAND, commit = %commit, "land event committed");
    Ok(commit)
}
