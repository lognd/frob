//! PLAN020: An input-chosen alternative is modeled as an outcome arm.

// frob:ticket 01M6D467K5GSWH3VRBNZM68NSY

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An input-chosen alternative is modeled as an outcome arm.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN020",
    slug = "plan-variant-as-arm",
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
pub struct Plan020;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan020 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
