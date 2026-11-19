//! VMOD002: A design artifact satisfies no requirement.

// frob:ticket 01M6PWX1T8YBXB9PE5H21YT2RK

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A design artifact satisfies no requirement.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VMOD002",
    slug = "unjustified-design",
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
pub struct Vmod002;

impl<P: ?Sized + MdlHost> RepoRule<P> for Vmod002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
