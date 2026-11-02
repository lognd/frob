//! AMB008: A system ambient policy has no `verified_by` test.

// frob:ticket 01M6CKH5NBZR6KXAXQDSAVFSVM

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A system ambient policy has no `verified_by` test.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB008",
    slug = "amb-unverified-policy",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = MdlHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Amb008;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb008 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
