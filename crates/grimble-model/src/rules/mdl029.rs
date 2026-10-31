//! MDL029: A scenario starts with a system step instead of an actor step.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A scenario starts with a system step instead of an actor step.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL029",
    slug = "mdl-scenario-start",
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
pub struct Mdl029;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl029 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
