//! `PM039`: a ticket closed `done` whose landed diff touches none of the identities bound to what it implements.

// frob:ticket 01M6PJTS0C0E4G01XPY5JKQ2BP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::PmHost;

/// A ticket closed done without touching anything bound to the design it implements.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM039",
    slug = "done-untouched",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = PmHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Pm039;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm039 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let Some(landed) = host.landed_design() else {
            tracing::debug!("PM039: host supplies no landed design facts; skipped");
            return Vec::new();
        };
        let out = crate::eval::design::pm039(&landed);
        tracing::info!(findings = out.len(), "PM039 evaluated");
        out
    }
}
