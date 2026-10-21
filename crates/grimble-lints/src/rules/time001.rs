//! TIME001: A current-time read in the local zone, or without a zone, whose value is stored or sent.

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::TimeHost;

/// A current-time read in the local zone, or without a zone, whose value is stored or sent.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TIME001",
    slug = "local-clock-read",
    severity = Warn,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = TimeHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Time001;

impl<P: ?Sized + TimeHost> RepoRule<P> for Time001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + TimeHost> Measured<P> for Time001 {
    fn subjects(&self, host: &P) -> usize {
        host.time_subjects_of("TIME001")
    }
}
