//! VET001: A new direct dependency that is not on the vet allowlist.

// frob:ticket 01M5A63T4BZ3XH842F3RDFJ929

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::VetHost;

/// A new direct dependency that is not on the vet allowlist.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VET001",
    slug = "unvetted-direct",
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
pub struct Vet001;

impl<P: ?Sized + VetHost> RepoRule<P> for Vet001 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + VetHost> Measured<P> for Vet001 {
    fn subjects(&self, host: &P) -> usize {
        host.vet_subjects_of("VET001")
    }
}
