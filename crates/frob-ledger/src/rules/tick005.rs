//! `TICK005`: A committed ledger file or changelog fragment holds a private term.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::{LedgerHost, evaluation_failed};

const ID: &str = "TICK005";

/// A committed ledger file or changelog fragment holds a private term.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TICK005",
    slug = "private-term",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    needs = Lexical,
    scope = Repo,
    body = relay,
    fix = Deterministic,
    applies = project,
    host = LedgerHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tick005;

impl<P: ?Sized + LedgerHost> RelayRule<P> for Tick005 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let view = host.ledger_view();
        if view.missing.is_some() {
            return Vec::new();
        }
        let ledger = match view.open(ID) {
            Ok(Some(ledger)) => ledger,
            Ok(None) => return Vec::new(),
            Err(finding) => return vec![finding],
        };
        let mut found = match ledger.private_term_findings() {
            Ok(found) => found,
            Err(e) => return vec![evaluation_failed(ID, e)],
        };
        if let Ok(rules) = ledger.redaction() {
            found.extend(crate::redact::fragment_findings(
                view.root,
                "changelog.d",
                rules,
            ));
        }
        tracing::debug!(found = found.len(), "TICK005 evaluated");
        found
    }
}
