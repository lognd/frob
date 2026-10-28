//! CI004: A push or pull request workflow with no concurrency group.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A push or pull request workflow with no concurrency group.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI004",
    slug = "ci-concurrency-missing",
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
pub struct Ci004;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci004 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci004 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI004")
    }
}
