//! PLAN044: An outcome map over an `open` set has no `_` source.

// frob:ticket 01M6P033S4VV7JST84C3Q0TF80

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An outcome map over an `open` set has no `_` source.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN044",
    slug = "plan-open-map-no-rest",
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
pub struct Plan044;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan044 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
