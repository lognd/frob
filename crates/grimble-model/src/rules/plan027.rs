//! PLAN027: A scenario realizes a `non_goal` of its system.

// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A scenario realizes a `non_goal` of its system.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN027",
    slug = "plan-realized-non-goal",
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
pub struct Plan027;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan027 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
