//! `PM012`: A cycle member that has not started fails the definition of ready (`[pm] ready_requires`).

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// A cycle member that has not started fails the definition of ready (`[pm] ready_requires`).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM012",
    slug = "cycle-member-not-ready",
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
pub struct Pm012;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm012 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM012", |ledger| {
            let cfg = host
                .pm_config()
                .map_err(|e| format!("pm config unreadable: {e}"))?;
            crate::eval::ready::evaluate(ledger, &cfg.pm.ready_requires)
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }
}
