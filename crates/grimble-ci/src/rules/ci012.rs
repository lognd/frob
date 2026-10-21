//! CI012: CI configuration that disagrees with the repository manifests and ownership files.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// CI configuration that disagrees with the repository manifests and ownership files.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI012",
    slug = "ci-config-consistency",
    severity = Warn,
    polarity = P0,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci012;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci012 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci012 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI012")
    }
}
