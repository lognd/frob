//! CI015: An external action from an archived repository or on an end-of-life Node runtime.

// frob:ticket 01M5F010V5GV0B7KJ7M5QQG70Q

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// An external action from an archived repository or on an end-of-life Node runtime.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI015",
    slug = "action-currency",
    severity = Advisory,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci015;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci015 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci015 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI015")
    }
}
