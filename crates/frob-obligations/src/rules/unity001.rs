//! `UNITY001`: a tracked Unity asset or folder with no tracked .meta.

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::ObligationHost;
use crate::unity;

/// A tracked Unity asset or folder with no tracked .meta.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "UNITY001",
    slug = "asset-missing-meta",
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
pub struct Unity001;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Unity001 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = unity::unity001(host.obligations().root, files);
        tracing::debug!(found = found.len(), "UNITY001 evaluated");
        found
    }
}
