//! CI006: A dangerous trigger (`pull_request_target`, `workflow_run`) runs with untrusted pull request content.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// A dangerous trigger (`pull_request_target`, `workflow_run`) runs with untrusted pull request content.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI006",
    slug = "no-prt-head-checkout",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci006;

gob_rules::list_in_registry!(Ci006, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Ci006 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
