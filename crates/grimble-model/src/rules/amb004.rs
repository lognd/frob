//! AMB004: An arm `retry` of a system step is also repeated by an applying ambient `retry`, so the attempts multiply.

// frob:ticket 01M6CKH5NBZR6KXAXQDSAVFSVM

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An arm `retry` of a system step is also repeated by an applying ambient `retry`, so the attempts multiply.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB004",
    slug = "amb-retry-product",
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
pub struct Amb004;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
