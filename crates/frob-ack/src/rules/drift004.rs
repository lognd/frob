//! `DRIFT004`: a lock entry was recorded under another file version or digest scheme and must be re-attested.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::eval::{Raw, drift004};
use crate::host::AckHost;

/// A lock entry was recorded under another file version or digest scheme and must be re-attested.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DRIFT004",
    slug = "reattest-required",
    severity = Error,
    polarity = P0,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = AckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Drift004;

impl<P: ?Sized + AckHost> RelayRule<P> for Drift004 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let found: Vec<Finding> = drift004(host.inputs())
            .into_iter()
            .map(Raw::into_finding)
            .collect();
        tracing::debug!(found = found.len(), "DRIFT004 evaluated");
        found
    }
}
