//! The folded state of a milestone and of a cycle, and the small types they share.
// frob:ticket 01M40VQWCV38B2JCABYNNNA877

use std::fmt;
use std::str::FromStr;

use frob_ledger::TicketId;
use frob_ledger::model::Stamp;
use serde::{Deserialize, Serialize};

/// The two kinds of PM object; each has its own sub-directory of the tickets directory.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ObjectKind {
    /// A release milestone (`tickets/_milestones/<ULID>/milestone.md`).
    Milestone,
    /// A planning cycle (`tickets/_cycles/<ULID>/cycle.md`).
    Cycle,
}

impl ObjectKind {
    /// Every kind.
    pub const ALL: [Self; 2] = [Self::Milestone, Self::Cycle];

    /// The spelling in files and messages.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Milestone => "milestone",
            Self::Cycle => "cycle",
        }
    }

    /// Directory name below the tickets directory.
    pub const fn dir(self) -> &'static str {
        match self {
            Self::Milestone => "_milestones",
            Self::Cycle => "_cycles",
        }
    }

    /// Name of the frontmatter file inside an object directory.
    pub const fn file(self) -> &'static str {
        match self {
            Self::Milestone => "milestone.md",
            Self::Cycle => "cycle.md",
        }
    }
}

impl fmt::Display for ObjectKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// The identity of a milestone or cycle: a ULID minted at creation, also its directory name.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct ObjectId(TicketId);

impl ObjectId {
    /// Mint a fresh id.
    pub fn mint() -> Self {
        Self(TicketId::mint())
    }

    /// The random part (last 16 characters), the alphabet of handles.
    pub fn random_part(&self) -> String {
        self.0.random_part()
    }

    /// The handle shown to humans: `~` plus the last seven characters.
    pub fn handle(&self) -> String {
        format!("~{}", &self.random_part()[9..])
    }
}

impl fmt::Display for ObjectId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}

impl FromStr for ObjectId {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, String> {
        s.parse::<TicketId>().map(Self).map_err(|e| e.to_string())
    }
}

pub use gob_time::Day;

/// Where an object is in its life; which values are legal depends on the kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum State {
    /// Milestone: being worked toward.
    Open,
    /// Milestone: shipped.
    Released,
    /// Milestone: abandoned.
    Dropped,
    /// Cycle: created, not started.
    Planned,
    /// Cycle: running.
    Active,
    /// Cycle: ended and closed.
    Closed,
}

impl State {
    /// The spelling in files and messages.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Open => "open",
            Self::Released => "released",
            Self::Dropped => "dropped",
            Self::Planned => "planned",
            Self::Active => "active",
            Self::Closed => "closed",
        }
    }

    /// The state a new object of `kind` starts in.
    pub const fn initial(kind: ObjectKind) -> Self {
        match kind {
            ObjectKind::Milestone => Self::Open,
            ObjectKind::Cycle => Self::Planned,
        }
    }

    /// Whether this state exists for `kind`.
    pub const fn valid_for(self, kind: ObjectKind) -> bool {
        matches!(
            (kind, self),
            (
                ObjectKind::Milestone,
                Self::Open | Self::Released | Self::Dropped
            ) | (
                ObjectKind::Cycle,
                Self::Planned | Self::Active | Self::Closed
            )
        )
    }
}

impl fmt::Display for State {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// One exit criterion of a milestone and whether passing evidence is bound to it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Criterion {
    /// The criterion text.
    pub text: String,
    /// True when measured, passing evidence is bound to it (the ticket rule, remapped).
    #[serde(default)]
    pub bound: bool,
}

/// A milestone: a version, a goal, a target and the epics and criteria that define done.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Milestone {
    /// Identity.
    pub id: ObjectId,
    /// The release version; also the alias (`0.532.0`).
    pub version: String,
    /// One-line goal.
    pub goal: String,
    /// Target date; absent means unscheduled.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<Day>,
    /// Life-cycle state.
    pub state: State,
    /// Member epics (tickets), sorted.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub epics: Vec<TicketId>,
    /// Exit criteria, in order.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub criteria: Vec<Criterion>,
    /// Creation time (the `create` event).
    pub created: Stamp,
    /// Time of the latest event.
    pub updated: Stamp,
}

/// A cycle: a dated window with a goal, an optional capacity and member tickets.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Cycle {
    /// Identity.
    pub id: ObjectId,
    /// First day.
    pub start: Day,
    /// Last planned day.
    pub end: Day,
    /// Effective last day when the cycle closed before `end` (the close day, UTC); `None` otherwise.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ended: Option<Day>,
    /// One-line goal.
    pub goal: String,
    /// Story points the team commits to, when set.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub capacity_points: Option<u32>,
    /// Life-cycle state.
    pub state: State,
    /// Member tickets, sorted.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tickets: Vec<TicketId>,
    /// Creation time (the `create` event).
    pub created: Stamp,
    /// Time of the latest event.
    pub updated: Stamp,
    /// Position among cycles sharing this date range, fixed at creation (1: the first); stored, written only when above 1.
    #[serde(default = "first_ordinal", skip_serializing_if = "is_first")]
    pub ordinal: u32,
}

/// The ordinal of a cycle that is first (or alone) in its date range.
const fn first_ordinal() -> u32 {
    1
}

/// True for the ordinal that needs no stored suffix.
#[allow(clippy::trivially_copy_pass_by_ref)] // serde `skip_serializing_if` passes a reference
const fn is_first(n: &u32) -> bool {
    *n == 1
}

impl Cycle {
    /// The alias of the cycle: `START..END`, with the stored `.N` appended from the second cycle of a shared date range.
    pub fn alias(&self) -> String {
        match self.ordinal {
            0 | 1 => format!("{}..{}", self.start, self.end),
            n => format!("{}..{}.{n}", self.start, self.end),
        }
    }

    /// The last day the cycle really covers: the early-close day when set, else the planned `end`.
    pub fn effective_end(&self) -> Day {
        self.ended.unwrap_or(self.end)
    }
}

/// A folded milestone or cycle.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Object {
    /// A milestone.
    Milestone(Milestone),
    /// A cycle.
    Cycle(Cycle),
}

impl Object {
    /// Which kind this is.
    pub const fn kind(&self) -> ObjectKind {
        match self {
            Self::Milestone(_) => ObjectKind::Milestone,
            Self::Cycle(_) => ObjectKind::Cycle,
        }
    }

    /// The identity.
    pub const fn id(&self) -> ObjectId {
        match self {
            Self::Milestone(m) => m.id,
            Self::Cycle(c) => c.id,
        }
    }

    /// The alias: the version of a milestone, the dates of a cycle.
    pub fn alias(&self) -> String {
        match self {
            Self::Milestone(m) => m.version.clone(),
            Self::Cycle(c) => c.alias(),
        }
    }

    /// The member tickets: epics of a milestone, tickets of a cycle.
    pub fn members(&self) -> &[TicketId] {
        match self {
            Self::Milestone(m) => &m.epics,
            Self::Cycle(c) => &c.tickets,
        }
    }

    /// Render the frontmatter file text.
    ///
    /// # Errors
    ///
    /// [`crate::PmError::Malformed`] when the state cannot be written as TOML.
    pub fn render(&self) -> crate::Result<String> {
        let label = format!("{}/{}/{}", self.kind().dir(), self.id(), self.kind().file());
        let front = match self {
            Self::Milestone(m) => toml::to_string(m),
            Self::Cycle(c) => toml::to_string(c),
        }
        .map_err(|e| crate::PmError::malformed(label, e.to_string()))?;
        Ok(frob_ledger::doc::fenced(&front, ""))
    }

    /// Parse the frontmatter file text of an object of `kind`; `label` names it in errors.
    ///
    /// # Errors
    ///
    /// [`crate::PmError::Malformed`] for a missing fence, bad TOML or an unknown key.
    pub fn parse(kind: ObjectKind, label: &str, text: &str) -> crate::Result<Self> {
        let bad = |m: String| crate::PmError::malformed(label, m);
        let (front, _body) =
            frob_ledger::doc::split_fenced(label, text).map_err(|e| bad(e.to_string()))?;
        match kind {
            ObjectKind::Milestone => toml::from_str(front)
                .map(Self::Milestone)
                .map_err(|e| bad(e.to_string())),
            ObjectKind::Cycle => toml::from_str(front)
                .map(Self::Cycle)
                .map_err(|e| bad(e.to_string())),
        }
    }
}
