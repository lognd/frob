//! PLAN015: A `sorry` hole stands in for a scenario tail.

// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `sorry` hole stands in for a scenario tail.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN015",
    slug = "plan-sorry-hole",
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
pub struct Plan015;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan015 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
