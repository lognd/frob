//! MDL032: An `unknown` arm that is the only arm, or a known variant has no arm.

// frob:ticket 01M6P033KB0H2X52QC73P40F6M

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An `unknown` arm that is the only arm, or a known variant has no arm.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL032",
    slug = "mdl-unknown-arm",
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
pub struct Mdl032;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl032 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
