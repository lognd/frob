//! DUP005: a function anywhere in the repository has the same statement shapes as another function.

// frob:ticket 01M4P0SXJRVQ0ADAAH3FMYPAR6

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A function anywhere in the repository has the same statement shapes as another function (whole-repo scan).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DUP005",
    slug = "arch-structural-duplicate-scan",
    severity = Error,
    polarity = Pn,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ArchHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Dup005;

impl<P: ?Sized + ArchHost> RepoRule<P> for Dup005 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Dup005 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("DUP005")
    }
}
