//! TESTQ002: A sleep, wall-clock read or unseeded random source in a test body.

// frob:ticket 01M5HJNE91SN4N0MR8GHM30Z1Y

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::TestqHost;

/// A sleep, wall-clock read or unseeded random source in a test body.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TESTQ002",
    slug = "nondeterministic-test",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = TestqHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Testq002;

impl<P: ?Sized + TestqHost> RepoRule<P> for Testq002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + TestqHost> Measured<P> for Testq002 {
    fn subjects(&self, host: &P) -> usize {
        host.testq_subjects_of("TESTQ002")
    }
}
