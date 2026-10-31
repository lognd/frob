//! PLAN005: A goal leaf, scenario, impl or page has no own evidence

// frob:ticket 01M69AXE9FSCASMNDSMA1A7YMH

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A goal leaf, scenario, impl or page has no own evidence
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN005",
    slug = "plan-unverified",
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
pub struct Plan005;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan005 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
