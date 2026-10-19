//! FLOW002: A flow into a higher-trust node has no endorse boundary reaching that trust.

// frob:ticket 01M4FGYG9TXDAMZ2VS2ZHGJKX1

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A flow into a higher-trust node has no endorse boundary reaching that trust.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "FLOW002",
    slug = "flow-unendorsed",
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
pub struct Flow002;

impl<P: ?Sized + MdlHost> RepoRule<P> for Flow002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
