//! MDL004: A pack is not enabled, not under `packs/`, or its version or digest differs from the pin.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A pack is not enabled, not under `packs/`, or its version or digest differs from the pin.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL004",
    slug = "mdl-unknown-pack",
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
pub struct Mdl004;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl004 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
