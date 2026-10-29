//! LOG002: A program that emits output has no logging crate configured.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::LogHost;

/// A program that emits output has no logging crate configured.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LOG002",
    slug = "no-logging-crate",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = LogHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Log002;

impl<P: ?Sized + LogHost> RepoRule<P> for Log002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + LogHost> Measured<P> for Log002 {
    fn subjects(&self, host: &P) -> usize {
        host.log_subjects_of("LOG002")
    }
}
