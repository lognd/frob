//! AMB007: A mapped domain error is converted to a panic by the bound unit.

// frob:ticket 01M6P033P70RJ9JZJ5NWV5AWNB

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A mapped domain error is converted to a panic by the bound unit.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB007",
    slug = "amb-domain-panic",
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
pub struct Amb007;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb007 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
