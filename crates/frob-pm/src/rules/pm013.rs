//! `PM013`: the repository has more tickets in progress than `[pm.wip] in_progress` allows.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::eval::wip::WipLimits;
use crate::host::{PmHost, relay_pm};

/// The repository has more tickets in progress than `[pm.wip] in_progress` allows.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM013",
    slug = "wip-limit-exceeded",
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
pub struct Pm013;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm013 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM013", |ledger| {
            let cfg = host
                .pm_config()
                .map_err(|e| format!("pm config unreadable: {e}"))?;
            let limits = WipLimits {
                in_progress: cfg.wip.in_progress,
                expedite_max: cfg.classes.expedite_max,
                ready: cfg.wip.ready,
            };
            let live = host.live_leases();
            crate::eval::wip::evaluate_with(ledger, limits, live.as_ref())
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }
}
