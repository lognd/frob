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
use gob_directives::DirectiveRecord;
use gob_rules::{Baseline, BaselineHost, Finding, TicketLife};
use gob_symbols::SymbolGraph;

use crate::snapshot::FrobInputs;

/// Everything the migrated rule crates ask of frob: obligations, ack, test-coverage, ledger and PM facts.
pub trait FrobHost: ObligationHost + AckHost + TestsHost + LedgerHost + PmHost + BaselineHost {}

impl<T: ObligationHost + AckHost + TestsHost + LedgerHost + PmHost + BaselineHost + ?Sized> FrobHost
    for T
{
}

impl ObligationHost for FrobInputs {
    fn obligations(&self) -> ObligationInputs<'_> {
        FrobInputs::obligations(self)
    }

    // frob:ticket 01M561ZF9TSJF59M2CAXW3KTP0
    fn has_test_capable_files(&self) -> bool {
        self.test_capable_files > 0
    }

    // frob:ticket 01M561ZF9TSJF59M2CAXW3KTP0
    fn ledger_facts(&self) -> Option<LedgerView<'_>> {
        Some(LedgerHost::ledger_view(self))
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
        self.test_sources.get(path).cloned()
    }

    // frob:ticket 01M4P2N1XMDZAGS1EAZPR6WQMQ
    fn repo_root(&self) -> Option<&std::path::Path> {
        Some(&self.root)
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
    fn design_graph(&self) -> Option<frob_ledger::design::DesignGraph> {
        match frob_ledger::design::DesignGraph::load(&self.root) {
            Ok(graph) => Some(graph),
            Err(err) => {
                tracing::debug!(%err, "no design graph; PM037 skipped");
                None
            }
        }
    }

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
            // frob:ticket 01M4H5Y68GYFTMG9Y73F696589
            // Queued leases hold no worktree, so they hold no in-progress slot.
            Ok(live) => Some(
                live.into_iter()
                    .filter(|l| !l.queued)
                    .map(|l| l.ticket)
                    .collect(),
            ),
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

// frob:ticket 01M7KME88Y8N7JD506Y0WRG2MX
impl BaselineHost for FrobInputs {
    fn baseline_head(&self) -> Option<&Baseline> {
        self.baseline_head.as_ref()
    }

    fn baseline_base(&self) -> Option<&Baseline> {
        self.baseline_base.as_ref()
    }

    fn ticket_life(&self, ticket: &str) -> TicketLife {
        let Some(state) = &self.ledger else {
            return TicketLife::Unknown;
        };
        life_in(&state.ledger, ticket)
    }
}

/// Liveness of `ticket` in `ledger`: open is live, done is live only through a live supersession link, absent is unknown.
fn life_in(ledger: &frob_ledger::Ledger, ticket: &str) -> TicketLife {
    let Ok(id) = ledger.resolve(ticket) else {
        tracing::debug!(ticket, "baseline ticket not in the ledger");
        return TicketLife::Unknown;
    };
    let Ok(view) = ledger.show(id) else {
        return TicketLife::Unknown;
    };
    if !view.summary.category.is_terminal() {
        return TicketLife::Live;
    }
    let successor_live = view
        .outgoing
        .iter()
        .chain(&view.incoming)
        .filter(|l| l.kind == frob_ledger::model::LinkKind::SupersededBy)
        .any(|l| l.category.is_some_and(|c| !c.is_terminal()));
    if successor_live {
        TicketLife::Live
    } else {
        TicketLife::Dead
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
