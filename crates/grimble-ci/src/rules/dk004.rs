//! DK004: A download piped straight into a shell.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A download piped straight into a shell.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DK004",
    slug = "dk-pipe-to-shell",
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
pub struct Dk004;

impl<P: ?Sized + CiHost> RepoRule<P> for Dk004 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Dk004 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("DK004")
    }
}
