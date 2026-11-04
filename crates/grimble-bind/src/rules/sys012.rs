//! SYS012: A template excuse overlaps a may grant.

// frob:ticket 01M5XNNK0W03EZMP1EE2NDKP55

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A template excuse overlaps a may grant.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS012",
    slug = "sys-excuse-grant",
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
pub struct Sys012;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys012 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
