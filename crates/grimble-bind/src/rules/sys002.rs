//! SYS002: Two nodes own one identity at the same specificity.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// Two nodes own one identity at the same specificity.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS002",
    slug = "sys-ambiguous-owner",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys002;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
