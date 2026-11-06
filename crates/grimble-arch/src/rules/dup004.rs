//! DUP004: a function in a changed file has the same statement shapes as another function.

// frob:ticket 01M4P0SXFYYD9TE4F53NQ5SB96

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ArchHost;

/// A function in a changed file has the same statement shapes as another function.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "DUP004",
    slug = "arch-structural-duplicate-code",
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
pub struct Dup004;

impl<P: ?Sized + ArchHost> RepoRule<P> for Dup004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ArchHost> Measured<P> for Dup004 {
    fn subjects(&self, host: &P) -> usize {
        host.arch_subjects_of("DUP004")
    }
}
