//! The close guard: code-changing tickets need measured evidence (tickets.md section 3 and 9).

use frob_ledger::guards::{CloseContext, CloseGuard, GuardFailure};
use frob_ledger::model::TicketType;
use frob_ledger::{Ledger, TicketId};

use crate::error::Result as EvResult;
use crate::events::{self, Appended};
use crate::record::EvidenceRecord;
use crate::store::BlobStore;

/// Stable code of the refusal.
pub const CODE_MISSING: &str = "E-EVIDENCE-MISSING";

/// Ticket types whose close needs evidence; docs, chores and epics do not.
pub const CODE_CHANGING: &[TicketType] = &[
    TicketType::Task,
    TicketType::Bug,
    TicketType::Security,
    TicketType::Story,
    TicketType::Incident,
    TicketType::Invariant,
];

/// Requires at least one measured, non-failing evidence record to close a code-changing ticket.
#[derive(Debug, Clone, Default)]
pub struct EvidenceGuard {
    measured: usize,
    bypass: Option<String>,
}

impl EvidenceGuard {
    /// A guard that has seen `records`, judging each against `store` (a missing blob does not count).
    pub fn from_records(records: &[EvidenceRecord], store: &BlobStore) -> Self {
        let measured = records.iter().filter(|r| r.satisfies_close(store)).count();
        tracing::debug!(records = records.len(), measured, "evidence guard loaded");
        Self {
            measured,
            bypass: None,
        }
    }

    /// A guard loaded with the evidence events of ticket `id`.
    ///
    /// # Errors
    ///
    /// Ledger, git or format failures reading the events.
    pub fn for_ticket(ledger: &Ledger, store: &BlobStore, id: TicketId) -> EvResult<Self> {
        let records: Vec<EvidenceRecord> = events::list(ledger, id)?
            .into_iter()
            .map(|s| s.record)
            .collect();
        Ok(Self::from_records(&records, store))
    }

    /// Let the close through without evidence (`--no-evidence --reason <why>`).
    #[must_use]
    pub fn allow_bypass(mut self, reason: impl Into<String>) -> Self {
        let reason = reason.into();
        tracing::warn!(%reason, "evidence guard bypass requested");
        self.bypass = Some(reason);
        self
    }

    /// The bypass reason, when one was set.
    pub fn bypass_reason(&self) -> Option<&str> {
        self.bypass.as_deref()
    }

    /// How many measured records the guard counted.
    pub fn measured(&self) -> usize {
        self.measured
    }

    /// Write the bypass as an `evidence-bypass` event on `id`; `None` when no bypass was set.
    ///
    /// Call it once the close has succeeded so the audit trail matches what happened.
    ///
    /// # Errors
    ///
    /// Ledger, git or format failures.
    pub fn record_bypass(&self, ledger: &Ledger, id: TicketId) -> EvResult<Option<Appended>> {
        self.bypass
            .as_deref()
            .map(|reason| events::append_bypass(ledger, id, reason))
            .transpose()
    }
}

impl CloseGuard for EvidenceGuard {
    fn name(&self) -> &'static str {
        "has_evidence"
    }

    fn check(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        let ty = cx.ticket.front.ty;
        if !CODE_CHANGING.contains(&ty) {
            return Ok(());
        }
        if self.measured > 0 || self.bypass.is_some() {
            return Ok(());
        }
        Err(GuardFailure {
            code: CODE_MISSING.to_owned(),
            message: format!(
                "closing {} ({ty}) needs at least one measured evidence record; \
                 run `frob test --base <ref>` or `frob ticket evidence add {} --provider nextest --ref <filter>`",
                cx.handle, cx.handle
            ),
            remedy: Some("frob test --base <ref>".to_owned()),
        })
    }
}
