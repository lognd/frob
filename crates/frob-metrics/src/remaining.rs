//! Points remaining: open work by milestone and by epic, a count rather than a statistic so it is never gated.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use std::collections::BTreeMap;

use schemars::JsonSchema;
use serde::Serialize;

use crate::report::{TicketFact, TicketState};

/// Open work under one milestone or epic.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct RemainingRow {
    /// Milestone version or epic handle.
    pub name: String,
    /// Estimated points not yet done.
    pub points: u32,
    /// Open tickets (estimated or not).
    pub tickets: u32,
    /// Open tickets without an estimate, whose points are not in `points`.
    pub unestimated: u32,
}

/// Points remaining overall, by milestone and by epic.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Remaining {
    /// Totals over every open ticket.
    pub total: RemainingRow,
    /// One row per milestone, by version.
    pub by_milestone: Vec<RemainingRow>,
    /// One row per epic that has open children, by handle.
    pub by_epic: Vec<RemainingRow>,
}

/// Add one open ticket to `row`.
fn add(row: &mut RemainingRow, fact: &TicketFact) {
    row.tickets += 1;
    match fact.points {
        Some(p) => row.points += p,
        None => row.unestimated += 1,
    }
}

/// An empty row named `name`.
fn empty(name: &str) -> RemainingRow {
    RemainingRow {
        name: name.to_owned(),
        points: 0,
        tickets: 0,
        unestimated: 0,
    }
}

/// Remaining open work; `milestones` pairs each version with the handles of its epics.
pub fn remaining(facts: &[TicketFact], milestones: &[(String, Vec<String>)]) -> Remaining {
    let open: Vec<&TicketFact> = facts
        .iter()
        .filter(|f| f.state == TicketState::Open)
        .collect();
    let mut total = empty("total");
    let mut epics: BTreeMap<&str, RemainingRow> = BTreeMap::new();
    for f in &open {
        add(&mut total, f);
        if let Some(epic) = f.parent.as_deref() {
            add(epics.entry(epic).or_insert_with(|| empty(epic)), f);
        }
    }
    let mut by_milestone: Vec<RemainingRow> = milestones
        .iter()
        .map(|(version, members)| {
            let mut row = empty(version);
            for f in &open {
                if f.parent.as_ref().is_some_and(|p| members.contains(p)) {
                    add(&mut row, f);
                }
            }
            row
        })
        .collect();
    by_milestone.sort_by(|a, b| a.name.cmp(&b.name));
    tracing::debug!(open = open.len(), epics = epics.len(), "points remaining");
    Remaining {
        total,
        by_milestone,
        by_epic: epics.into_values().collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fact(
        handle: &str,
        points: Option<u32>,
        state: TicketState,
        parent: Option<&str>,
    ) -> TicketFact {
        TicketFact {
            handle: handle.to_owned(),
            points,
            state,
            parent: parent.map(str::to_owned),
            created: 0,
            started: None,
            done_at: None,
            tokens: None,
        }
    }

    #[test]
    fn remaining_sums_open_points_by_epic_and_milestone() {
        // frob:tests crates/frob-metrics/src/remaining.rs::remaining
        let facts = [
            fact("~A", Some(3), TicketState::Open, Some("~E1")),
            fact("~B", Some(5), TicketState::Open, Some("~E1")),
            fact("~C", None, TicketState::Open, Some("~E2")),
            fact("~D", Some(8), TicketState::Finished, Some("~E1")),
            fact("~F", Some(2), TicketState::Dropped, Some("~E2")),
        ];
        let ms = [("0.1.0".to_owned(), vec!["~E1".to_owned()])];
        let r = remaining(&facts, &ms);
        assert_eq!(
            (r.total.points, r.total.tickets, r.total.unestimated),
            (8, 3, 1)
        );
        assert_eq!(r.by_milestone[0].points, 8);
        assert_eq!(r.by_milestone[0].tickets, 2);
        assert_eq!(r.by_epic.len(), 2);
        assert_eq!(r.by_epic[1].unestimated, 1);
    }
}
