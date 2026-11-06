//! CLAIM005: A secret environment variable reaches a print, log or HTTP sink without a declassify symbol.

// frob:ticket 01M6QA50A5BK89J2G8SCZ4WBPR

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A secret environment variable reaches a print, log or HTTP sink without a declassify symbol.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CLAIM005",
    slug = "taint-secret-env",
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
pub struct Claim005;

impl<P: ?Sized + BindHost> RepoRule<P> for Claim005 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
