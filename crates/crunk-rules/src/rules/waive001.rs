//! WAIVE001: a `crunk:waive` comment without a reason (port of `crunk/rules/_waive.py` `waive001`).
//!
//! Divergence from the Python rule: there a reasonless waiver still silenced its rule and WAIVE001
//! was the separate nag. Here the waiver is an `accept` exception (D120) and an exception without
//! a reason is not granted, so the finding it was meant to hide stays visible next to WAIVE001.
//! A blank `reason=""` counts as missing (Python accepted it). WAIVE001 is in a family that is
//! not waivable, so a reasonless waiver cannot silence the check that exists to catch it.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::host::CrunkHost;
use crate::waiver::scan;

/// A `crunk:waive` comment that gives no reason.
#[rule(
    id = "WAIVE001",
    slug = "waiver-without-reason",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Waive001;

impl<P: ?Sized + CrunkHost> FileRule<P> for Waive001 {
    fn check(&self, cx: &FileCx<'_, P>, out: &mut Out<'_, Self>) {
        for waiver in scan(cx.text).into_iter().filter(|w| w.reason.is_none()) {
            tracing::debug!(rule = %waiver.rule, line = waiver.line, "WAIVE001: waiver has no reason");
            out.fire(
                waiver.offset,
                format!("waiver for {} has no reason", waiver.rule),
            );
        }
    }
}
