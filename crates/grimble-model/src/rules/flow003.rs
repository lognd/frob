//! FLOW003: A flow from a foreign node declares no rate.

// frob:ticket 01M4FGYG9TXDAMZ2VS2ZHGJKX1

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A flow from a foreign node declares no rate.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "FLOW003",
    slug = "flow-no-rate",
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
pub struct Flow003;

impl<P: ?Sized + MdlHost> RepoRule<P> for Flow003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
