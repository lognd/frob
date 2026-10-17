//! CI007: A `run:` script interpolates an expression an attacker can influence.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CheckHost;

/// A `run:` script interpolates an expression an attacker can influence.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI007",
    slug = "no-event-interpolation-in-run",
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
pub struct Ci007;

gob_rules::list_in_registry!(Ci007, "frob");

impl<P: ?Sized + CheckHost> FileRule<P> for Ci007 {
    /// The verdict is computed by the check pipeline (tools, perf, read); see the module doc.
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}
