//! CI016: A privileged workflow that runs frob, grimble or crunk with trust not read from a protected ref.

// frob:ticket 01M5F010V5GV0B7KJ7M5QQG70Q

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A privileged workflow that runs frob, grimble or crunk with trust not read from a protected ref.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI016",
    slug = "trust-from-protected-ref",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci016;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci016 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci016 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI016")
    }
}
