//! `PM033`: the ready queue holds fewer doable tickets than `[pm] ready_min`.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// The ready queue holds fewer doable tickets than `[pm] ready_min`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM033",
    slug = "ready-queue-low",
    severity = Error,
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
pub struct Pm033;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm033 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM033", |ledger| {
            let ready_min = host
                .pm_config()
                .map_err(|e| format!("pm config unreadable: {e}"))?
                .pm
                .ready_min;
            let leases = host.lease_check();
            crate::eval::replenish::evaluate(ledger, &*leases, ready_min)
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }
}
