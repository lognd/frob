//! Exit-criterion binding: which evidence records bind which criterion of a milestone.
//!
//! The ticket rule (tickets.md section 9), applied to milestone events: an
//! evidence event counts for criterion N as numbered when it was written,
//! carried through later removals (nothing if N was removed); within one
//! (provider, ref, criterion) the latest record in fold order decides and binds
//! only when measured and not failed ([`frob_ledger::fold::evidence_passes`]).

use std::collections::BTreeMap;

use frob_ledger::EventId;
use frob_ledger::event::EvidenceData;

use crate::error::Result;
use crate::event::{CriterionData, Op, PmBody, PmEvent, sort_events};
use crate::model::{ObjectId, ObjectKind};
use crate::store::PmStore;

/// A passing evidence record that binds a criterion.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Binding {
    /// The evidence event id.
    pub event: EventId,
    /// The provider that measured it.
    pub provider: String,
    /// What was measured (the record's `ref`).
    pub reference: String,
}

/// Where criterion `n` (numbered when evidence `since` was written) sits after later removals; `None` when removed.
pub(crate) fn remap(ordered: &[&PmEvent], since: &PmEvent, n: usize) -> Option<usize> {
    let mut now = n;
    for ev in ordered.iter().skip_while(|e| e.id != since.id).skip(1) {
        if let PmBody::Criterion(CriterionData {
            op: Op::Remove,
            position: Some(p),
            ..
        }) = &ev.body
        {
            match now.cmp(p) {
                std::cmp::Ordering::Equal => return None,
                std::cmp::Ordering::Greater => now -= 1,
                std::cmp::Ordering::Less => {}
            }
        }
    }
    Some(now)
}

/// A string key of an evidence record (`provider`, `ref`), empty when absent.
fn key(data: &EvidenceData, name: &str) -> String {
    data.record
        .get(name)
        .and_then(toml::Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

/// The passing records binding each of the final `count` criteria, indexed by position - 1.
///
/// `ordered` must be in fold order. A criterion is bound when this list is non-empty.
pub(crate) fn bindings_of(ordered: &[&PmEvent], count: usize) -> Vec<Vec<Binding>> {
    type Slot = (String, String, usize);
    let mut latest: BTreeMap<Slot, (EventId, bool)> = BTreeMap::new();
    for ev in ordered {
        let PmBody::Evidence(data) = &ev.body else {
            continue;
        };
        let passes = frob_ledger::fold::evidence_passes(data);
        let (provider, reference) = (key(data, "provider"), key(data, "ref"));
        for n in data.accepts.iter().filter_map(|n| remap(ordered, ev, *n)) {
            latest.insert((provider.clone(), reference.clone(), n), (ev.id, passes));
        }
    }
    let mut out = vec![Vec::new(); count];
    for ((provider, reference, n), (event, passes)) in latest {
        if passes && (1..=count).contains(&n) {
            out[n - 1].push(Binding {
                event,
                provider,
                reference,
            });
        }
    }
    out
}

/// The passing records binding each of `count` criteria, folding `events` first.
pub fn bindings(events: &[PmEvent], count: usize) -> Vec<Vec<Binding>> {
    let mut sorted = events.to_vec();
    sort_events(&mut sorted);
    let refs: Vec<&PmEvent> = sorted.iter().collect();
    bindings_of(&refs, count)
}

impl PmStore<'_> {
    /// The evidence binding each exit criterion of milestone `id` at the current tip.
    ///
    /// # Errors
    ///
    /// Ledger read failures or a malformed event file.
    pub fn criterion_bindings(self, id: ObjectId, count: usize) -> Result<Vec<Vec<Binding>>> {
        let Some(tip) = self.ledger.tip_hex()? else {
            return Ok(vec![Vec::new(); count]);
        };
        let events = self.read_events_at(&tip, ObjectKind::Milestone, id)?;
        Ok(bindings(&events, count))
    }

    /// Every evidence event of milestone `id` at the current tip, in fold order.
    ///
    /// # Errors
    ///
    /// Ledger read failures or a malformed event file.
    pub fn evidence_events(self, id: ObjectId) -> Result<Vec<(PmEvent, EvidenceData)>> {
        let Some(tip) = self.ledger.tip_hex()? else {
            return Ok(Vec::new());
        };
        Ok(self
            .read_events_at(&tip, ObjectKind::Milestone, id)?
            .into_iter()
            .filter_map(|e| match &e.body {
                PmBody::Evidence(d) => {
                    let d = d.clone();
                    Some((e, d))
                }
                _ => None,
            })
            .collect())
    }
}
