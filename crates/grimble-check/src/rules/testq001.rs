//! TESTQ001: A test that asserts nothing, directly or through a helper in the same file.

// frob:ticket 01M5HJNE91SN4N0MR8GHM30Z1Y

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::TestqHost;

/// A test that asserts nothing, directly or through a helper in the same file.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TESTQ001",
    slug = "no-assertion",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = TestqHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Testq001;

impl<P: ?Sized + TestqHost> RepoRule<P> for Testq001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + TestqHost> Measured<P> for Testq001 {
    fn subjects(&self, host: &P) -> usize {
        host.testq_subjects_of("TESTQ001")
    }
}
