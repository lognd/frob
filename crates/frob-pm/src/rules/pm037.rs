//! `PM037`: a design obligation has no live implementing ticket.

// frob:ticket 01M4FDBDC401KMNN4C12QTA3PK

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// A design obligation has no live implementing ticket.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM037",
    slug = "obligation-unplanned",
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
pub struct Pm037;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm037 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let Some(graph) = host.design_graph() else {
            return Vec::new();
        };
        relay_pm(host, "PM037", |ledger| {
            crate::eval::design::evaluate(ledger, &graph)
        })
    }
}
