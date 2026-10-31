//! MDL023: An error variant is collected by `-!>` but neither handled nor declared in `fails with`.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An error variant is collected by `-!>` but neither handled nor declared in `fails with`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL023",
    slug = "mdl-unhandled",
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
pub struct Mdl023;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl023 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
