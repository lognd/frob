//! PLAN002: A scenario realizes a goal that has child goals

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A scenario realizes a goal that has child goals
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN002",
    slug = "plan-coarse-realization",
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
pub struct Plan002;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan002 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
