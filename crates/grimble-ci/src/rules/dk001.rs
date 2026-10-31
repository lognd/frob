//! DK001: A final image stage that runs as root.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A final image stage that runs as root.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DK001",
    slug = "dk-root-user",
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
pub struct Dk001;

impl<P: ?Sized + CiHost> RepoRule<P> for Dk001 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Dk001 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("DK001")
    }
}
