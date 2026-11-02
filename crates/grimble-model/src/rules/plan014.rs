//! PLAN014: A step is used nowhere, or a refinement or `one_of` has a single alternative.

// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A step is used nowhere, or a refinement or `one_of` has a single alternative.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN014",
    slug = "plan-dead-structure",
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
pub struct Plan014;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan014 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
