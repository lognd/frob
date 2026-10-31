//! CI008: A registry publish on a trigger that is not limited to release tags.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A registry publish on a trigger that is not limited to release tags.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI008",
    slug = "ci-publish-untagged",
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
pub struct Ci008;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci008 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci008 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI008")
    }
}
