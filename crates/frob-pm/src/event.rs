//! Events of milestones and cycles: one append-only TOML file per change,
//! `events/<ulid>.toml`, with the same envelope as ticket events
//! (`kind`, `at`, `actor`, `rev`).
//!
//! Kinds: `create`, `field`, `member`, `criterion`, `transition` (releases.md
//! section 6a) plus `cycle` (carried, ratio, retro at cycle close), `evidence`, which binds exit criteria exactly as it binds
//! ticket acceptance, and `override`, `cut` and `adopt`, which `release cut` records on a
//! milestone (they fold to no change; REL001 reads `cut`). Any other kind parses as [`PmBody::Other`] and folds to
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
    /// Cycle: position among cycles sharing the date range, assigned at creation; absent means 1.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ordinal: Option<u32>,
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
    /// Remove only: for each criterion before this event, its 1-based position after, or 0 when removed.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub moved: Option<Vec<usize>>,
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
    /// Cycle closing before its planned end: the close day (UTC), which becomes the effective end.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ended: Option<Day>,
}

/// A release override: a cut proceeded although the milestone was not ready (releases.md section 4).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OverrideData {
    /// The version being cut.
    pub version: String,
    /// Why the readiness gate was overridden.
    pub reason: String,
}

/// One tag a cut created: its name, the tag object and the commit it points at.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TagRecord {
    /// Tag name, for example `frob-v0.532.0`.
    pub name: String,
    /// Object id of the annotated tag.
    pub object: String,
    /// Commit id the tag points at.
    pub commit: String,
}

/// A completed release cut: what `release cut` committed and tagged (REL001 reads this).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CutData {
    /// The version cut.
    pub version: String,
    /// The one commit holding the version bump and the compiled changelog.
    pub commit: String,
    /// The per-binary tags created at that commit.
    pub tags: Vec<TagRecord>,
}

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
/// Marks the `cut` of a version as adopted: the tags were made by hand, not by `release cut`.
///
/// A separate event kind, not a field of [`CutData`]: `CutData` denies unknown fields, so an
/// older binary could not read a `cut` carrying a new key, while it reads an unknown kind as
/// [`PmBody::Other`]. The `cut` itself stays byte-identical to one `release cut` writes.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdoptData {
    /// The version whose cut was adopted.
    pub version: String,
    /// Why the tags are recorded as a cut instead of redone.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// What a `cycle` event records.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum CycleOp {
    /// An incomplete member moved to a later cycle at close (`ticket`, `to`).
    Carried,
    /// The commitment-versus-done ratio at close (`committed`, `done` points).
    Ratio,
    /// The retrospective note written at close (`text`).
    Retro,
    /// An assignment past capacity, allowed by `--over-commit` (`ticket`, `committed` points after it, `capacity`, `text` the reason).
    OverCommit,
    /// An op this version does not interpret; it folds to no change.
    #[serde(other)]
    Other,
}

/// A cycle-review fact recorded on a cycle (pm-enforcement.md section 4); which fields are set depends on the op.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CycleEventData {
    /// What this records.
    pub op: CycleOp,
    /// Carried: the ticket that moved on.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ticket: Option<TicketId>,
    /// Carried: the cycle it moved to.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub to: Option<crate::model::ObjectId>,
    /// Ratio: story points committed (members' points at close); over-commit: committed points after the assignment.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub committed: Option<u32>,
    /// Ratio: story points done.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub done: Option<u32>,
    /// Retro: the note, taken whole; over-commit: the reason.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub text: Option<String>,
    /// Over-commit: the capacity in points that was exceeded.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub capacity: Option<u32>,
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
    /// A cycle-review fact (`carried`, `ratio`, `retro`); only `carried` changes the fold.
    Cycle(Box<CycleEventData>),
    /// A readiness override recorded by `release cut --override`; folds to no change.
    Override(OverrideData),
    /// A completed release cut; folds to no change (the `transition` to released is separate).
    Cut(CutData),
    /// Marks the version's `cut` as adopted from hand-made tags; folds to no change.
    Adopt(AdoptData),
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
            Self::Cycle(_) => "cycle",
            Self::Override(_) => "override",
            Self::Cut(_) => "cut",
            Self::Adopt(_) => "adopt",
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
    /// A new event stamped `at`, with a fresh id.
    pub fn new(at: Stamp, actor: &str, body: PmBody) -> Self {
        let ev = Self {
            id: EventId::mint(),
            at,
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
