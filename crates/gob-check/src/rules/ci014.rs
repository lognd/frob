//! CI014: actionlint rejects the workflow syntax, schema, expression or runner label.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// actionlint rejects the workflow syntax, schema, expression or runner label.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI014",
    slug = "gha-syntax-and-schema",
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
pub struct Ci014;

gob_rules::list_in_registry!(Ci014, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Ci014 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
