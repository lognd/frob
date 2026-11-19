//! VMOD001: A requirement is satisfied by no design artifact.

// frob:ticket 01M6PWX1T8YBXB9PE5H21YT2RK

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A requirement is satisfied by no design artifact.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "VMOD001",
    slug = "orphan-requirement",
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
pub struct Vmod001;

impl<P: ?Sized + MdlHost> RepoRule<P> for Vmod001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
