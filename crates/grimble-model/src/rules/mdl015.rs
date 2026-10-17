//! MDL015: A reference resolved to a nearer entity that shadows an outer one of the same name.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A reference resolved to a nearer entity that shadows an outer one of the same name.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL015",
    slug = "mdl-shadow",
    severity = Advisory,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = MdlHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Mdl015;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl015 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
