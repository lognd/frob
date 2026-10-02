//! The ticket data model: enums, the frontmatter struct and the ticket document.
//!
//! Frontmatter is a cache of the event fold (`fold(events) == frontmatter` is
//! the integrity invariant), so every field here is derivable from events.

use std::fmt;
use std::str::FromStr;

use jiff::Timestamp;
use schemars::JsonSchema;
use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::id::TicketId;

/// Defines a kebab-case string enum with `as_str`, `FromStr`, `Display` and `ALL`.
macro_rules! string_enum {
    ($(#[$meta:meta])* $name:ident { $($(#[$vmeta:meta])* $variant:ident => $text:literal),+ $(,)? }) => {
        $(#[$meta])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize, JsonSchema)]
        pub enum $name {
            $($(#[$vmeta])* #[serde(rename = $text)] $variant),+
        }

        impl $name {
            /// Every variant, in declaration order.
            pub const ALL: &'static [Self] = &[$(Self::$variant),+];

            /// The spelling used in files, flags and JSON.
            pub const fn as_str(self) -> &'static str {
                match self { $(Self::$variant => $text),+ }
            }

            /// The accepted spellings, for error messages.
            pub const NAMES: &'static [&'static str] = &[$($text),+];
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(self.as_str())
            }
        }

        impl FromStr for $name {
            type Err = ParseEnumError;

            fn from_str(s: &str) -> Result<Self, Self::Err> {
                match s {
                    $($text => Ok(Self::$variant),)+
                    _ => Err(ParseEnumError {
                        what: stringify!($name),
                        input: s.to_owned(),
                        allowed: Self::NAMES,
                    }),
                }
            }
        }
    };
}

/// An unknown spelling of a closed enum.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("`{input}` is not a valid {what}; expected one of: {}", allowed.join(", "))]
pub struct ParseEnumError {
    /// The enum's type name.
    pub what: &'static str,
    /// The rejected input.
    pub input: String,
    /// The accepted spellings.
    pub allowed: &'static [&'static str],
}

string_enum!(
    /// What kind of work a ticket tracks (a milestone is never a type).
    TicketType {
        /// A large body of work with children.
        Epic => "epic",
        /// A user-visible capability.
        Story => "story",
        /// A unit of engineering work.
        Task => "task",
        /// A defect.
        Bug => "bug",
        /// A security issue.
        Security => "security",
        /// Documentation work.
        Docs => "docs",
        /// A property that must keep holding.
        Invariant => "invariant",
        /// An operational incident.
        Incident => "incident",
        /// Maintenance with no user-visible effect.
        Chore => "chore",
        /// A repo-declared type.
        Custom => "custom",
    }
);

string_enum!(
    /// The fixed workflow categories; `blocked` is derived, never stored.
    Category {
        /// Awaiting a decision to accept the ticket.
        Triage => "triage",
        /// Accepted and queued.
        Todo => "todo",
        /// Being worked.
        InProgress => "in-progress",
        /// Terminal; carries an outcome.
        Done => "done",
    }
);

string_enum!(
    /// Why a ticket reached `done`.
    Outcome {
        /// The work was completed and verified.
        Fixed => "fixed",
        /// Deliberately not done.
        WontFix => "wont-fix",
        /// Another ticket covers it.
        Duplicate => "duplicate",
        /// The report is not valid.
        Invalid => "invalid",
        /// Completed work with nothing to "fix" (a feature, a chore).
        Done => "done",
    }
);

string_enum!(
    /// Urgency, ascending.
    Priority {
        /// Whenever.
        Low => "low",
        /// The default.
        Medium => "medium",
        /// Soon.
        High => "high",
        /// Now.
        Critical => "critical",
    }
);

string_enum!(
    /// Subtype of a `comment` event.
    CommentSubtype {
        /// A plain note.
        Note => "note",
        /// A decision and its reasons.
        Decision => "decision",
        /// An open question.
        Question => "question",
        /// An answer to a question.
        Answer => "answer",
    }
);

string_enum!(
    /// Kinds of exception recorded in M1 (hotfix arrives later).
    ExceptionKind {
        /// A finding is accepted with a reason.
        Accept => "accept",
        /// A finding is deferred to a later ticket.
        Defer => "defer",
    }
);

string_enum!(
    /// Whether a `link` event adds or removes an edge.
    LinkOp {
        /// Add the edge.
        Add => "add",
        /// Remove the edge.
        Remove => "remove",
    }
);

impl Category {
    /// True for `done`, the only terminal category.
    pub const fn is_terminal(self) -> bool {
        matches!(self, Self::Done)
    }
}

/// Story points: a Fibonacci number from 1 to 13.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Points(u8);

impl Points {
    /// The accepted values.
    pub const ALLOWED: [u8; 6] = [1, 2, 3, 5, 8, 13];

    /// Validate `n` as story points.
    ///
    /// # Errors
    ///
    /// [`PointsError`] when `n` is not in [`Points::ALLOWED`].
    pub fn new(n: u8) -> Result<Self, PointsError> {
        if Self::ALLOWED.contains(&n) {
            Ok(Self(n))
        } else {
            Err(PointsError(i64::from(n)))
        }
    }

    /// The numeric value.
    pub const fn get(self) -> u8 {
        self.0
    }
}

/// A rejected points value.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("points must be one of 1, 2, 3, 5, 8, 13 (got {0})")]
pub struct PointsError(pub i64);

impl FromStr for Points {
    type Err = PointsError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let n: i64 = s.trim().parse().map_err(|_| PointsError(-1))?;
        u8::try_from(n)
            .map_err(|_| PointsError(n))
            .and_then(Self::new)
    }
}

impl Serialize for Points {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_u8(self.0)
    }
}

impl<'de> Deserialize<'de> for Points {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let n = i64::deserialize(d)?;
        u8::try_from(n)
            .map_err(|_| PointsError(n))
            .and_then(Self::new)
            .map_err(serde::de::Error::custom)
    }
}

impl JsonSchema for Points {
    fn schema_name() -> std::borrow::Cow<'static, str> {
        "Points".into()
    }

    fn json_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
        schemars::json_schema!({ "type": "integer", "enum": [1, 2, 3, 5, 8, 13] })
    }
}

/// An RFC 3339 instant with whole-second precision, always rendered in UTC (`Z`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Stamp(Timestamp);

impl Stamp {
    /// The current time, truncated to the second.
    pub fn now() -> Self {
        Self::from_unix(Timestamp::now().as_second())
    }

    /// An instant from Unix seconds (clamped into jiff's range).
    pub fn from_unix(secs: i64) -> Self {
        Self(Timestamp::from_second(secs).unwrap_or(Timestamp::UNIX_EPOCH))
    }

    /// Unix seconds.
    pub fn unix(self) -> i64 {
        self.0.as_second()
    }
}

impl fmt::Display for Stamp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0.strftime("%Y-%m-%dT%H:%M:%SZ"))
    }
}

impl FromStr for Stamp {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        s.parse::<Timestamp>()
            .map(|t| Self::from_unix(t.as_second()))
            .map_err(|e| format!("`{s}` is not an RFC 3339 timestamp: {e}"))
    }
}

impl Serialize for Stamp {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for Stamp {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        String::deserialize(d)?
            .parse()
            .map_err(serde::de::Error::custom)
    }
}

impl JsonSchema for Stamp {
    fn schema_name() -> std::borrow::Cow<'static, str> {
        "Stamp".into()
    }

    fn json_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
        schemars::json_schema!({ "type": "string", "format": "date-time" })
    }
}

string_enum!(
    /// Link kinds of the canonical table (tickets.md section 3), both directions.
    LinkKind {
        /// This ticket blocks the target.
        Blocks => "blocks",
        /// The target blocks this ticket.
        BlockedBy => "blocked-by",
        /// Related, symmetric.
        Relates => "relates",
        /// This ticket duplicates the target.
        Duplicates => "duplicates",
        /// The target duplicates this ticket.
        DuplicatedBy => "duplicated-by",
        /// This ticket causes the target.
        Causes => "causes",
        /// The target causes this ticket.
        CausedBy => "caused-by",
        /// This ticket was split out of the target.
        SplitFrom => "split-from",
        /// The target was split out of this ticket.
        Splits => "splits",
        /// This ticket was discovered while working the target.
        DiscoveredFrom => "discovered-from",
        /// The target was discovered while working this ticket.
        Spawned => "spawned",
        /// This ticket enables the target story.
        EnablerFor => "enabler-for",
        /// The target enables this story.
        EnabledBy => "enabled-by",
        /// This ticket supersedes the target.
        Supersedes => "supersedes",
        /// The target supersedes this ticket.
        SupersededBy => "superseded-by",
    }
);

/// One typed edge stored on its source ticket.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Link {
    /// Link kind, in the direction written from this ticket.
    pub kind: LinkKind,
    /// The other ticket.
    pub target: TicketId,
}

/// One acceptance criterion and whether evidence is bound to it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Acceptance {
    /// The criterion text.
    pub text: String,
    /// True once evidence is bound (arrives with frob-evidence; false in M1).
    #[serde(default)]
    pub bound: bool,
}

/// The TOML frontmatter of `ticket.md`: the fold of the ticket's events.
///
/// Table-valued fields come last so the TOML writer emits plain values first.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Frontmatter {
    /// The ticket id (also the directory name).
    pub id: TicketId,
    /// Ticket title.
    pub title: String,
    /// Ticket type.
    #[serde(rename = "type")]
    pub ty: TicketType,
    /// Free-form flavour, for example `user_story`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub flavour: Option<String>,
    /// Workflow category (`blocked` is derived and never stored).
    pub category: Category,
    /// Terminal outcome; present exactly when the category is `done`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub outcome: Option<Outcome>,
    /// Priority.
    pub priority: Priority,
    /// Story points.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub points: Option<Points>,
    /// Parent ticket.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent: Option<TicketId>,
    /// Who filed the ticket.
    pub reporter: String,
    /// Optional assignee.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub assignee: Option<String>,
    /// Creation time.
    pub created: Stamp,
    /// Time of the latest event.
    pub updated: Stamp,
    /// Story persona.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub persona: Option<String>,
    /// Story capability.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub capability: Option<String>,
    /// Story outcome text ("so that ...").
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub outcome_text: Option<String>,
    /// Key that made `ticket new` idempotent.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub idempotency_key: Option<String>,
    /// Ids from other systems (v1 ids such as `T-0042`).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub aliases: Vec<String>,
    /// Labels.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub labels: Vec<String>,
    /// Write-scope globs.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub scope: Vec<String>,
    /// Typed edges to other tickets.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub links: Vec<Link>,
    /// Acceptance criteria.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub acceptance: Vec<Acceptance>,
}

/// A whole ticket document: frontmatter plus markdown body.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Ticket {
    /// The frontmatter.
    pub front: Frontmatter,
    /// The markdown body, normalized (no leading blank line, no trailing newlines).
    pub body: String,
}

/// Strip leading blank lines and trailing newlines so bodies compare stably.
pub fn normalize_body(body: &str) -> String {
    body.trim_start_matches(['\n', '\r'])
        .trim_end_matches(['\n', '\r'])
        .to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn points_accept_fibonacci_only() {
        assert!("5".parse::<Points>().is_ok());
        assert!("4".parse::<Points>().is_err());
        assert!("21".parse::<Points>().is_err());
        assert!("x".parse::<Points>().is_err());
    }

    #[test]
    fn enums_round_trip_through_text() {
        for c in Category::ALL {
            assert_eq!(c.as_str().parse::<Category>().ok(), Some(*c));
        }
        let err = "blocked".parse::<Category>().unwrap_err();
        assert!(err.to_string().contains("in-progress"));
    }

    #[test]
    fn stamp_renders_utc_seconds() {
        let s: Stamp = "2026-10-02T14:03:11Z".parse().expect("parse");
        assert_eq!(s.to_string(), "2026-10-02T14:03:11Z");
        let off: Stamp = "2026-10-02T16:03:11+02:00".parse().expect("parse");
        assert_eq!(off, s);
    }
}
