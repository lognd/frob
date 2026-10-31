//! DUP001: A block of code copied three or more times.

// frob:ticket 01M4D958QKMX7VHFJMRMAWDT22

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A block of code copied three or more times.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DUP001",
    slug = "arch-duplicate-code",
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
pub struct Dup001;

impl<P: ?Sized + ArchHost> RepoRule<P> for Dup001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Dup001 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("DUP001")
    }
}
