//! TIME002: A naive and a timezone-aware datetime compared or subtracted.

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::TimeHost;

/// A naive and a timezone-aware datetime compared or subtracted.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TIME002",
    slug = "naive-aware-mix",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = TimeHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Time002;

impl<P: ?Sized + TimeHost> RepoRule<P> for Time002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + TimeHost> Measured<P> for Time002 {
    fn subjects(&self, host: &P) -> usize {
        host.time_subjects_of("TIME002")
    }
}
