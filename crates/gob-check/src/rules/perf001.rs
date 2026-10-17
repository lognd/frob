//! PERF001: The built-in stages of a check run took longer than the `[perf]` budget.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{Out, RepoRule, rule};

use crate::host::CheckHost;

/// The built-in stages of a check run took longer than the `[perf]` budget.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PERF001",
    slug = "check-over-budget",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Perf001;

gob_rules::list_in_registry!(Perf001, "frob");

impl<P: ?Sized + CheckHost> RepoRule<P> for Perf001 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
