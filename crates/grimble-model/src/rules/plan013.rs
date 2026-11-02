//! PLAN013: An `impl STEP for *` covers a step that no scenario uses.

// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An `impl STEP for *` covers a step that no scenario uses.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN013",
    slug = "plan-unused-wildcard-impl",
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
pub struct Plan013;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan013 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
