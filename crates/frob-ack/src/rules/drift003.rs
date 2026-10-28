//! `DRIFT003`: a symbol was acked, its signature changed, and no `frob:doc` directive covers it.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::eval::{Raw, drift003};
use crate::host::AckHost;

/// A symbol was acked, its signature changed, and no `frob:doc` directive covers it.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DRIFT003",
    slug = "stale-ack",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = AckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Drift003;

impl<P: ?Sized + AckHost> RelayRule<P> for Drift003 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let found: Vec<Finding> = drift003(host.inputs())
            .into_iter()
            .map(Raw::into_finding)
            .collect();
        tracing::debug!(found = found.len(), "DRIFT003 evaluated");
        found
    }
}
