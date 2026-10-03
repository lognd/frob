//! Folding an object's events into its state: `fold(events) == frontmatter`.
//!
//! Events apply in (ULID time, `at`, id) order, as for tickets. The fold is a
//! pure function of the set of events, so merging two branches (which only
//! unions event files) and re-folding loses nothing and gives every reader the
//! same state. A `field` or `transition` event whose recorded previous value
//! disagrees with the state it meets is applied anyway and reported as a
//! [`Conflict`]; `member` events are set operations and never conflict.

use frob_ledger::TicketId;
pub use frob_ledger::fold::Conflict;

use crate::error::{PmError, Result};
use crate::event::{
    CreateData, CriterionData, MemberData, Op, PmBody, PmEvent, TransitionData, sort_events,
};
use crate::model::{Criterion, Cycle, Day, Milestone, Object, ObjectId, ObjectKind, State};

/// The result of a fold.
#[derive(Debug, Clone, PartialEq)]
pub struct Folded {
    /// The object state.
    pub object: Object,
    /// Conflicting concurrent changes, in fold order.
    pub conflicts: Vec<Conflict>,
}

fn show(v: Option<&toml::Value>) -> Option<String> {
    v.map(ToString::to_string)
}

fn initial(id: ObjectId, ev: &PmEvent, c: &CreateData) -> std::result::Result<Object, String> {
    let need = |v: &Option<Day>, what: &str| v.ok_or_else(|| format!("create is missing `{what}`"));
    match c.object {
        ObjectKind::Milestone => Ok(Object::Milestone(Milestone {
            id,
            version: c
                .version
                .clone()
                .filter(|v| !v.is_empty())
                .ok_or("create is missing `version`")?,
            goal: c.goal.clone(),
            target: c.target,
            state: State::initial(ObjectKind::Milestone),
            epics: Vec::new(),
            criteria: c
                .criteria
                .iter()
                .map(|t| Criterion {
                    text: t.clone(),
                    bound: false,
                })
                .collect(),
            created: ev.at,
            updated: ev.at,
        })),
        ObjectKind::Cycle => {
            let (start, end) = (need(&c.start, "start")?, need(&c.end, "end")?);
            if end < start {
                return Err(format!("cycle ends ({end}) before it starts ({start})"));
            }
            Ok(Object::Cycle(Cycle {
                id,
                start,
                end,
                goal: c.goal.clone(),
                capacity_points: c.capacity_points,
                state: State::initial(ObjectKind::Cycle),
                tickets: Vec::new(),
                created: ev.at,
                updated: ev.at,
            }))
        }
    }
}

/// The current value of `field` of `o` as TOML, or `None` when unset or unknown.
pub(crate) fn get_field(o: &Object, field: &str) -> Option<toml::Value> {
    let s = |v: &str| Some(toml::Value::String(v.to_owned()));
    match (o, field) {
        (Object::Milestone(m), "version") => s(&m.version),
        (Object::Milestone(m), "goal") => s(&m.goal),
        (Object::Milestone(m), "target") => m.target.and_then(|d| s(&d.to_string())),
        (Object::Cycle(c), "goal") => s(&c.goal),
        (Object::Cycle(c), "start") => s(&c.start.to_string()),
        (Object::Cycle(c), "end") => s(&c.end.to_string()),
        (Object::Cycle(c), "capacity_points") => c
            .capacity_points
            .map(|n| toml::Value::Integer(i64::from(n))),
        _ => None,
    }
}

fn text(v: Option<&toml::Value>, field: &str) -> std::result::Result<String, String> {
    match v {
        Some(toml::Value::String(s)) if !s.is_empty() || field == "goal" => Ok(s.clone()),
        _ => Err(format!("`{field}` needs a string value")),
    }
}

fn day(v: Option<&toml::Value>, field: &str) -> std::result::Result<Day, String> {
    text(v, field)?.parse()
}

fn set_field(
    o: &mut Object,
    field: &str,
    v: Option<&toml::Value>,
) -> std::result::Result<(), String> {
    match (&mut *o, field) {
        (Object::Milestone(m), "version") => m.version = text(v, field)?,
        (Object::Milestone(m), "goal") => m.goal = text(v, field)?,
        (Object::Milestone(m), "target") => {
            m.target = v.map(|_| day(v, field)).transpose()?;
        }
        (Object::Cycle(c), "goal") => c.goal = text(v, field)?,
        (Object::Cycle(c), "start") => c.start = day(v, field)?,
        (Object::Cycle(c), "end") => c.end = day(v, field)?,
        (Object::Cycle(c), "capacity_points") => {
            c.capacity_points = match v {
                None => None,
                Some(toml::Value::Integer(n)) => Some(
                    u32::try_from(*n)
                        .map_err(|_| "`capacity_points` must be 0 or more".to_owned())?,
                ),
                Some(_) => return Err("`capacity_points` needs an integer".to_owned()),
            };
        }
        (o, f) => return Err(format!("a {} has no settable field `{f}`", o.kind())),
    }
    if let Object::Cycle(c) = o
        && c.end < c.start
    {
        return Err(format!(
            "cycle ends ({}) before it starts ({})",
            c.end, c.start
        ));
    }
    Ok(())
}

fn members_mut(o: &mut Object) -> &mut Vec<TicketId> {
    match o {
        Object::Milestone(m) => &mut m.epics,
        Object::Cycle(c) => &mut c.tickets,
    }
}

fn apply_member(o: &mut Object, d: &MemberData) {
    let list = members_mut(o);
    match d.op {
        Op::Add => {
            if let Err(at) = list.binary_search(&d.ticket) {
                list.insert(at, d.ticket);
            }
        }
        Op::Remove => list.retain(|t| *t != d.ticket),
    }
}

fn apply_criterion(o: &mut Object, d: &CriterionData) -> std::result::Result<(), String> {
    let Object::Milestone(m) = o else {
        return Err("only a milestone has exit criteria".to_owned());
    };
    match (d.op, &d.text, d.position) {
        (Op::Add, Some(t), None) => m.criteria.push(Criterion {
            text: t.clone(),
            bound: false,
        }),
        (Op::Remove, None, Some(p)) if (1..=m.criteria.len()).contains(&p) => {
            m.criteria.remove(p - 1);
        }
        (Op::Remove, None, Some(p)) => {
            return Err(format!(
                "criterion {p} does not exist ({} criteria)",
                m.criteria.len()
            ));
        }
        _ => {
            return Err("a criterion event adds with `text` or removes with `position`".to_owned());
        }
    }
    Ok(())
}

fn apply_transition(
    o: &mut Object,
    ev: &PmEvent,
    d: &TransitionData,
    out: &mut Vec<Conflict>,
) -> std::result::Result<(), String> {
    let kind = o.kind();
    if !d.to.valid_for(kind) || !d.from.valid_for(kind) {
        return Err(format!("`{}` is not a state of a {kind}", d.to));
    }
    let slot = match o {
        Object::Milestone(m) => &mut m.state,
        Object::Cycle(c) => &mut c.state,
    };
    if *slot != d.from {
        out.push(Conflict {
            event: ev.id,
            field: "state".to_owned(),
            expected: Some(d.from.to_string()),
            found: Some(slot.to_string()),
        });
    }
    *slot = d.to;
    Ok(())
}

/// Set each criterion's `bound` from the evidence offered for it, by the ticket rule.
///
/// The rule lives in [`crate::milestone::criteria`]; a criterion is bound when
/// some (provider, ref) pair's latest record for it passes.
fn bind_criteria(o: &mut Object, ordered: &[&PmEvent]) {
    let Object::Milestone(m) = o else { return };
    let bound = crate::milestone::criteria::bindings_of(ordered, m.criteria.len());
    for (c, by) in m.criteria.iter_mut().zip(bound) {
        c.bound = !by.is_empty();
    }
}

/// Fold `events` of object `id` (of `kind`) into its state.
///
/// # Errors
///
/// [`PmError::Fold`] when there is no `create` event or more than one, the
/// first event is not the create, or an event carries a value the model rejects.
pub fn fold(kind: ObjectKind, id: ObjectId, events: &[PmEvent]) -> Result<Folded> {
    let fail = |m: String| PmError::Fold {
        kind,
        id: id.to_string(),
        message: m,
    };
    let mut ordered: Vec<PmEvent> = events.to_vec();
    sort_events(&mut ordered);
    let refs: Vec<&PmEvent> = ordered.iter().collect();
    let creates = ordered
        .iter()
        .filter(|e| matches!(e.body, PmBody::Create(_)))
        .count();
    if creates != 1 {
        return Err(fail(format!(
            "expected exactly one create event, found {creates}"
        )));
    }
    let Some(first) = ordered.first() else {
        return Err(fail("no events".to_owned()));
    };
    let PmBody::Create(c) = &first.body else {
        return Err(fail(format!(
            "event {} sorts before the create event",
            first.id
        )));
    };
    if c.object != kind {
        return Err(fail(format!("create says this is a {}", c.object)));
    }
    let mut object = initial(id, first, c).map_err(|m| fail(format!("event {}: {m}", first.id)))?;
    let mut conflicts = Vec::new();
    let mut updated = first.at;
    for ev in ordered.iter().skip(1) {
        let applied = match &ev.body {
            PmBody::Create(_) | PmBody::Other | PmBody::Evidence(_) => Ok(()),
            PmBody::Field(f) => {
                let current = get_field(&object, &f.field);
                if f.old != current {
                    tracing::debug!(object = %id, field = %f.field, event = %ev.id, "concurrent field conflict");
                    conflicts.push(Conflict {
                        event: ev.id,
                        field: f.field.clone(),
                        expected: show(f.old.as_ref()),
                        found: show(current.as_ref()),
                    });
                }
                set_field(&mut object, &f.field, f.new.as_ref())
            }
            PmBody::Member(d) => {
                apply_member(&mut object, d);
                Ok(())
            }
            PmBody::Criterion(d) => apply_criterion(&mut object, d),
            PmBody::Transition(d) => apply_transition(&mut object, ev, d, &mut conflicts),
        };
        applied.map_err(|m| fail(format!("event {}: {m}", ev.id)))?;
        updated = updated.max(ev.at);
    }
    bind_criteria(&mut object, &refs);
    match &mut object {
        Object::Milestone(m) => m.updated = updated,
        Object::Cycle(c) => c.updated = updated,
    }
    Ok(Folded { object, conflicts })
}
