//! PLAN010: A scenario realizes no goal and no scenario includes it

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A scenario realizes no goal and no scenario includes it
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN010",
    slug = "plan-unjustified-scenario",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Plan010;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan010 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
