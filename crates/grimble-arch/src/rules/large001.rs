//! LARGE001: A function, method or type longer than the configured line limit.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A function, method or type longer than the configured line limit.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LARGE001",
    slug = "arch-large-unit",
    severity = Warn,
    polarity = Pn,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ArchHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Large001;

impl<P: ?Sized + ArchHost> RepoRule<P> for Large001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Large001 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("LARGE001")
    }
}
