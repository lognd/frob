//! `PM010`: A planned or active cycle commits more points than its capacity.

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// A planned or active cycle commits more points than its capacity.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM010",
    slug = "cycle-over-capacity",
    severity = Advisory,
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
pub struct Pm010;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm010 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM010", |ledger| {
            let cfg = host
                .pm_config()
                .map_err(|e| format!("pm config unreadable: {e}"))?;
            crate::eval::capacity::evaluate(ledger, cfg.pm.min_history, cfg.pm.capacity_k)
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }
}
