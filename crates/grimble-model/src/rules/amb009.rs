//! AMB009: A `restart` policy covers an impl in a stateful node that has no flow to a store.

// frob:ticket 01M6CKH5NBZR6KXAXQDSAVFSVM

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `restart` policy covers an impl in a stateful node that has no flow to a store.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB009",
    slug = "amb-restart-stateful",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = MdlHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Amb009;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb009 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
