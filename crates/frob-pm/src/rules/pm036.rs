//! `PM036`: an active cycle is past its end date and has not been closed.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// An active cycle is past its end date and has not been closed.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM036",
    slug = "cycle-overdue",
    severity = Warn,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = PmHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Pm036;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm036 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM036", |ledger| {
            crate::eval::cycle::evaluate(ledger)
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }
}
