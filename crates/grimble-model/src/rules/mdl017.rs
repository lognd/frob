//! MDL017: A list clause repeated with identical content.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A list clause repeated with identical content.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL017",
    slug = "mdl-duplicate-clause",
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
pub struct Mdl017;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl017 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
