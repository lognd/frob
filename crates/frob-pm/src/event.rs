//! Events of milestones and cycles: one append-only TOML file per change,
//! `events/<ulid>.toml`, with the same envelope as ticket events
//! (`kind`, `at`, `actor`, `rev`).
//!
//! Kinds: `create`, `field`, `member`, `criterion`, `transition` (releases.md
//! section 6a) plus `evidence`, which binds exit criteria exactly as it binds
//! ticket acceptance. Any other kind parses as [`PmBody::Other`] and folds to
//! no change, so a newer ledger still folds here.

use frob_ledger::EventId;
use frob_ledger::TicketId;
use frob_ledger::event::{EvidenceData, FieldChange};
use frob_ledger::model::Stamp;
use serde::{Deserialize, Serialize};

use crate::error::{PmError, Result};
use crate::model::{Day, ObjectKind, State};

/// Revision of the event file format written by this crate.
pub const EVENT_REV: u32 = 1;

/// The initial state of an object, carried by its `create` event.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CreateData {
    /// Which kind of object this creates.
    pub object: ObjectKind,
    /// Milestone: the version (required).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
    /// One-line goal.
    pub goal: String,
    /// Milestone: target date; absent means unscheduled.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<Day>,
    /// Cycle: first day (required).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub start: Option<Day>,
    /// Cycle: last day (required).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub end: Option<Day>,
    /// Cycle: committed story points.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub capacity_points: Option<u32>,
    /// Milestone: initial exit criteria texts.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub criteria: Vec<String>,
}

/// Add or remove.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Op {
    /// Put in.
    Add,
    /// Take out.
    Remove,
}

/// A ticket joining or leaving the object (an epic of a milestone, a ticket of a cycle).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MemberData {
    /// Add or remove.
    pub op: Op,
    /// The ticket.
    pub ticket: TicketId,
}

/// An exit criterion added to or removed from a milestone.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CriterionData {
    /// Add or remove.
    pub op: Op,
    /// Add only: the criterion text.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub text: Option<String>,
    /// Remove only: the 1-based position in the list as it stood before this event.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub position: Option<usize>,
}

/// A state change.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransitionData {
    /// State before.
    pub from: State,
    /// State after.
    pub to: State,
    /// Why.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// The kind-specific part of an event; the `kind` key selects the variant.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "kebab-case")]
pub enum PmBody {
    /// The object's birth.
    Create(Box<CreateData>),
    /// A frontmatter field changed.
    Field(FieldChange),
    /// A ticket joined or left.
    Member(MemberData),
    /// An exit criterion was added or removed.
    Criterion(CriterionData),
    /// The state changed.
    Transition(TransitionData),
    /// A measurement offered for exit criteria; binds them in the fold.
    Evidence(EvidenceData),
    /// A kind this version does not interpret; it folds to no change.
    #[serde(other)]
    Other,
}

impl PmBody {
    /// The `kind` spelling (`other` for uninterpreted kinds).
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Create(_) => "create",
            Self::Field(_) => "field",
            Self::Member(_) => "member",
            Self::Criterion(_) => "criterion",
            Self::Transition(_) => "transition",
            Self::Evidence(_) => "evidence",
            Self::Other => "other",
        }
    }
}

#[derive(Serialize, Deserialize)]
struct EventFile {
    #[serde(flatten)]
    body: PmBody,
    at: Stamp,
    actor: String,
    rev: u32,
}

/// One event of one object, with its id (the file stem).
#[derive(Debug, Clone, PartialEq)]
pub struct PmEvent {
    /// Event id.
    pub id: EventId,
    /// When it happened.
    pub at: Stamp,
    /// Audit label of who wrote it.
    pub actor: String,
    /// Event format revision.
    pub rev: u32,
    /// The parsed body.
    pub body: PmBody,
}

impl PmEvent {
    /// A new event stamped now, with a fresh id.
    pub fn new(actor: &str, body: PmBody) -> Self {
        let ev = Self {
            id: EventId::mint(),
            at: Stamp::now(),
            actor: actor.to_owned(),
            rev: EVENT_REV,
            body,
        };
        tracing::debug!(event = %ev.id, kind = ev.body.name(), "pm event created");
        ev
    }

    /// Ordering key: (ULID time, `at`, id), the fold order of tickets.
    pub fn order_key(&self) -> (u64, i64, EventId) {
        (self.id.timestamp_ms(), self.at.unix(), self.id)
    }

    /// File name below `events/`.
    pub fn file_name(&self) -> String {
        format!("{}.toml", self.id)
    }

    /// Render the event file (TOML).
    ///
    /// # Errors
    ///
    /// [`PmError::Malformed`] when the body cannot be written as TOML.
    pub fn to_toml(&self) -> Result<String> {
        let file = EventFile {
            body: self.body.clone(),
            at: self.at,
            actor: self.actor.clone(),
            rev: self.rev,
        };
        toml::to_string(&file)
            .map_err(|e| PmError::malformed(format!("events/{}.toml", self.id), e.to_string()))
    }

    /// Parse the file `<id>.toml` whose text is `text`.
    ///
    /// # Errors
    ///
    /// [`PmError::Malformed`] on bad TOML, a missing envelope key or a bad value.
    pub fn parse(id: EventId, text: &str) -> Result<Self> {
        let label = format!("events/{id}.toml");
        let file: EventFile = toml::from_str(text)
            .map_err(|e: toml::de::Error| PmError::malformed(&label, e.to_string()))?;
        Ok(Self {
            id,
            at: file.at,
            actor: file.actor,
            rev: file.rev,
            body: file.body,
        })
    }
}

/// Sort events into fold order.
pub fn sort_events(events: &mut [PmEvent]) {
    events.sort_by_key(PmEvent::order_key);
}
