//! `DOC003`: a document under `docs/` has no valid status header.

// frob:ticket 01M4H0RKJHHWWT0XC17W5JD1VG

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::docstatus;
use crate::host::ObligationHost;

/// A document under docs/ without one valid status header.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DOC003",
    slug = "doc-status-header",
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
pub struct Doc003;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Doc003 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = docstatus::doc003(host.obligations().root, files);
        tracing::debug!(found = found.len(), "DOC003 evaluated");
        found
    }
}
