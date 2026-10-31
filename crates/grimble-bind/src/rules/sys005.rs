//! SYS005: A public unit in a modeled selector that no node owns.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::BindHost;

/// A public unit in a modeled selector that no node owns.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS005",
    slug = "sys-unmodeled",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys005;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys005 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + BindHost> Measured<P> for Sys005 {
    fn subjects(&self, host: &P) -> usize {
        host.subjects_of("SYS005")
    }
}
