//! ERR003: An acquire with no release on the teardown path.

// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::ErrHost;

/// A catch-all handler that neither rethrows nor logs the error.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ERR003",
    slug = "silent-catch-all",
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
pub struct Err003;

impl<P: ?Sized + ErrHost> RepoRule<P> for Err003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + ErrHost> Measured<P> for Err003 {
    fn subjects(&self, host: &P) -> usize {
        host.err_subjects_of("ERR003")
    }
}
