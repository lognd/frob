//! MDL028: A `_` arm hides outcome variants added later.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `_` arm hides outcome variants added later.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL028",
    slug = "mdl-wildcard-arm",
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
pub struct Mdl028;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl028 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
