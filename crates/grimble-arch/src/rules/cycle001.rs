//! CYCLE001: Crates (or files, outside any crate) that import each other.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// Crates (or files, outside any crate) that import each other.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CYCLE001",
    slug = "arch-import-cycle",
    severity = Error,
    polarity = Pc,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ArchHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cycle001;

impl<P: ?Sized + ArchHost> RepoRule<P> for Cycle001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Cycle001 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("CYCLE001")
    }
}
