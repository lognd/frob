//! PLAN003: A step used by a scenario has no impl

// frob:ticket 01M69AXE9FSCASMNDSMA1A7YMH

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A step used by a scenario has no impl
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN003",
    slug = "plan-unimplemented-step",
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
pub struct Plan003;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan003 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
