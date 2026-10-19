//! SYS008: An acked identity vanished and its Body appears under a new name.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// An acked identity vanished and its Body appears under a new name.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS008",
    slug = "sys-renamed",
    severity = Advisory,
    polarity = P0,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys008;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys008 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
