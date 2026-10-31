//! COH002: A unit that branches on computed data and performs effects inside those branches.

// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CohHost;

/// A unit that branches on computed data and performs effects inside those branches.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COH002",
    slug = "decision-with-effects",
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
pub struct Coh002;

impl<P: ?Sized + CohHost> RepoRule<P> for Coh002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CohHost> Measured<P> for Coh002 {
    fn subjects(&self, host: &P) -> usize {
        host.coh_subjects_of("COH002")
    }
}
