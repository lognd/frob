//! `REL002`: the workspace crates and the wheel do not share one version.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use frob_ledger::LedgerHost;
use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

/// Crates or the wheel whose version differs from the workspace version.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "REL002",
    slug = "lockstep-version-mismatch",
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
pub struct Rel002;

impl<P: ?Sized + LedgerHost> RelayRule<P> for Rel002 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        crate::rel002::evaluate(host.ledger_view().root).findings
    }
}
