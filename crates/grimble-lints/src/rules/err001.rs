//! ERR001: An error handler with an empty body that silently swallows the error.

// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ErrHost;

/// An error handler with an empty body that silently swallows the error.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ERR001",
    slug = "empty-error-handler",
    severity = Warn,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ErrHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Err001;

impl<P: ?Sized + ErrHost> RepoRule<P> for Err001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ErrHost> Measured<P> for Err001 {
    fn subjects(&self, host: &P) -> usize {
        host.err_subjects_of("ERR001")
    }
}
