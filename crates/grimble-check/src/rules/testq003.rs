//! TESTQ003: An if, a loop or a match in a test body (off unless the project enables it).

// frob:ticket 01M5HJNE91SN4N0MR8GHM30Z1Y

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::TestqHost;

/// An if, a loop or a match in a test body (off unless the project enables it).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TESTQ003",
    slug = "control-flow-in-test",
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
pub struct Testq003;

impl<P: ?Sized + TestqHost> RepoRule<P> for Testq003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + TestqHost> Measured<P> for Testq003 {
    fn subjects(&self, host: &P) -> usize {
        host.testq_subjects_of("TESTQ003")
    }
}
