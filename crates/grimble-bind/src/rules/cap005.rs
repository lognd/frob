//! CAP005: A new or widened `may` grant has no human acknowledgement.

// frob:ticket 01M4GYBNW01DT1MJ6NJN2GX6NN

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A new or widened `may` grant has no human acknowledgement.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CAP005",
    slug = "cap-grant-unacknowledged",
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
pub struct Cap005;

impl<P: ?Sized + BindHost> RepoRule<P> for Cap005 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
