//! CAP006: A `may` grant exceeds a trust-level capability ceiling.

// frob:ticket 01M5XNNJMSCGPFS84V3PZQKTNC

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A `may` grant exceeds a trust-level capability ceiling.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CAP006",
    slug = "cap-grant-exceeds-ceiling",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cap006;

impl<P: ?Sized + BindHost> RepoRule<P> for Cap006 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
