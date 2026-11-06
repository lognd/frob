//! `PM037`: a design obligation with no live implementing ticket (pm-and-releases.md 10.3).
//!
//! The pure core [`pm037`] takes the grimble graph and the overlay computed by
//! [`frob_ledger::design::overlay`]; [`evaluate`] reads the ledger's `implements` links for `frob-check`.
//! It stays silent until some live ticket carries an `implements` link, so a repo that has not adopted
//! the planning join sees nothing.

// frob:ticket 01M4FDBDC401KMNN4C12QTA3PK

use std::collections::BTreeSet;

use frob_ledger::Ledger;
use frob_ledger::design::{DesignGraph, Overlay, overlay};
use gob_rules::{Finding, RuleId, Severity};

use crate::eval::id_of;
use crate::rules::pm037::Pm037;
use crate::rules::pm039::Pm039;

fn rule_id() -> RuleId {
    id_of::<Pm037>()
}

/// What `PM039` needs about one ticket closed `done`: the entities it implements and what its landed diff touched.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LandedDesign {
    /// The ticket handle for the message, such as `~5JKQ2BP`.
    pub ticket: String,
    /// Each implemented entity anchor with the code identities (symrefs) bound to it.
    pub entities: Vec<(String, BTreeSet<String>)>,
    /// The code identities (symrefs) the landed diff touches.
    pub touched: BTreeSet<String>,
}

/// Flag every landed ticket whose diff touches none of the identities bound to the entities it implements.
///
/// A ticket whose implemented entities have no bound identity at all is skipped: there is nothing to compare against.
pub fn pm039(landed: &[LandedDesign]) -> Vec<Finding> {
    let mut out = Vec::new();
    for t in landed {
        let bound: BTreeSet<&String> = t.entities.iter().flat_map(|(_, ids)| ids).collect();
        if bound.is_empty() {
            tracing::debug!(ticket = %t.ticket, "PM039: no bound identities to compare");
            continue;
        }
        if t.touched.iter().any(|id| bound.contains(id)) {
            continue;
        }
        let anchors: Vec<&str> = t.entities.iter().map(|(a, _)| a.as_str()).collect();
        tracing::debug!(ticket = %t.ticket, ?anchors, "PM039: done ticket touched none of its bound identities");
        out.push(Finding::new(
            id_of::<Pm039>(),
            Severity::Error,
            None,
            format!(
                "ticket {} closed done but its landed diff touches none of the identities bound to {}; bind the code it changed with `grimble:binds`, or fix the `implements` link",
                t.ticket,
                anchors.join(", ")
            ),
            &t.ticket,
        ));
    }
    out
}

/// Flag every obligation anchor of `graph` that no live ticket implements; one finding per anchor.
pub fn pm037(
    graph: &DesignGraph,
    links: &[(frob_ledger::design::TicketFacts, Vec<String>)],
) -> Vec<Finding> {
    let state = overlay(graph, links);
    let mut seen = BTreeSet::new();
    let mut out = Vec::new();
    for ob in graph.obligations() {
        let unplanned = state
            .get(&ob.anchor)
            .is_some_and(|o| o.state == Overlay::Unplanned);
        if !unplanned || !seen.insert(ob.anchor.clone()) {
            continue;
        }
        tracing::debug!(anchor = %ob.anchor, kind = %ob.kind, "PM037: obligation without a ticket");
        out.push(Finding::new(
            rule_id(),
            Severity::Error,
            None,
            format!(
                "design obligation `{}` on `{}` has no implementing ticket; run `frob plan --from-design --apply` or create one with `--implements design:{}`",
                ob.kind, ob.anchor, ob.anchor
            ),
            &format!("design:{}", ob.anchor),
        ));
    }
    out
}

/// Read the `implements` links from `ledger` and run [`pm037`]; empty when no live ticket implements anything.
///
/// # Errors
///
/// The ledger read failure rendered as text.
pub fn evaluate(ledger: &Ledger, graph: &DesignGraph) -> Result<Vec<Finding>, String> {
    let links = ledger.design_links().map_err(|e| e.to_string())?;
    if !links.iter().any(|(facts, _)| facts.is_live()) {
        tracing::debug!("PM037: no ticket uses implements; planning join not in use");
        return Ok(Vec::new());
    }
    let out = pm037(graph, &links);
    tracing::info!(findings = out.len(), "PM037 evaluated");
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_ledger::TicketId;
    use frob_ledger::design::TicketFacts;
    use frob_ledger::model::Category;

    const GRAPH: &str = r#"{"schema":"grimble.graph/1","entities":[{"anchor":"impl/a.b","kind":"impl","status":"declared","status_hi":null,"name":"B"},{"anchor":"impl/a.c","kind":"impl","status":"declared","status_hi":null,"name":"C"}],"obligations":[{"rule":"PLAN001","kind":"unbound_impl","anchor":"impl/a.b","detail":"d"},{"rule":"PLAN001","kind":"unbound_impl","anchor":"impl/a.c","detail":"d"}],"edges":[]}"#;

    // frob:tests crates/frob-pm/src/eval/design.rs::pm037
    #[test]
    fn an_obligation_without_a_ticket_fires_and_a_planned_one_does_not() {
        let graph = DesignGraph::from_json(GRAPH).expect("graph");
        let facts = TicketFacts {
            id: TicketId::mint(),
            category: Category::Todo,
            outcome: None,
        };
        let found = pm037(&graph, &[(facts, vec!["design:impl/a.b".to_owned()])]);
        assert_eq!(found.len(), 1);
        assert!(found[0].message.contains("impl/a.c"));
    }

    // frob:tests crates/frob-pm/src/eval/design.rs::pm039
    #[test]
    fn a_done_ticket_that_touched_no_bound_identity_warns() {
        let ids = |v: &[&str]| v.iter().map(|s| (*s).to_owned()).collect::<BTreeSet<_>>();
        let landed = |touched: &[&str], bound: &[&str]| LandedDesign {
            ticket: "~T".to_owned(),
            entities: vec![("impl/a.b".to_owned(), ids(bound))],
            touched: ids(touched),
        };
        let found = pm039(&[landed(&["x::y"], &["a::b"])]);
        assert_eq!(found.len(), 1);
        assert!(found[0].message.contains("impl/a.b"));
        assert!(pm039(&[landed(&["a::b"], &["a::b"])]).is_empty());
        assert!(pm039(&[landed(&["x::y"], &[])]).is_empty());
    }
}
