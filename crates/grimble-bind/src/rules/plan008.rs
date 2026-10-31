//! PLAN008: A page cannot be reached from an entry page

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A page cannot be reached from an entry page
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN008",
    slug = "plan-page-unreachable",
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
pub struct Plan008;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan008 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
