//! Evidence as ledger events: append and read `evidence` events of one ticket.
//!
//! `frob-ledger` folds every kind it does not interpret to a no-change
//! [`frob_ledger::event::EventBody::Other`], which would drop the payload, so
//! this module writes the event file itself (envelope plus the record's own
//! keys), re-folds the ticket so `ticket.md` stays equal to the fold (its
//! `updated` stamp moves with every event), and commits both through
//! `gob_git::Repo::commit_paths` on the ledger ref, exactly as the ledger does.

use frob_ledger::event::{EVENT_REV, Event};
use frob_ledger::model::Stamp;
use frob_ledger::{EventId, Ledger, TicketId, doc, fold};
use gob_git::{CommitOptions, Oid, RelPath};
use serde::Serialize;

use crate::error::{EvidenceError, Result};
use crate::record::EvidenceRecord;

/// The event `kind` of a measurement.
pub const KIND_EVIDENCE: &str = "evidence";
/// The event `kind` recording a `--no-evidence --reason` close bypass.
pub const KIND_BYPASS: &str = "evidence-bypass";

/// An evidence event read back from the ledger.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct StoredEvidence {
    /// The event id.
    pub event: String,
    /// When the event was written.
    pub at: String,
    /// Who wrote it.
    pub actor: String,
    /// The record.
    pub record: EvidenceRecord,
}

/// A committed evidence event.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Appended {
    /// The new event's id.
    pub event: EventId,
    /// The ledger commit that holds it.
    pub commit: Oid,
}

#[derive(Serialize)]
struct Envelope<'a> {
    kind: &'a str,
    at: Stamp,
    actor: &'a str,
    rev: u32,
}

#[derive(Serialize)]
struct Bypass<'a> {
    reason: &'a str,
}

/// Envelope first (so `kind` leads the file), then the body's own keys.
fn render(kind: &str, actor: &str, body: &impl Serialize) -> Result<String> {
    let envelope = Envelope {
        kind,
        at: Stamp::now(),
        actor,
        rev: EVENT_REV,
    };
    let mut text =
        toml::to_string(&envelope).map_err(|e| EvidenceError::Malformed(e.to_string()))?;
    text.push_str(&toml::to_string(body).map_err(|e| EvidenceError::Malformed(e.to_string()))?);
    Ok(text)
}

fn commit(ledger: &Ledger, id: TicketId, verb: &str, text: &str) -> Result<Appended> {
    let view = ledger.show(id)?;
    let ref_name = ledger.ledger_ref()?;
    let tip = ledger
        .tip()?
        .ok_or_else(|| EvidenceError::Malformed("the ledger ref has no commits".to_owned()))?;
    let event = Event::parse(EventId::mint(), text)?;
    let event_id = event.id;
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
            Some(text.as_bytes().to_vec()),
        ),
    ];
    let message = format!(
        "tickets({verb}): {} {}",
        view.summary.handle, ticket.front.title
    );
    let opts = CommitOptions {
        cas_retries: ledger.config().cas_retries,
        author: None,
    };
    let out = ledger
        .repo()
        .commit_paths(&ref_name, &changes, &message, &opts)?;
    tracing::info!(verb, ticket = %id, event = %event_id, commit = %out.oid, "evidence event committed");
    Ok(Appended {
        event: event_id,
        commit: out.oid,
    })
}

/// Append `record` to ticket `id` as an `evidence` event.
///
/// # Errors
///
/// Ledger lookup (`E-TICKET-NOT-FOUND`), fold, git or format failures.
pub fn append(ledger: &Ledger, id: TicketId, record: &EvidenceRecord) -> Result<Appended> {
    let actor = ledger.actor()?;
    let text = render(KIND_EVIDENCE, &actor, record)?;
    commit(ledger, id, "evidence", &text)
}

/// Record that closing `id` bypassed the evidence guard, with the reason given.
///
/// # Errors
///
/// As [`append`].
pub fn append_bypass(ledger: &Ledger, id: TicketId, reason: &str) -> Result<Appended> {
    let actor = ledger.actor()?;
    let text = render(KIND_BYPASS, &actor, &Bypass { reason })?;
    commit(ledger, id, "evidence-bypass", &text)
}

/// Every evidence event of ticket `id` at the ledger tip, in fold order.
///
/// # Errors
///
/// Ledger, git or format failures; an evidence event whose body does not parse is an error.
pub fn list(ledger: &Ledger, id: TicketId) -> Result<Vec<StoredEvidence>> {
    let Some(tip) = ledger.tip()? else {
        return Ok(Vec::new());
    };
    let tip = tip.to_string();
    let dir = &ledger.config().dir;
    let mut out = Vec::new();
    for event in ledger.read_events_at(&tip, id)? {
        if event.kind != KIND_EVIDENCE {
            continue;
        }
        let path = format!("{dir}/{id}/events/{}", event.file_name());
        let bytes = ledger
            .repo()
            .read_blob_at(&tip, &path)?
            .ok_or_else(|| EvidenceError::Malformed(format!("{path} is listed but unreadable")))?;
        let text = String::from_utf8(bytes)
            .map_err(|_| EvidenceError::Malformed(format!("{path} is not UTF-8")))?;
        let mut table: toml::Table = text
            .parse()
            .map_err(|e: toml::de::Error| EvidenceError::Malformed(format!("{path}: {e}")))?;
        for key in ["kind", "at", "actor", "rev"] {
            table.remove(key);
        }
        let record: EvidenceRecord = table
            .try_into()
            .map_err(|e: toml::de::Error| EvidenceError::Malformed(format!("{path}: {e}")))?;
        out.push(StoredEvidence {
            event: event.id.to_string(),
            at: event.at.to_string(),
            actor: event.actor,
            record,
        });
    }
    tracing::debug!(ticket = %id, count = out.len(), "evidence listed");
    Ok(out)
}
