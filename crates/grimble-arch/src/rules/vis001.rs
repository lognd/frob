//! VIS001: A `pub` function that no other package uses.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A `pub` function that no other package uses.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VIS001",
    slug = "arch-wide-visibility",
    severity = Advisory,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ArchHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Vis001;

impl<P: ?Sized + ArchHost> RepoRule<P> for Vis001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Vis001 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("VIS001")
    }
}
