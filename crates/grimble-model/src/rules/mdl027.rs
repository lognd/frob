//! MDL027: A `retry` is misplaced, has no valid `max`, or does not target a step on its path.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `retry` is misplaced, has no valid `max`, or does not target a step on its path.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL027",
    slug = "mdl-retry",
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
pub struct Mdl027;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl027 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
