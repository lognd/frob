//! The forecast line shared by `ticket show` and `release status`, both computed by one function.
//!
//! Gathers ticket facts and the blocked-by chain from the ledger and hands them to
//! `frob_metrics::forecast`, so the two surfaces can never disagree about a date.

// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use std::collections::BTreeSet;

use frob_ledger::model::{Category, LinkKind};
use frob_ledger::{Ledger, TicketId};
use frob_metrics::forecast::{
    DEFAULT_SEED, ForecastInput, TRIALS, forecast, forecast_line, longest_chain, workload,
};
use gob_cli::CliError;

use crate::stats_cmd::ticket_facts;
use crate::ticket::cli_err;

/// The one-line forecast for finishing `ids` and the open tickets that block them; Unresolved below `min_history`.
pub(crate) fn forecast_line_for(
    ledger: &Ledger,
    ids: &[TicketId],
    min_history: u32,
) -> Result<String, CliError> {
    let (open, edges) = open_closure(ledger, ids)?;
    let facts = ticket_facts(ledger, None)?;
    let chain = longest_chain(&edges);
    tracing::debug!(
        open = open.len(),
        edges = edges.len(),
        chain,
        "forecast inputs"
    );
    let fig = forecast(&ForecastInput {
        work: workload(&facts, &open, chain),
        facts: &facts,
        now: ledger.clock().now().unix(),
        min_history,
        seed: DEFAULT_SEED,
        trials: TRIALS,
    });
    Ok(forecast_line(&fig))
}

/// Open handles plus `(ticket, blocker)` handle pairs.
type Closure = (Vec<String>, Vec<(String, String)>);

/// The open handles reachable from `ids` through blocked-by links, and those links as `(ticket, blocker)` handle pairs.
fn open_closure(ledger: &Ledger, ids: &[TicketId]) -> Result<Closure, CliError> {
    let mut seen: BTreeSet<TicketId> = BTreeSet::new();
    let mut queue: Vec<TicketId> = ids.to_vec();
    let (mut open, mut edges) = (Vec::new(), Vec::new());
    while let Some(id) = queue.pop() {
        if !seen.insert(id) {
            continue;
        }
        let view = ledger.show(id).map_err(cli_err)?;
        if view.summary.category == Category::Done {
            continue;
        }
        open.push(view.summary.handle.clone());
        for l in view
            .outgoing
            .iter()
            .filter(|l| l.kind == LinkKind::BlockedBy)
        {
            if l.category == Some(Category::Done) {
                continue;
            }
            if let Some(h) = &l.handle {
                edges.push((view.summary.handle.clone(), h.clone()));
                queue.push(l.id);
            }
        }
    }
    Ok((open, edges))
}
