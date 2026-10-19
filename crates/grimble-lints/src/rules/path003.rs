//! PATH003: A path interpolated into one command-line string instead of passed as its own argument.

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::PathHost;

/// A path interpolated into one command-line string instead of passed as its own argument.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PATH003",
    slug = "path-in-command-line",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = PathHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Path003;

impl<P: ?Sized + PathHost> RepoRule<P> for Path003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + PathHost> Measured<P> for Path003 {
    fn subjects(&self, host: &P) -> usize {
        host.path_subjects_of("PATH003")
    }
}
