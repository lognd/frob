//! CI001: An external `uses:` reference is not pinned to a full commit SHA.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// An external `uses:` reference is not pinned to a full commit SHA.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI001",
    slug = "pinned-ref",
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
pub struct Ci001;

gob_rules::list_in_registry!(Ci001, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Ci001 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
