//! SYS007: An acked identity changed since its ack.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::BindHost;

/// An acked identity changed since its ack.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS007",
    slug = "sys-changed-since-ack",
    severity = Error,
    polarity = P0,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys007;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys007 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + BindHost> Measured<P> for Sys007 {
    fn subjects(&self, host: &P) -> usize {
        host.subjects_of("SYS007")
    }
}
