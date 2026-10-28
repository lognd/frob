//! `INV001`: an invariants document that no `frob:invariant` directive names.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::ObligationHost;
use crate::inv;

/// An invariants document that no `frob:invariant` directive names.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "INV001",
    slug = "invariant-without-anchor",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Inv001;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Inv001 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let i = host.obligations();
        let found = inv::inv001(i.graph, i.directives, files);
        tracing::debug!(found = found.len(), "INV001 evaluated");
        found
    }
}
