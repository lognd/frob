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

/// Append a `land` event to ticket `id` and commit it on the ledger ref; returns the ledger commit.
///
/// # Errors
///
/// Ledger lookup, fold, git or format failures.
pub fn append_land(ledger: &Ledger, id: TicketId, body: &LandEvent<'_>) -> Result<Oid, LandError> {
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
