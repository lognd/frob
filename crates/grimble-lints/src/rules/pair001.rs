//! PAIR001: An acquire with no release on the teardown path.

// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::PairHost;

/// An acquire (timer, listener, request, observer, subscription) with no release on the teardown path.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PAIR001",
    slug = "acquire-without-release",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = PairHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Pair001;

impl<P: ?Sized + PairHost> RepoRule<P> for Pair001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + PairHost> Measured<P> for Pair001 {
    fn subjects(&self, host: &P) -> usize {
        host.pair_subjects_of("PAIR001")
    }
}
