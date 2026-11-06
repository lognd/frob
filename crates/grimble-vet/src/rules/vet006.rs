//! VET006: A locked version that was yanked from the registry.

// frob:ticket 01M5A63T0R2D5DKF95XEZ00NZ6

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::VetHost;

/// A locked version that was yanked from the registry.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VET006",
    slug = "yanked",
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
pub struct Vet006;

impl<P: ?Sized + VetHost> RepoRule<P> for Vet006 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + VetHost> Measured<P> for Vet006 {
    fn subjects(&self, host: &P) -> usize {
        host.vet_subjects_of("VET006")
    }
}
