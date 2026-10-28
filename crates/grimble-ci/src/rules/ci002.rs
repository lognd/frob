//! CI002: A workflow without top-level permissions where a job sets none.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A workflow without top-level permissions where a job sets none.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI002",
    slug = "ci-permissions-missing",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci002;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci002 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci002 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI002")
    }
}
