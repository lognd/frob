//! The `land` ledger event: written beside the ticket's other events, committed on the ledger ref.
//!
//! `frob-ledger` folds kinds it does not interpret to a no-change event, so
//! (like `frob-evidence` does for evidence) this writes the event file with
//! its own keys, re-folds the ticket so `ticket.md` keeps equalling the fold,
//! and commits both through `commit_paths`.

use frob_ledger::event::{EVENT_REV, Event};
use frob_ledger::model::Stamp;
use frob_ledger::{EventId, Ledger, TicketId, doc, fold};
use gob_git::{CommitOptions, Oid, RelPath};
use serde::Serialize;

use crate::error::LandError;

/// The event `kind` recording a land.
pub const KIND_LAND: &str = "land";

/// The body of a `land` event.
#[derive(Debug, Clone, Serialize)]
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

#[derive(Serialize)]
struct Envelope<'a> {
    kind: &'a str,
    at: Stamp,
    actor: &'a str,
    rev: u32,
}

/// Append a `land` event to ticket `id` and commit it on the ledger ref; returns the ledger commit.
///
/// # Errors
///
/// Ledger lookup, fold, git or format failures.
pub fn append_land(ledger: &Ledger, id: TicketId, body: &LandEvent<'_>) -> Result<Oid, LandError> {
    let actor = ledger.actor()?;
    let fmt = |e: toml::ser::Error| LandError::Config(format!("rendering the land event: {e}"));
    let mut text = toml::to_string(&Envelope {
        kind: KIND_LAND,
        at: Stamp::now(),
        actor: &actor,
        rev: EVENT_REV,
    })
    .map_err(fmt)?;
    text.push_str(&toml::to_string(body).map_err(fmt)?);

    let view = ledger.show(id)?;
    let ref_name = ledger.ledger_ref()?;
    let tip = ledger
        .tip()?
        .ok_or_else(|| LandError::Config("the ledger ref has no commits".to_owned()))?;
    let event = Event::parse(EventId::mint(), &text)?;
    let mut all = ledger.read_events_at(&tip.to_string(), id)?;
    all.push(event.clone());
    let ticket = fold::fold(id, &all)?.ticket;
    let dir = &ledger.config().dir;
    let changes = vec![
        (
            RelPath::new(format!("{dir}/{id}/ticket.md"))?,
            Some(doc::render(&ticket)?.into_bytes()),
        ),
        (
            RelPath::new(format!("{dir}/{id}/events/{}", event.file_name()))?,
            Some(text.into_bytes()),
        ),
    ];
    let message = format!(
        "tickets(land): {} {}",
        view.summary.handle, ticket.front.title
    );
    let opts = CommitOptions {
        cas_retries: ledger.config().cas_retries,
        author: None,
    };
    let out = ledger
        .repo()
        .commit_paths(&ref_name, &changes, &message, &opts)?;
    tracing::info!(ticket = %id, event = %event.id, commit = %out.oid, "land event committed");
    Ok(out.oid)
}
