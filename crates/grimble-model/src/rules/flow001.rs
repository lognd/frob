//! FLOW001: A flow's label exceeds the destination node's clearance and no declassify boundary lowers it.

// frob:ticket 01M4FGYG9TXDAMZ2VS2ZHGJKX1

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A flow's label exceeds the destination node's clearance and no declassify boundary lowers it.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "FLOW001",
    slug = "flow-label-closure",
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
pub struct Flow001;

impl<P: ?Sized + MdlHost> RepoRule<P> for Flow001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
