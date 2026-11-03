//! COH001: A unit that does two or more independent jobs.

// frob:ticket 01M4TVEKR73CP9A5RGGPPK3AWW

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CohHost;

/// A unit that does two or more independent jobs.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COH001",
    slug = "independent-jobs",
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
pub struct Coh001;

impl<P: ?Sized + CohHost> RepoRule<P> for Coh001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CohHost> Measured<P> for Coh001 {
    fn subjects(&self, host: &P) -> usize {
        host.coh_subjects_of("COH001")
    }
}
