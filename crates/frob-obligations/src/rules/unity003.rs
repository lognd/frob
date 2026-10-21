//! `UNITY003`: a guid shared by two or more .meta files.

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::ObligationHost;
use crate::unity;

/// A guid shared by two or more .meta files.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "UNITY003",
    slug = "duplicate-guid",
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
pub struct Unity003;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Unity003 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = unity::unity003(host.obligations().root, files);
        tracing::debug!(found = found.len(), "UNITY003 evaluated");
        found
    }
}
