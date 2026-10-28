//! COH003: A unit whose callees span abstraction layers further apart than the allowed spread.

// frob:ticket 01M5M1TVT09K4YPK17S62Y1A18

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CohHost;

/// A unit whose callees span abstraction layers further apart than the allowed spread.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COH003",
    slug = "mixed-abstraction-levels",
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
pub struct Coh003;

impl<P: ?Sized + CohHost> RepoRule<P> for Coh003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CohHost> Measured<P> for Coh003 {
    fn subjects(&self, host: &P) -> usize {
        host.coh_subjects_of("COH003")
    }
}
