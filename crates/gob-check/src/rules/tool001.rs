//! TOOL001: A configured tool stage (`[[check.tool]]`) exited nonzero, timed out or could not start.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{Out, RepoRule, rule};

use crate::host::CheckHost;

/// A configured tool stage (`[[check.tool]]`) exited nonzero, timed out or could not start.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOOL001",
    slug = "tool-stage-failed",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tool001;

gob_rules::list_in_registry!(Tool001, "frob");

impl<P: ?Sized + CheckHost> RepoRule<P> for Tool001 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
