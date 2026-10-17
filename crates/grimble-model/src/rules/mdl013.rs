//! MDL013: A malformed exception clause.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A malformed exception clause.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL013",
    slug = "mdl-exception",
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
pub struct Mdl013;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl013 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
