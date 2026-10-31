//! PLAN004: An impl or page has no realization clause

// frob:ticket 01M69AXE9FSCASMNDSMA1A7YMH

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// An impl or page has no realization clause
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN004",
    slug = "plan-unbound-impl",
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
pub struct Plan004;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan004 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
