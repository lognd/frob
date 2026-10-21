//! CI003: Top-level permissions that grant write to every job.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// Top-level permissions that grant write to every job.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI003",
    slug = "ci-permissions-write-all",
    severity = Warn,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci003;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci003 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci003 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI003")
    }
}
