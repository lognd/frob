//! CAP007: A `may` grant has expired (its `until=` date has passed).

// frob:ticket 01M5XNNJTK08K3CB98MCT14W34

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A `may` grant has expired (its `until=` date has passed).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CAP007",
    slug = "cap-grant-expired",
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
pub struct Cap007;

impl<P: ?Sized + BindHost> RepoRule<P> for Cap007 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
