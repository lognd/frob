//! `TICK001`: A ticket's frontmatter differs from the fold of its events.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{LedgerHost, evaluation_failed};

const ID: &str = "TICK001";

/// A ticket's frontmatter differs from the fold of its events.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TICK001",
    slug = "frontmatter-differs-from-fold",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Deterministic,
    applies = project,
    host = LedgerHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tick001;

impl<P: ?Sized + LedgerHost> RelayRule<P> for Tick001 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let view = host.ledger_view();
        if let Some(why) = view.missing {
            // One finding for the whole absent ledger, carried by the ledger doctor's first rule.
            return vec![evaluation_failed(ID, why)];
        }
        if let Err(finding) = view.open(ID) {
            return vec![finding];
        }
        if view.ledger.is_none() {
            return Vec::new();
        }
        match host.doctor_findings() {
            Ok(found) => {
                tracing::debug!(found = found.len(), "TICK001 evaluated");
                found
            }
            Err(e) => vec![evaluation_failed(ID, e)],
        }
    }
}
