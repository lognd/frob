//! CI014: A workflow that breaks the GitHub Actions syntax.

// frob:ticket 01M5F010V5GV0B7KJ7M5QQG70Q

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// A workflow that breaks the GitHub Actions syntax.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI014",
    slug = "gha-syntax-and-schema",
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
pub struct Ci014;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci014 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci014 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI014")
    }
}
