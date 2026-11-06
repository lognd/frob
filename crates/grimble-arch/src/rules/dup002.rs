//! DUP002: A block of code copied three or more times with renamed identifiers or the same shape.

// frob:ticket 01M4P0SX8PWMV49CTPDX2SAP57

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A block of code copied three or more times with renamed identifiers or the same shape.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DUP002",
    slug = "arch-renamed-duplicate-code",
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
pub struct Dup002;

impl<P: ?Sized + ArchHost> RepoRule<P> for Dup002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Dup002 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("DUP002")
    }
}
