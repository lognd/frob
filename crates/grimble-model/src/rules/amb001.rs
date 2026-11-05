//! AMB001: A system declares no ambient policy.

// frob:ticket 01M6P033P70RJ9JZJ5NWV5AWNB

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A system declares no ambient policy.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB001",
    slug = "amb-policy-missing",
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
pub struct Amb001;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
