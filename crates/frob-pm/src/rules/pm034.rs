//! `PM034`: a ticket claims a milestone that its epic ancestry does not reach.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{PmHost, relay_pm};

/// Why this rule is not applicable when the ledger holds no milestone objects.
const NO_MILESTONES: &str = "no milestone objects in this repository";

/// A ticket claims a milestone that its epic ancestry does not reach.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PM034",
    slug = "milestone-member-outside-epics",
    severity = Warn,
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
pub struct Pm034;

impl<P: ?Sized + PmHost> RelayRule<P> for Pm034 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        relay_pm(host, "PM034", |ledger| {
            crate::eval::membership::evaluate(ledger)
                .map(|e| e.findings)
                .map_err(|e| e.to_string())
        })
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        let view = host.ledger_view();
        // An unreadable ledger is applicable: its failure must surface, not hide as "not applicable".
        (view.error.is_none() && view.milestones == 0).then(|| NO_MILESTONES.to_owned())
    }
}
