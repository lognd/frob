//! `PM011`: A planned or active cycle has no goal.

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// A planned or active cycle has no goal.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM011",
    slug = "cycle-without-goal",
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
pub struct Pm011;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm011 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM011", |ledger| {
            crate::eval::goal::evaluate(ledger)
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }
}
