//! CI006: A privileged trigger that checks out the pull request head.

// frob:ticket 01M5F010QB00AR00D4HYVYYPWH

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A privileged trigger that checks out the pull request head.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI006",
    slug = "no-prt-head-checkout",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci006;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci006 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci006 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI006")
    }
}
