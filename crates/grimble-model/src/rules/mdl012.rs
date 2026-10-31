//! MDL012: A reference uses a `renamed_from` name.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A reference uses a `renamed_from` name.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL012",
    slug = "mdl-deprecated-name",
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
pub struct Mdl012;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl012 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
