//! CAP004: A template excuse covers a unit that uses the excused capability.

// frob:ticket 01M5A75BSA2RK08ERZERAD5ARW

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A template excuse covers a unit that uses the excused capability.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CAP004",
    slug = "cap-excuse-masks-use",
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
pub struct Cap004;

impl<P: ?Sized + BindHost> RepoRule<P> for Cap004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
