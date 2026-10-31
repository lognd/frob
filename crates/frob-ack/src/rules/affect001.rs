//! `AFFECT001`: a public symbol changed its signature and its dependents were not re-acked.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::eval::{Raw, affect001};
use crate::host::AckHost;

/// A public symbol changed its signature and its dependents were not re-acked.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AFFECT001",
    slug = "dependents-not-updated",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [TestItems], min_fidelity = F2),
    host = AckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Affect001;

impl<P: ?Sized + AckHost> RelayRule<P> for Affect001 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let found: Vec<Finding> = affect001(host.inputs())
            .into_iter()
            .map(Raw::into_finding)
            .collect();
        tracing::debug!(found = found.len(), "AFFECT001 evaluated");
        found
    }
}
