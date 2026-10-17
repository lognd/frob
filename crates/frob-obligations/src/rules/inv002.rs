//! `INV002`: an import that a `forbid_imports` entry forbids.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::ObligationHost;
use crate::inv;

/// An import that a `forbid_imports` entry forbids.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "INV002",
    slug = "forbidden-import",
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
pub struct Inv002;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Inv002 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let i = host.obligations();
        let found = inv::inv002(i.root, i.graph, i.config, files);
        tracing::debug!(found = found.len(), "INV002 evaluated");
        found
    }
}
