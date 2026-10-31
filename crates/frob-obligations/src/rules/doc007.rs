//! `DOC007`: a document under `docs/` that no link chain from a root page reaches.

// frob:ticket 01M67VEKBESFK2C23JMXV82RW9

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::doc_orphan;
use crate::host::ObligationHost;

/// A document under docs/ that no link chain from the docs index or a root page reaches.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DOC007",
    slug = "orphan-doc-page",
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
pub struct Doc007;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Doc007 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = doc_orphan::doc007(host.obligations().root, files);
        tracing::debug!(found = found.len(), "DOC007 evaluated");
        found
    }
}
