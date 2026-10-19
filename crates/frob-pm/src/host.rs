//! The host the `PM` rules judge: the ledger plus the `[pm]` knobs and the lease facts a product supplies.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use std::collections::BTreeSet;

use frob_ledger::guards::LeaseCheck;
use frob_ledger::{Ledger, LedgerHost, TicketId, evaluation_failed};
use gob_rules::Finding;

use crate::config::PmConfig;
use crate::eval::apply_strict;

/// A product that can answer the questions the `PM` rules ask beyond the ledger itself.
pub trait PmHost: LedgerHost {
    /// The `[pm]` configuration of the repository, or why it could not be read.
    ///
    /// # Errors
    ///
    /// The config load failure rendered as text.
    fn pm_config(&self) -> Result<PmConfig, String>;

    /// Ticket ids holding a live lease (the liveness input of `PM013`); `None` when the lease store cannot be read.
    fn live_leases(&self) -> Option<BTreeSet<TicketId>>;

    /// The lease check `PM033` counts doable tickets under; every ticket is free when no store can be opened.
    fn lease_check(&self) -> Box<dyn LeaseCheck + '_>;
}

/// Run one `PM` rule body over the host's ledger and apply `[pm] strict` to what it reports.
///
/// An unreadable ledger or a failing body becomes the rule's required Unresolved finding, never zero findings.
pub fn relay_pm<H: ?Sized + PmHost>(
    host: &H,
    rule: &str,
    body: impl FnOnce(&Ledger) -> Result<Vec<Finding>, String>,
) -> Vec<Finding> {
    let found = match host.ledger_view().open(rule) {
        Err(finding) => vec![finding],
        Ok(None) => return Vec::new(),
        Ok(Some(ledger)) => body(ledger).unwrap_or_else(|e| vec![evaluation_failed(rule, e)]),
    };
    tracing::debug!(rule, found = found.len(), "PM rule evaluated");
    if found.is_empty() {
        return found;
    }
    let strict = match host.pm_config() {
        Ok(cfg) => cfg.pm.strict,
        Err(err) => {
            tracing::warn!(%err, "pm config unreadable; [pm] strict not applied");
            false
        }
    };
    apply_strict(strict, found)
}
