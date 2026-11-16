//! `COV005`: fewer unit test functions in a scope than a `[[testing.threshold]]` minimum.

// frob:ticket 01M5HT58NK23KQMMVXD1FZ0R2D

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::ObligationHost;
use crate::unit_cases;

/// A scope holds fewer unit test functions than its `[[testing.threshold]]` `min_unit_cases`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COV005",
    slug = "unit-cases-below-minimum",
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
pub struct Cov005;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Cov005 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = unit_cases::cov005(&host.obligations(), files);
        tracing::debug!(found = found.len(), "COV005 evaluated");
        found
    }
}
