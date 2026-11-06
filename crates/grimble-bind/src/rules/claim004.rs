//! CLAIM004: A `never NODE uses ATOM` claim is refuted by code the node owns.

// frob:ticket 01M5XNNJQN463MG3PT8NBEC70D

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A `never NODE uses ATOM` claim is refuted by code the node owns.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CLAIM004",
    slug = "claim-never-refuted",
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
pub struct Claim004;

impl<P: ?Sized + BindHost> RepoRule<P> for Claim004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
