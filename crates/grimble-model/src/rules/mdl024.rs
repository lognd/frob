//! MDL024: A `->` hop follows an element that can fail, or a `-!>` hop follows one that cannot succeed.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `->` hop follows an element that can fail, or a `-!>` hop follows one that cannot succeed.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL024",
    slug = "mdl-fallible-sequence",
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
pub struct Mdl024;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl024 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
