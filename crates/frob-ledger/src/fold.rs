//! Folding a ticket's events into its state: the integrity invariant.
//!
//! `fold(events) == frontmatter` is checked by `doctor` and rule `TICK001`.
//! Events are applied in (ULID time, `at`, id) order; a `field` or
//! `transition` event whose recorded previous value disagrees with the state
//! it meets is applied anyway (last writer in fold order wins) and reported
//! as a [`Conflict`], never silently picked.

use crate::error::{LedgerError, Result};
use crate::event::{
    CreateData, Event, EventBody, FieldChange, LinkData, TransitionData, sort_events,
};
use crate::id::{EventId, TicketId};
use crate::model::{Acceptance, Category, Frontmatter, LinkOp, Ticket, normalize_body};
use crate::schema::{get_field, set_acceptance, set_field};

/// A concurrent pair of changes that disagree about the previous value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Conflict {
    /// The event whose recorded `old` or `from` did not match.
    pub event: EventId,
    /// The field (or `category`) involved.
    pub field: String,
    /// What the event said the previous value was.
    pub expected: Option<String>,
    /// What the fold had at that point.
    pub found: Option<String>,
}

/// The result of a fold.
#[derive(Debug, Clone, PartialEq)]
pub struct Folded {
    /// The ticket state.
    pub ticket: Ticket,
    /// Conflicting concurrent changes, in fold order.
    pub conflicts: Vec<Conflict>,
}

fn initial(id: TicketId, at: crate::model::Stamp, actor: &str, c: &CreateData) -> Ticket {
    let mut links = c.links.clone();
    links.sort();
    links.dedup();
    Ticket {
        front: Frontmatter {
            id,
            title: c.title.clone(),
            ty: c.ty,
            flavour: c.flavour.clone(),
            category: c.category,
            outcome: None,
            priority: c.priority,
            class: c.class,
            due: c.due,
            points: c.points,
            parent: c.parent,
            reporter: actor.to_owned(),
            assignee: c.assignee.clone(),
            created: at,
            updated: at,
            persona: c.persona.clone(),
            capability: c.capability.clone(),
            outcome_text: c.outcome_text.clone(),
            idempotency_key: c.idempotency_key.clone(),
            aliases: c.aliases.clone(),
            labels: c.labels.clone(),
            scope: c.scope.clone(),
            links,
            acceptance: c
                .acceptance
                .iter()
                .map(|text| Acceptance {
                    text: text.clone(),
                    bound: false,
                })
                .collect(),
        },
        body: normalize_body(&c.body),
    }
}

fn show(v: Option<&toml::Value>) -> Option<String> {
    v.map(ToString::to_string)
}

fn apply_field(
    id: TicketId,
    t: &mut Ticket,
    ev: &Event,
    c: &FieldChange,
    out: &mut Vec<Conflict>,
) -> Result<()> {
    let current = get_field(t, &c.field);
    if c.old.is_some() || current.is_some() {
        let same = match (&c.old, &current) {
            (Some(a), Some(b)) => a == b,
            (None, None) => true,
            _ => false,
        };
        if !same {
            tracing::debug!(ticket = %id, field = %c.field, event = %ev.id, "concurrent field conflict");
            out.push(Conflict {
                event: ev.id,
                field: c.field.clone(),
                expected: show(c.old.as_ref()),
                found: show(current.as_ref()),
            });
        }
    }
    let applied = if c.field == "acceptance" {
        set_acceptance(t, c.new.as_ref())
    } else {
        set_field(t, &c.field, c.new.as_ref())
    };
    applied.map_err(|m| LedgerError::fold(id, format!("event {}: {m}", ev.id)))
}

/// Where criteria numbered under the list as it stood at event `since` sit now.
///
/// Evidence events are immutable and record `accepts` as 1-based positions in
/// the acceptance list at write time. Every later `acceptance` field event
/// carries a `moved` map, so composing those maps in fold order gives each
/// recorded position's current one, or `None` when that criterion was removed
/// (or a later event has no map, which can only lose track of it).
pub fn remap_accepts(events: &[Event], since: EventId, accepts: &[usize]) -> Vec<Option<usize>> {
    let mut ordered: Vec<&Event> = events.iter().collect();
    ordered.sort_by_key(|e| e.order_key());
    let mut now: Vec<Option<usize>> = accepts.iter().map(|n| Some(*n)).collect();
    let later = ordered.into_iter().skip_while(|e| e.id != since).skip(1);
    for ev in later {
        let EventBody::Field(c) = &ev.body else {
            continue;
        };
        if c.field != "acceptance" {
            continue;
        }
        for slot in &mut now {
            *slot = slot.and_then(|n| match c.moved.as_deref() {
                Some(map) => map.get(n.wrapping_sub(1)).copied().filter(|m| *m != 0),
                None => None,
            });
        }
    }
    now
}

/// Whether an evidence record counts as a pass: measured and not a failing run.
///
/// `status` must be `measured` and `passed` must not be `false`; a file-provider
/// record has no `passed` and counts when measured, as the close guard reads it.
pub fn evidence_passes(data: &crate::event::EvidenceData) -> bool {
    let measured = data.record.get("status").and_then(toml::Value::as_str) == Some("measured");
    let failed = data.record.get("passed").and_then(toml::Value::as_bool) == Some(false);
    measured && !failed
}

/// Set each criterion's `bound` from the evidence offered for it, through the remap.
///
/// Rule: an evidence event offered for criterion N when it was written counts
/// for whatever N became after later acceptance edits, and for nothing when N
/// was removed. Within one (provider, reference, criterion) the latest record
/// in fold order decides: it binds only when it is measured and passed, so a
/// failing or unmeasured record never binds and supersedes an earlier pass of
/// the same provider and reference. A criterion is bound when at least one
/// (provider, reference) pair's latest record for it passes.
fn bind_acceptance(t: &mut Ticket, events: &[Event]) {
    let mut ordered: Vec<&Event> = events.iter().collect();
    ordered.sort_by_key(|e| e.order_key());
    let text = |data: &crate::event::EvidenceData, key: &str| {
        data.record
            .get(key)
            .and_then(toml::Value::as_str)
            .unwrap_or_default()
            .to_owned()
    };
    let mut latest: std::collections::BTreeMap<(String, String, usize), bool> =
        std::collections::BTreeMap::new();
    for ev in ordered {
        let EventBody::Evidence(data) = &ev.body else {
            continue;
        };
        let passes = evidence_passes(data);
        let (provider, reference) = (text(data, "provider"), text(data, "ref"));
        for now in remap_accepts(events, ev.id, &data.accepts)
            .into_iter()
            .flatten()
        {
            latest.insert((provider.clone(), reference.clone(), now), passes);
        }
    }
    for (i, a) in t.front.acceptance.iter_mut().enumerate() {
        a.bound = latest.iter().any(|((_, _, n), pass)| *n == i + 1 && *pass);
    }
}

fn apply_transition(
    id: TicketId,
    t: &mut Ticket,
    ev: &Event,
    c: &TransitionData,
    out: &mut Vec<Conflict>,
) -> Result<()> {
    let fm = &mut t.front;
    if fm.category != c.from {
        out.push(Conflict {
            event: ev.id,
            field: "category".to_owned(),
            expected: Some(c.from.to_string()),
            found: Some(fm.category.to_string()),
        });
    }
    match (c.to, c.outcome) {
        (Category::Done, Some(o)) => fm.outcome = Some(o),
        (Category::Done, None) => {
            return Err(LedgerError::fold(
                id,
                format!("event {}: transition to done has no outcome", ev.id),
            ));
        }
        (_, None) => fm.outcome = None,
        (_, Some(_)) => {
            return Err(LedgerError::fold(
                id,
                format!(
                    "event {}: outcome given for a non-terminal transition",
                    ev.id
                ),
            ));
        }
    }
    fm.category = c.to;
    Ok(())
}

fn apply_link(t: &mut Ticket, c: &LinkData) {
    let link = crate::model::Link {
        kind: c.link,
        target: c.target,
    };
    let links = &mut t.front.links;
    match c.op {
        LinkOp::Add => {
            if !links.contains(&link) {
                links.push(link);
                links.sort();
            }
        }
        LinkOp::Remove => links.retain(|l| *l != link),
    }
}

/// Fold `events` (any order) into the state of ticket `id`.
///
/// # Errors
///
/// [`LedgerError::Fold`] when there is no `create` event or more than one,
/// when a field event names an unknown or unsettable field or carries a bad
/// value, or when a transition breaks the outcome rule.
pub fn fold(id: TicketId, events: &[Event]) -> Result<Folded> {
    let mut ordered: Vec<&Event> = events.iter().collect();
    ordered.sort_by_key(|e| e.order_key());
    let mut iter = ordered.into_iter();
    let first = iter
        .next()
        .ok_or_else(|| LedgerError::fold(id, "no events"))?;
    let EventBody::Create(create) = &first.body else {
        return Err(LedgerError::fold(
            id,
            format!(
                "the first event {} is `{}`, not `create`",
                first.id, first.kind
            ),
        ));
    };
    let mut ticket = initial(id, first.at, &first.actor, create);
    let mut conflicts = Vec::new();
    let mut last = first.at;
    for ev in iter {
        match &ev.body {
            EventBody::Create(_) => {
                return Err(LedgerError::fold(
                    id,
                    format!("event {} is a second `create`", ev.id),
                ));
            }
            EventBody::Field(c) => apply_field(id, &mut ticket, ev, c, &mut conflicts)?,
            EventBody::Transition(c) => apply_transition(id, &mut ticket, ev, c, &mut conflicts)?,
            EventBody::Link(c) => apply_link(&mut ticket, c),
            EventBody::Comment(_)
            | EventBody::Exception(_)
            | EventBody::EvidenceBypass(_)
            | EventBody::ChangelogExempt(_)
            | EventBody::Land(_)
            | EventBody::Other
            // Evidence binds once at the end, through the acceptance remap.
            | EventBody::Evidence(_) => {}
        }
        last = ev.at;
    }
    bind_acceptance(&mut ticket, events);
    ticket.front.updated = last;
    tracing::debug!(ticket = %id, events = events.len(), conflicts = conflicts.len(), "folded");
    Ok(Folded { ticket, conflicts })
}

/// Sort a copy of `events` into fold order (a convenience for callers that list them).
pub fn ordered(events: &[Event]) -> Vec<Event> {
    let mut v = events.to_vec();
    sort_events(&mut v);
    v
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event::{CommentData, FieldChange};
    use crate::model::{CommentSubtype, Outcome, Priority, TicketType};

    fn create_event(actor: &str) -> Event {
        Event::new(
            actor,
            EventBody::Create(Box::new(CreateData {
                title: "T".into(),
                ty: TicketType::Task,
                category: Category::Todo,
                priority: Priority::Medium,
                class: crate::model::Class::Standard,
                due: None,
                flavour: None,
                points: None,
                parent: None,
                assignee: None,
                persona: None,
                capability: None,
                outcome_text: None,
                idempotency_key: None,
                aliases: vec![],
                labels: vec![],
                scope: vec![],
                acceptance: vec!["a".into()],
                body: "hello".into(),
                links: vec![],
            })),
        )
    }

    fn set(field: &str, old: Option<&str>, new: &str) -> Event {
        Event::new(
            "a",
            EventBody::Field(FieldChange {
                field: field.into(),
                old: old.map(|s| toml::Value::String(s.into())),
                new: Some(toml::Value::String(new.into())),
                reason: None,
                moved: None,
            }),
        )
    }

    #[test]
    fn fold_applies_creation_fields_and_transitions() {
        let id = TicketId::mint();
        let evs = vec![
            create_event("logan"),
            set("title", Some("T"), "Renamed"),
            Event::new(
                "a",
                EventBody::Comment(CommentData {
                    subtype: CommentSubtype::Note,
                    body: "n".into(),
                }),
            ),
            Event::new(
                "a",
                EventBody::Transition(TransitionData {
                    from: Category::Todo,
                    to: Category::Done,
                    outcome: Some(Outcome::Fixed),
                    reason: None,
                }),
            ),
        ];
        let f = fold(id, &evs).expect("fold");
        assert_eq!(f.ticket.front.title, "Renamed");
        assert_eq!(f.ticket.front.category, Category::Done);
        assert_eq!(f.ticket.front.outcome, Some(Outcome::Fixed));
        assert_eq!(f.ticket.front.reporter, "logan");
        assert_eq!(f.ticket.body, "hello");
        assert!(f.conflicts.is_empty());
        // Input order does not matter.
        let mut rev = evs.clone();
        rev.reverse();
        assert_eq!(fold(id, &rev).expect("fold").ticket, f.ticket);
    }

    #[test]
    fn concurrent_field_changes_are_reported() {
        let id = TicketId::mint();
        let evs = vec![
            create_event("a"),
            set("title", Some("T"), "Left"),
            set("title", Some("T"), "Right"),
        ];
        let f = fold(id, &evs).expect("fold");
        assert_eq!(f.ticket.front.title, "Right");
        assert_eq!(f.conflicts.len(), 1);
        assert_eq!(f.conflicts[0].field, "title");
    }

    #[test]
    fn missing_or_duplicate_create_is_an_error() {
        let id = TicketId::mint();
        assert!(fold(id, &[]).is_err());
        assert!(fold(id, &[set("title", None, "x")]).is_err());
        assert!(fold(id, &[create_event("a"), create_event("a")]).is_err());
    }

    #[test]
    fn bad_field_is_an_error() {
        let id = TicketId::mint();
        let evs = vec![create_event("a"), set("category", None, "done")];
        assert!(fold(id, &evs).is_err());
        let evs = vec![create_event("a"), set("nope", None, "x")];
        assert!(fold(id, &evs).is_err());
    }

    fn texts(items: &[&str]) -> toml::Value {
        toml::Value::Array(
            items
                .iter()
                .map(|t| toml::Value::String((*t).into()))
                .collect(),
        )
    }

    fn acceptance_edit(old: &[&str], new: &[&str], moved: &[usize]) -> Event {
        Event::new(
            "a",
            EventBody::Field(FieldChange {
                field: "acceptance".into(),
                old: Some(texts(old)),
                new: Some(texts(new)),
                reason: None,
                moved: Some(moved.to_vec()),
            }),
        )
    }

    // frob:ticket 01M4055D28TPGSJW71D09P2DKX
    #[test]
    fn acceptance_events_fold_and_remap_recorded_positions() {
        let id = TicketId::mint();
        let create = create_event("a");
        let evidence = Event::new("a", EventBody::Other);
        let first = acceptance_edit(&["a"], &["a", "b, c"], &[1]);
        let later = Event::new("a", EventBody::Other);
        let second = acceptance_edit(&["a", "b, c"], &["b, c"], &[0, 1]);
        let evs = vec![create, evidence.clone(), first, later.clone(), second];
        let f = fold(id, &evs).expect("fold");
        assert!(f.conflicts.is_empty(), "{:?}", f.conflicts);
        let left: Vec<_> = f
            .ticket
            .front
            .acceptance
            .iter()
            .map(|a| a.text.as_str())
            .collect();
        assert_eq!(left, ["b, c"]);
        // Recorded before both edits: "a" (1) was removed by the second.
        assert_eq!(remap_accepts(&evs, evidence.id, &[1]), [None]);
        // Recorded between them: "b, c" (2) is now the first criterion, "a" (1) is gone.
        assert_eq!(remap_accepts(&evs, later.id, &[1, 2]), [None, Some(1)]);
    }
}
