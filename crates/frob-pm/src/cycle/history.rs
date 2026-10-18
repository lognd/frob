//! Cycle history readers: the recorded events, member facts and per-cycle deliveries the capacity rules share.
//!
//! `cycle assign`, `cycle velocity`, `cycle close` and the `PM010` evaluator
//! all need the same reading of a cycle's past, so it lives here once.

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use std::collections::BTreeMap;

use frob_ledger::Ledger;
use frob_ledger::model::{Category, Outcome as TicketOutcome, TicketType};

use crate::cycle::lifecycle::{MemberFacts, MemberStatus};
use crate::cycle::velocity::{Delivery, delivery};
use crate::error::PmError;
use crate::event::{CycleEventData, CycleOp, PmBody, PmEvent};
use crate::model::{Cycle, ObjectId, ObjectKind, State};
use crate::store::PmStore;

/// The `cycle` events of `c` in fold order; unreadable history is logged and treated as empty.
pub fn review_events(store: PmStore<'_>, c: &Cycle) -> Vec<CycleEventData> {
    let read = store
        .ledger()
        .tip_hex()
        .map_err(PmError::from)
        .and_then(|tip| {
            tip.map_or(Ok(Vec::new()), |t| {
                store.read_events_at(&t, ObjectKind::Cycle, c.id)
            })
        });
    match read {
        Ok(events) => events
            .into_iter()
            .filter_map(|e: PmEvent| match e.body {
                PmBody::Cycle(d) => Some(*d),
                _ => None,
            })
            .collect(),
        Err(e) => {
            tracing::warn!(cycle = %c.id, error = %e, "cycle events unreadable");
            Vec::new()
        }
    }
}

/// A member's standing from its category and outcome.
pub const fn member_status(category: Category, outcome: Option<TicketOutcome>) -> MemberStatus {
    match (category, outcome) {
        (Category::Done, Some(TicketOutcome::Fixed | TicketOutcome::Done)) => {
            MemberStatus::Finished
        }
        (Category::Done, _) => MemberStatus::Dropped,
        (Category::InProgress, _) => MemberStatus::InProgress,
        _ => MemberStatus::Open,
    }
}

/// The delivery of every closed cycle, by the close-time definition: the recorded ratio event, else the finished members.
pub fn deliveries(
    store: PmStore<'_>,
    ledger: &Ledger,
    all: &[Cycle],
) -> BTreeMap<ObjectId, Delivery> {
    all.iter()
        .filter(|c| c.state == State::Closed)
        .map(|c| {
            let recorded = review_events(store, c)
                .into_iter()
                .rev()
                .find(|d| d.op == CycleOp::Ratio)
                .and_then(|d| d.committed.zip(d.done));
            let members: Vec<MemberFacts> = c
                .tickets
                .iter()
                .filter_map(|id| match ledger.show(*id) {
                    Ok(v) => Some(MemberFacts {
                        id: *id,
                        handle: v.summary.handle,
                        status: member_status(v.summary.category, v.summary.outcome),
                        live_lease: false,
                        points: u32::from(v.summary.points.unwrap_or(0)),
                    }),
                    Err(e) => {
                        tracing::warn!(ticket = %id, error = %e, "member ticket unreadable; not counted");
                        None
                    }
                })
                .collect();
            (c.id, delivery(recorded, &members))
        })
        .collect()
}

/// Done points per closed cycle, the input of velocity and capacity.
pub fn done_points(deliveries: &BTreeMap<ObjectId, Delivery>) -> BTreeMap<ObjectId, u32> {
    deliveries.iter().map(|(id, d)| (*id, d.done)).collect()
}

/// The `(type, points)` of every member of `c`; unreadable members are logged and skipped.
pub fn member_points(ledger: &Ledger, c: &Cycle) -> Vec<(TicketType, u32)> {
    c.tickets
        .iter()
        .filter_map(|id| match ledger.show(*id) {
            Ok(v) => Some((v.summary.ty, u32::from(v.summary.points.unwrap_or(0)))),
            Err(e) => {
                tracing::warn!(ticket = %id, error = %e, "member ticket unreadable; not counted");
                None
            }
        })
        .collect()
}
