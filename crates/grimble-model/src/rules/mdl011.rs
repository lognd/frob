//! MDL011: A `part of` name differs from the root `module`, two roots share a module name, or an included file declares `module`.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `part of` name differs from the root `module`, two roots share a module name, or an included file declares `module`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL011",
    slug = "mdl-module",
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
pub struct Mdl011;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl011 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
