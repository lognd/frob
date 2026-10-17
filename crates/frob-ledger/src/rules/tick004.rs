//! `TICK004`: A committed ledger file holds an absolute home path.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{LedgerHost, evaluation_failed};

const ID: &str = "TICK004";

/// A committed ledger file holds an absolute home path.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TICK004",
    slug = "absolute-home-path",
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
pub struct Tick004;

impl<P: ?Sized + LedgerHost> RelayRule<P> for Tick004 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let view = host.ledger_view();
        if view.missing.is_some() {
            return Vec::new();
        }
        let ledger = match view.open(ID) {
            Ok(Some(ledger)) => ledger,
            Ok(None) => return Vec::new(),
            Err(finding) => return vec![finding],
        };
        match ledger.home_path_findings() {
            Ok(found) => {
                tracing::debug!(found = found.len(), "TICK004 evaluated");
                found
            }
            Err(e) => vec![evaluation_failed(ID, e)],
        }
    }
}
