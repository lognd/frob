//! SYS015: A consecutive step-use pair across two nodes has no declared flow.

// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A consecutive step-use pair across two nodes has no declared flow.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS015",
    slug = "sys-behavior-flow",
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
pub struct Sys015;

impl<P: ?Sized + MdlHost> RepoRule<P> for Sys015 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
