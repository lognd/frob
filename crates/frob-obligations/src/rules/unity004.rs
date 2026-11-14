//! `UNITY004`: a guid shared by two or more .meta files.

// frob:ticket 01M5FRZGDQ88QYMF8R547WNTP3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::ObligationHost;
use crate::unity;

/// A C# field no code assigns and the engine does not write.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "UNITY004",
    slug = "field-never-written",
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
pub struct Unity004;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Unity004 {
    fn relay(&self, host: &P, files: &mut FileInterner) -> Vec<Finding> {
        let found = {
            let inputs = host.obligations();
            unity::unity004(inputs.root, inputs.graph, inputs.unity, files)
        };
        tracing::debug!(found = found.len(), "UNITY004 evaluated");
        found
    }
}
