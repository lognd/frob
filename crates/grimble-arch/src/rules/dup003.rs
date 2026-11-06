//! DUP003: The clone index of DUP001 is missing or damaged.

// frob:ticket 01M4P0SXCZQTRS8W10VXJ1W4P0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// The clone index of DUP001 is missing or damaged.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DUP003",
    slug = "arch-clone-index",
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
pub struct Dup003;

impl<P: ?Sized + ArchHost> RepoRule<P> for Dup003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Dup003 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("DUP003")
    }
}
