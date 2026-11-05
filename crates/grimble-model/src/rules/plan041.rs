//! PLAN041: A producible error of a waypoint unit is covered by no outcome-map source.

// frob:ticket 01M6P033S4VV7JST84C3Q0TF80

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A producible error of a waypoint unit is covered by no outcome-map source.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN041",
    slug = "plan-unmapped-error",
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
pub struct Plan041;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan041 {
    /// The verdict is computed by the planning pass in `plan_check` (PLAN041 awaits adapter error-flow facts); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
