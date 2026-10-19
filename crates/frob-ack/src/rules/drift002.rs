//! `DRIFT002`: a `frob:doc` directive names a markdown section that does not exist.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::eval::{Raw, drift002};
use crate::host::AckHost;

/// A `frob:doc` directive names a markdown section that does not exist.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DRIFT002",
    slug = "dangling-doc-target",
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
pub struct Drift002;

impl<P: ?Sized + AckHost> RelayRule<P> for Drift002 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let found: Vec<Finding> = drift002(host.inputs())
            .into_iter()
            .map(Raw::into_finding)
            .collect();
        tracing::debug!(found = found.len(), "DRIFT002 evaluated");
        found
    }
}
