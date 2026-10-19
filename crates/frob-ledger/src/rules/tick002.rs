//! `TICK002`: A ticket id is referenced but absent from the base ref.

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::LedgerHost;

/// A ticket id is referenced but absent from the base ref.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TICK002",
    slug = "ticket-not-on-base",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = LedgerHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tick002;

/// The finding is raised by the `--ticket` scope, which reads the base ref; this declaration registers the id.
impl<P: ?Sized + LedgerHost> RepoRule<P> for Tick002 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}

    fn inapplicable(&self, host: &P) -> Option<String> {
        let view = host.ledger_view();
        if view.missing.is_some() {
            // The absent ledger is reported once by TICK001, not as zero-subject verdicts.
            return Some("ledger ref is absent".to_owned());
        }
        if !view.configured {
            return Some("no ticket ledger in this repository".to_owned());
        }
        // Without a loaded ledger (or any ticket) there is nothing a reference could be missing from.
        (view.tickets == 0).then(|| "no tickets in the ledger to compare against".to_owned())
    }
}

impl<P: ?Sized + LedgerHost> Measured<P> for Tick002 {
    fn subjects(&self, host: &P) -> usize {
        host.ledger_view().tickets
    }
}
