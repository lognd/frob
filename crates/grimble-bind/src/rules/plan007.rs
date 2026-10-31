//! PLAN007: An impl's realization kinds do not fit the kind of the step owner

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// An impl's realization kinds do not fit the kind of the step owner
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN007",
    slug = "plan-affordance",
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
pub struct Plan007;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan007 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
