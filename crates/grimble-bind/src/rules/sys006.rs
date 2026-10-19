//! SYS006: The two ends of an acked flow disagree on the Contract facet.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::BindHost;

/// The two ends of an acked flow disagree on the Contract facet.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS006",
    slug = "sys-contract-skew",
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
pub struct Sys006;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys006 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + BindHost> Measured<P> for Sys006 {
    fn subjects(&self, host: &P) -> usize {
        host.subjects_of("SYS006")
    }
}
