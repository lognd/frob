//! CI009: A long-lived token used to publish where trusted publishing exists.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A long-lived token used to publish where trusted publishing exists.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI009",
    slug = "ci-publish-token",
    severity = Advisory,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci009;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci009 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci009 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI009")
    }
}
