//! The host the declared rules of frob's rule crates run against: [`FrobInputs`] behind one trait.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use std::collections::BTreeSet;

use frob_ack::{AckHost, Inputs};
use frob_lease::{LeaseConfig, LeaseGuard, LeaseStore};
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::{LedgerHost, LedgerView, TicketId};
use frob_obligations::{ObligationHost, ObligationInputs};
use frob_pm::{PmConfig, PmHost};
use frob_tests::TestsHost;
use gob_check::CheckHost;
use gob_directives::{DirectiveHost, DirectiveRecord};
use gob_rules::Finding;
use gob_symbols::SymbolGraph;

use crate::snapshot::FrobInputs;

/// Everything the migrated rule crates ask of frob: obligations, ack, test-coverage, ledger and PM facts, plus the check and directive markers.
pub trait FrobHost:
    ObligationHost + AckHost + TestsHost + LedgerHost + PmHost + CheckHost + DirectiveHost
{
}

impl<
    T: ObligationHost + AckHost + TestsHost + LedgerHost + PmHost + CheckHost + DirectiveHost + ?Sized,
> FrobHost for T
{
}

// frob:ticket 01M55ZW4P41ES0N6HBZ9TQ01YC
/// The check pipeline, tool binders and PROC001 scan produce the CHECK verdicts; the marker only hosts the declarations.
impl CheckHost for FrobInputs {}

/// The directive scanner produces the PARSE and DSL verdicts; the marker only hosts the declarations.
impl DirectiveHost for FrobInputs {}

impl ObligationHost for FrobInputs {
    fn obligations(&self) -> ObligationInputs<'_> {
        FrobInputs::obligations(self)
    }
}

impl AckHost for FrobInputs {
    fn inputs(&self) -> &Inputs {
        &self.ack
    }
}

impl TestsHost for FrobInputs {
    fn directives(&self) -> &[DirectiveRecord] {
        &self.directives
    }

    fn graph(&self) -> &SymbolGraph {
        &self.ack.graph
    }

    fn read_source(&self, path: &str) -> Option<String> {
        std::fs::read_to_string(self.root.join(path)).ok()
    }
}

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP
impl LedgerHost for FrobInputs {
    fn ledger_view(&self) -> LedgerView<'_> {
        LedgerView {
            root: &self.root,
            ledger: self.ledger.as_ref().map(|l| &l.ledger),
            error: self.ledger_error.as_deref(),
            missing: self.ledger_missing.as_deref(),
            milestones: self.ledger.as_ref().map_or(0, |l| l.milestones),
            tickets: self.ledger.as_ref().map_or(0, |l| l.tickets),
            configured: self.ledger.is_some()
                || self.ledger_error.is_some()
                || self.tickets_configured,
        }
    }

    fn doctor_findings(&self) -> Result<Vec<Finding>, String> {
        self.doctor
            .get_or_init(|| match &self.ledger {
                Some(state) => state
                    .ledger
                    .doctor(false)
                    .map(|r| r.findings)
                    .map_err(|e| e.to_string()),
                None => Ok(Vec::new()),
            })
            .clone()
    }
}

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP
impl PmHost for FrobInputs {
    fn pm_config(&self) -> Result<PmConfig, String> {
        PmConfig::load(&self.root).map_err(|e| e.to_string())
    }

    fn live_leases(&self) -> Option<BTreeSet<TicketId>> {
        let state = self.ledger.as_ref()?;
        let cfg = self.lease_config().unwrap_or_else(|err| {
            tracing::warn!(%err, "lease config unreadable; default used for PM013 liveness");
            LeaseConfig::default()
        });
        match LeaseStore::open(state.ledger.repo(), cfg, state.ledger.clock().clone())
            .and_then(|s| s.live_snapshot())
        {
            Ok(live) => Some(live.into_iter().map(|l| l.ticket).collect()),
            Err(err) => {
                tracing::warn!(%err, "leases unreadable; PM013 counts every in-progress ticket");
                None
            }
        }
    }

    fn lease_check(&self) -> Box<dyn LeaseCheck + '_> {
        let Some(state) = self.ledger.as_ref() else {
            return Box::new(NoLeases);
        };
        let guard = self
            .lease_config()
            .and_then(|c| {
                frob_lease::open_store(&self.root, c, state.ledger.clock().clone())
                    .map_err(|e| e.to_string())
            })
            .and_then(|(store, _)| LeaseGuard::new(store).map_err(|e| e.to_string()));
        match guard {
            Ok(g) => Box::new(g),
            Err(msg) => {
                tracing::warn!(error = %msg, "lease check unavailable; PM033 counts every doable ticket");
                Box::new(NoLeases)
            }
        }
    }
}

impl FrobInputs {
    /// The caller's lease settings, else those of `frob.toml`.
    fn lease_config(&self) -> Result<LeaseConfig, String> {
        match &self.lease {
            Some(c) => Ok(c.clone()),
            None => LeaseConfig::load(&self.root).map_err(|e| e.to_string()),
        }
    }
}
