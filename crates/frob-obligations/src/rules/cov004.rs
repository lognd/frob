//! `COV004`: measured line or branch coverage under a `[[coverage.threshold]]` minimum.

// frob:ticket 01M4FD1NX760N78Z1T60MQ76H2

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::coverage;
use crate::host::ObligationHost;

/// Measured line or branch coverage under a `[[coverage.threshold]]` minimum.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COV004",
    slug = "coverage-below-threshold",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Visibility], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cov004;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Cov004 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = coverage::cov004(host.obligations().root, files);
        tracing::debug!(found = found.len(), "COV004 evaluated");
        found
    }
}
