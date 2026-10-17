//! MDL001: Two declarations of one full name.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// Two declarations of one full name.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL001",
    slug = "mdl-duplicate-entity",
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
pub struct Mdl001;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
