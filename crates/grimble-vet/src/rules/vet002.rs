//! VET002: A locked version that a RustSec advisory affects.

// frob:ticket 01M5A63T4BZ3XH842F3RDFJ929

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::VetHost;

/// A locked version that a RustSec advisory affects.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VET002",
    slug = "advisory",
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
pub struct Vet002;

impl<P: ?Sized + VetHost> RepoRule<P> for Vet002 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + VetHost> Measured<P> for Vet002 {
    fn subjects(&self, host: &P) -> usize {
        host.vet_subjects_of("VET002")
    }
}
