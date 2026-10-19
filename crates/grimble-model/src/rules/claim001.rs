//! CLAIM001: A claim's proposition is refuted by the declared flows, with the witness path.

// frob:ticket 01M4FGYHSXQXJD0JXFV2AZCED5

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A claim's proposition is refuted by the declared flows, with the witness path.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CLAIM001",
    slug = "claim-refuted",
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
pub struct Claim001;

impl<P: ?Sized + MdlHost> RepoRule<P> for Claim001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
