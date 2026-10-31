//! MDL031: A planning item is malformed: outside a system, a reserved name, an unknown kind, or an inconsistent reference.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A planning item is malformed: outside a system, a reserved name, an unknown kind, or an inconsistent reference.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL031",
    slug = "mdl-planning",
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
pub struct Mdl031;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl031 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
