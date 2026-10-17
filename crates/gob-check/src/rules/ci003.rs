//! CI003: A workflow or job grants a broader `GITHUB_TOKEN` scope than it needs.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// A workflow or job grants a broader `GITHUB_TOKEN` scope than it needs.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI003",
    slug = "no-top-level-write",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci003;

gob_rules::list_in_registry!(Ci003, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Ci003 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
