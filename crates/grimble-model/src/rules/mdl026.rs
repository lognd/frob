//! MDL026: A scenario chain does not end, a scenario has no main chain, or the include graph has a cycle.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A scenario chain does not end, a scenario has no main chain, or the include graph has a cycle.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL026",
    slug = "mdl-unterminated",
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
pub struct Mdl026;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl026 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
