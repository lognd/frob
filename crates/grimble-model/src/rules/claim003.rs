//! CLAIM003: A claim cannot be evaluated on this model, so it has no verdict.

// frob:ticket 01M4FGYHSXQXJD0JXFV2AZCED5

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A claim cannot be evaluated on this model, so it has no verdict.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CLAIM003",
    slug = "claim-unresolved",
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
pub struct Claim003;

impl<P: ?Sized + MdlHost> RepoRule<P> for Claim003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
