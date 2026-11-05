//! MDL034: A `one_of exclusive` group whose alternatives overlap.

// frob:ticket 01M6P033KB0H2X52QC73P40F6M

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `one_of exclusive` group whose alternatives overlap.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL034",
    slug = "mdl-exclusive",
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
pub struct Mdl034;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl034 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
