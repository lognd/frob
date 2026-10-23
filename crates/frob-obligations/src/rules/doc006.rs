//! `DOC006`: a prose citation names a markdown file, section or anchor that does not exist.

// frob:ticket 01M4H0RE1Q9A1M47ZT7Q1ZG43K

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::doc_citation;
use crate::host::ObligationHost;

/// A prose citation (`x.md section N`, `x.md#anchor`) whose target is missing and not remapped.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DOC006",
    slug = "dangling-citation",
    severity = Warn,
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
pub struct Doc006;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Doc006 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = doc_citation::doc006(host.obligations().root, files);
        tracing::debug!(found = found.len(), "DOC006 evaluated");
        found
    }
}
