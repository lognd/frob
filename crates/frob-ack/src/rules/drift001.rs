//! `DRIFT001`: a `frob:doc` binding went stale: the code changed under the doc, or the doc under the code.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::eval::{Raw, drift001};
use crate::host::AckHost;

/// A `frob:doc` binding went stale: the code changed under the doc, or the doc under the code.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DRIFT001",
    slug = "doc-binding-drift",
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
pub struct Drift001;

impl<P: ?Sized + AckHost> RelayRule<P> for Drift001 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let found: Vec<Finding> = drift001(host.inputs())
            .into_iter()
            .map(Raw::into_finding)
            .collect();
        tracing::debug!(found = found.len(), "DRIFT001 evaluated");
        found
    }
}
