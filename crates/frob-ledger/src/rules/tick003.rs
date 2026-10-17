//! `TICK003`: A link or parent names a ticket that does not exist.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{LedgerHost, evaluation_failed};

const ID: &str = "TICK003";

/// A link or parent names a ticket that does not exist.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TICK003",
    slug = "dangling-link",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = LedgerHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tick003;

impl<P: ?Sized + LedgerHost> RelayRule<P> for Tick003 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let view = host.ledger_view();
        if view.missing.is_some() || view.ledger.is_none() && view.error.is_none() {
            return Vec::new();
        }
        if let Err(finding) = view.open(ID) {
            return vec![finding];
        }
        match host.doctor_findings() {
            Ok(found) => {
                tracing::debug!(found = found.len(), "TICK003 evaluated");
                found
            }
            Err(e) => vec![evaluation_failed(ID, e)],
        }
    }
}
