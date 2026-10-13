//! The proposal fold: which tracker edits are still pending on a ticket (design: `mirror.md` 3.5, `tickets.md` 2a).
//!
//! Proposals are keyed by the tracker's event id, so a re-recorded edit never
//! reopens one that was superseded, accepted, declined or expired.

use std::collections::{BTreeMap, HashMap};

use crate::event::{Event, EventBody, ProposalData};

/// Where a proposal stands after the fold.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProposalState {
    /// Awaiting a decision.
    Pending,
    /// Replaced by a later proposal.
    Superseded,
    /// Accepted into the ticket.
    Accepted,
    /// Declined.
    Declined,
    /// Expired unanswered.
    Expired,
}

/// One proposal with its folded state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Proposal {
    /// The recorded edit.
    pub data: ProposalData,
    /// Its state.
    pub state: ProposalState,
}

/// Fold the proposal events of a ticket: every proposal in first-recorded order, with its state.
///
/// A `supersedes` link and a later proposal for the same (item, field) both
/// supersede an earlier pending one; a closing event wins whatever its order.
pub fn fold_proposals(events: &[Event]) -> Vec<Proposal> {
    let mut ordered: Vec<&Event> = events.iter().collect();
    ordered.sort_by_key(|e| e.order_key());
    let mut closed: HashMap<&str, ProposalState> = HashMap::new();
    let mut out: Vec<Proposal> = Vec::new();
    let mut index: HashMap<&str, usize> = HashMap::new();
    for ev in ordered {
        match &ev.body {
            EventBody::Proposal(d) | EventBody::ProposalSuperseded(d) => {
                if index.contains_key(d.tracker_event.as_str()) {
                    tracing::debug!(key = %d.tracker_event, "duplicate proposal ignored");
                    continue;
                }
                if let Some(prev) = d.supersedes.as_deref() {
                    if let Some(&i) = index.get(prev) {
                        if out[i].state == ProposalState::Pending {
                            out[i].state = ProposalState::Superseded;
                        }
                    } else {
                        closed.entry(prev).or_insert(ProposalState::Superseded);
                    }
                }
                index.insert(&d.tracker_event, out.len());
                out.push(Proposal {
                    data: d.clone(),
                    state: ProposalState::Pending,
                });
            }
            EventBody::ProposalAccepted(c) => {
                closed.insert(&c.tracker_event, ProposalState::Accepted);
            }
            EventBody::ProposalDeclined(c) => {
                closed.insert(&c.tracker_event, ProposalState::Declined);
            }
            EventBody::ProposalExpired(c) => {
                closed.insert(&c.tracker_event, ProposalState::Expired);
            }
            _ => {}
        }
    }
    for p in &mut out {
        if let Some(&s) = closed.get(p.data.tracker_event.as_str()) {
            p.state = s;
        }
    }
    let mut latest: BTreeMap<(&str, &str), usize> = BTreeMap::new();
    for (i, p) in out.iter().enumerate() {
        if p.state == ProposalState::Pending {
            latest.insert((p.data.item.as_str(), p.data.field.as_str()), i);
        }
    }
    let keep: Vec<usize> = latest.into_values().collect();
    for (i, p) in out.iter_mut().enumerate() {
        if p.state == ProposalState::Pending && !keep.contains(&i) {
            p.state = ProposalState::Superseded;
        }
    }
    tracing::debug!(proposals = out.len(), "folded proposals");
    out
}

/// The proposals still pending after the fold: at most one per (item, field).
pub fn pending(events: &[Event]) -> Vec<Proposal> {
    fold_proposals(events)
        .into_iter()
        .filter(|p| p.state == ProposalState::Pending)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event::ProposalCloseData;

    fn data(key: &str, supersedes: Option<&str>) -> ProposalData {
        ProposalData {
            tracker_event: key.into(),
            item: "I_1".into(),
            field: "title".into(),
            actor_id: "42".into(),
            time: "2026-11-01T00:00:00Z".parse().expect("stamp"),
            digest: "d".into(),
            excerpt: "x".into(),
            origin: "tracker".into(),
            supersedes: supersedes.map(str::to_owned),
        }
    }

    fn ev(secs: i64, body: EventBody) -> Event {
        Event::new(gob_time::Stamp::from_unix(1_800_000_000 + secs), "a", body)
    }

    fn close(key: &str) -> ProposalCloseData {
        ProposalCloseData {
            tracker_event: key.into(),
            reason: None,
        }
    }

    fn states(events: &[Event]) -> Vec<(String, ProposalState)> {
        fold_proposals(events)
            .into_iter()
            .map(|p| (p.data.tracker_event, p.state))
            .collect()
    }

    #[test]
    fn a_superseding_proposal_leaves_the_latest_pending() {
        let events = [
            ev(0, EventBody::Proposal(data("t1", None))),
            ev(1, EventBody::ProposalSuperseded(data("t2", Some("t1")))),
        ];
        assert_eq!(
            states(&events),
            vec![
                ("t1".to_owned(), ProposalState::Superseded),
                ("t2".to_owned(), ProposalState::Pending)
            ]
        );
        assert_eq!(pending(&events).len(), 1);
    }

    #[test]
    fn a_closed_proposal_stays_closed_when_its_tracker_event_is_recorded_again() {
        for (body, want) in [
            (
                EventBody::ProposalAccepted(close("t1")),
                ProposalState::Accepted,
            ),
            (
                EventBody::ProposalDeclined(close("t1")),
                ProposalState::Declined,
            ),
            (
                EventBody::ProposalExpired(close("t1")),
                ProposalState::Expired,
            ),
        ] {
            let events = [
                ev(0, EventBody::Proposal(data("t1", None))),
                ev(1, body.clone()),
                ev(2, EventBody::Proposal(data("t1", None))),
            ];
            assert_eq!(states(&events), vec![("t1".to_owned(), want)]);
            assert!(pending(&events).is_empty());
        }
    }

    #[test]
    fn a_close_recorded_before_the_proposal_still_closes_it() {
        let events = [
            ev(0, EventBody::ProposalDeclined(close("t1"))),
            ev(1, EventBody::Proposal(data("t1", None))),
        ];
        assert_eq!(
            states(&events),
            vec![("t1".to_owned(), ProposalState::Declined)]
        );
    }

    #[test]
    fn only_the_latest_pending_per_item_and_field_survives() {
        let events = [
            ev(0, EventBody::Proposal(data("t1", None))),
            ev(1, EventBody::Proposal(data("t2", None))),
        ];
        assert_eq!(
            states(&events),
            vec![
                ("t1".to_owned(), ProposalState::Superseded),
                ("t2".to_owned(), ProposalState::Pending)
            ]
        );
    }
}
