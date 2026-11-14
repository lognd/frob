//! COH004: A unit whose identifiers fall into two or more disjoint vocabularies.

// frob:ticket 01M5K18043Y5V9TF7QD2KNYR34

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CohHost;

/// A unit whose identifiers fall into two or more disjoint vocabularies.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COH004",
    slug = "mixed-vocabularies",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CohHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Coh004;

impl<P: ?Sized + CohHost> RepoRule<P> for Coh004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CohHost> Measured<P> for Coh004 {
    fn subjects(&self, host: &P) -> usize {
        host.coh_subjects_of("COH004")
    }
}
