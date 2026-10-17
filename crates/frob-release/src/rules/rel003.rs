//! `REL003`: a changelog fragment is missing for the ticket under check, or does not validate.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use frob_ledger::LedgerHost;
use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::rel003::{evaluate, fragment_required, not_applicable};

/// A changelog fragment that is missing for the checked ticket or that fails validation.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "REL003",
    slug = "changelog-fragment-required",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = LedgerHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Rel003;

impl<P: ?Sized + LedgerHost> RelayRule<P> for Rel003 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let view = host.ledger_view();
        let Some(ledger) = view.ledger else {
            tracing::info!("REL003: no ledger; fragment ULIDs cannot be resolved");
            return Vec::new();
        };
        let resolver = |ulid: &str| -> Option<String> {
            let id: frob_ledger::TicketId = ulid.parse().ok()?;
            ledger.show(id).ok().map(|v| v.summary.handle)
        };
        evaluate(view.root, &resolver).findings
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        let root = host.ledger_view().root;
        not_applicable(root, fragment_required(root))
    }
}
