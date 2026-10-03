//! Evidence as ledger events: append and read `evidence` events of one ticket.
//!
//! The ledger owns the event kinds ([`frob_ledger::event::EventBody::Evidence`]
//! and `EvidenceBypass`) and [`Ledger::append`] writes, re-folds and commits;
//! this module only converts between [`EvidenceRecord`] and the event body.

use frob_ledger::event::{Event, EventBody, EvidenceBypassData, EvidenceData};
use frob_ledger::{Applied, EventId, Ledger, TicketId};
use gob_git::Oid;
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

/// Split a record into the ledger's `accepts` plus the record's remaining keys.
fn to_data(record: &EvidenceRecord) -> Result<EvidenceData> {
    let mut table = toml::Table::try_from(record)
        .map_err(|e| EvidenceError::Malformed(format!("rendering the record: {e}")))?;
    table.remove("accepts");
    Ok(EvidenceData {
        accepts: record.accepts.clone(),
        record: table,
    })
}

/// Rebuild the record an `evidence` event carries.
fn to_record(event: &Event, data: &EvidenceData) -> Result<EvidenceRecord> {
    let mut table = data.record.clone();
    if !data.accepts.is_empty() {
        let accepts = data
            .accepts
            .iter()
            .map(|n| i64::try_from(*n).map(toml::Value::Integer))
            .collect::<std::result::Result<Vec<_>, _>>()
            .map_err(|e| EvidenceError::Malformed(format!("event {}: {e}", event.id)))?;
        table.insert("accepts".to_owned(), toml::Value::Array(accepts));
    }
    table
        .try_into()
        .map_err(|e: toml::de::Error| EvidenceError::Malformed(format!("event {}: {e}", event.id)))
}

fn appended(applied: &Applied, what: &str) -> Result<Appended> {
    let event = applied
        .events
        .first()
        .copied()
        .ok_or_else(|| EvidenceError::Malformed(format!("the {what} event was not written")))?;
    let commit = applied
        .commit
        .ok_or_else(|| EvidenceError::Malformed(format!("the {what} event was not committed")))?;
    tracing::info!(event = %event, commit = %commit, what, "evidence event committed");
    Ok(Appended { event, commit })
}

/// Append `record` to ticket `id` as an `evidence` event.
///
/// # Errors
///
/// Ledger lookup (`E-TICKET-NOT-FOUND`), fold, git or format failures.
pub fn append(ledger: &Ledger, id: TicketId, record: &EvidenceRecord) -> Result<Appended> {
    let applied = ledger.append(id, EventBody::Evidence(to_data(record)?))?;
    appended(&applied, KIND_EVIDENCE)
}

/// Record that closing `id` bypassed the evidence guard, with the reason given.
///
/// # Errors
///
/// As [`append`].
pub fn append_bypass(ledger: &Ledger, id: TicketId, reason: &str) -> Result<Appended> {
    let body = EventBody::EvidenceBypass(EvidenceBypassData {
        reason: reason.to_owned(),
    });
    let applied = ledger.append(id, body)?;
    appended(&applied, KIND_BYPASS)
}

/// Every evidence event of ticket `id` at the ledger tip, in fold order.
///
/// # Errors
///
/// Ledger, git or format failures; an evidence event whose body does not parse is an error.
pub fn list(ledger: &Ledger, id: TicketId) -> Result<Vec<StoredEvidence>> {
    let mut out = Vec::new();
    for event in ledger.events(id)? {
        let EventBody::Evidence(data) = &event.body else {
            continue;
        };
        let record = to_record(&event, data)?;
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
