//! MDL025: A match or handle arm matches no outcome of its domain, or ties with another arm of equal specificity.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A match or handle arm matches no outcome of its domain, or ties with another arm of equal specificity.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL025",
    slug = "mdl-unreachable-arm",
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
pub struct Mdl025;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl025 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
