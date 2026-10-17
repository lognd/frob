//! MDL010: A selector that cannot match anything whatever the repository holds.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A selector that cannot match anything whatever the repository holds.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL010",
    slug = "mdl-selector-empty-by-construction",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = MdlHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Mdl010;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl010 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
