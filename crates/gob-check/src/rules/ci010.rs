//! CI010: `actions/checkout` leaves credentials in the workspace.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// `actions/checkout` leaves credentials in the workspace.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI010",
    slug = "checkout-no-persist",
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
pub struct Ci010;

gob_rules::list_in_registry!(Ci010, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Ci010 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
