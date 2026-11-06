//! VET007: A locked crate with no release within the maintenance horizon.

// frob:ticket 01M5A63T0R2D5DKF95XEZ00NZ6

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::VetHost;

/// A locked crate with no release within the maintenance horizon.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VET007",
    slug = "maintenance",
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
pub struct Vet007;

impl<P: ?Sized + VetHost> RepoRule<P> for Vet007 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + VetHost> Measured<P> for Vet007 {
    fn subjects(&self, host: &P) -> usize {
        host.vet_subjects_of("VET007")
    }
}
