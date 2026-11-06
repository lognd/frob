//! VET008: A locked crate name one edit away from a well-known crate.

// frob:ticket 01M5A63T0R2D5DKF95XEZ00NZ6

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::VetHost;

/// A locked crate name one edit away from a well-known crate.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VET008",
    slug = "typosquat",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = VetHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Vet008;

impl<P: ?Sized + VetHost> RepoRule<P> for Vet008 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + VetHost> Measured<P> for Vet008 {
    fn subjects(&self, host: &P) -> usize {
        host.vet_subjects_of("VET008")
    }
}
