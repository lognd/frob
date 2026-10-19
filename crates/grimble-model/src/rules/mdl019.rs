//! MDL019: A .grmb file in the walk is reachable from no model root.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A .grmb file in the walk is reachable from no model root.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL019",
    slug = "mdl-orphan-file",
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
pub struct Mdl019;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl019 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
