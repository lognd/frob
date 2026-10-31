//! PLAN006: A collected error pair has no covering verified_by evidence

// frob:ticket 01M69T6Q3J2RVWGTT4PM7YR6SS

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A collected error pair has no covering `verified_by` evidence
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN006",
    slug = "plan-uncovered-arm",
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
pub struct Plan006;

impl<P: ?Sized + BindHost> RepoRule<P> for Plan006 {
    /// The verdict is computed by the product pipeline from the planning graph.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
