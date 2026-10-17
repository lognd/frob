//! TOOL002: A bound tool reported a finding that no frob rule id covers.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// A bound tool reported a finding that no frob rule id covers.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOOL002",
    slug = "tool-finding-unmapped",
    severity = Advisory,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tool002;

gob_rules::list_in_registry!(Tool002, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Tool002 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
