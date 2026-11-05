//! PLAN016: A `retry` repeats a step that is not marked `idempotent`.

// frob:ticket 01M6D467FK4WW4H4HB6NTVM2T5

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `retry` repeats a step that is not marked `idempotent`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN016",
    slug = "plan-retry-hazard",
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
pub struct Plan016;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan016 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
