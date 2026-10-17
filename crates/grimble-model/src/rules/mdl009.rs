//! MDL009: An ill-typed value.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An ill-typed value.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL009",
    slug = "mdl-type",
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
pub struct Mdl009;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl009 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
