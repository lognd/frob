//! SYS010: A claim above proof level L1 has no test evidence.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A claim above proof level L1 has no test evidence.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS010",
    slug = "sys-claim-without-evidence",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys010;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys010 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
