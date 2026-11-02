//! PLAN018: No alternative of a `one_of` is realized by any scenario.

// frob:ticket 01M6CKH5QRMZWZVDBEF49S8FVJ

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// No alternative of a `one_of` is realized by any scenario.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN018",
    slug = "plan-unrealized-one-of",
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
pub struct Plan018;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan018 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
