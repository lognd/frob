//! DEAD001: A private function or method that nothing references.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A private function or method that nothing references.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DEAD001",
    slug = "arch-dead-unit",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ArchHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Dead001;

impl<P: ?Sized + ArchHost> RepoRule<P> for Dead001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Dead001 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("DEAD001")
    }
}
