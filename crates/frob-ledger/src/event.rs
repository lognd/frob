//! Events: one append-only TOML file per state change, `events/<ulid>.toml`.
//!
//! Every kind of event the model knows is an [`EventBody`] variant. The kinds
//! of the design table that no M1 verb produces (`evidence`, `lease`,
//! `review`, `cycle`, `attempt`, `cost`) parse as
//! [`EventBody::Other`] and fold to no state change, so a ledger written by a
//! later frob still folds here.

use gob_git::RelPath;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::error::{LedgerError, Result};
use crate::id::{EventId, TicketId};
use crate::model::{
    Category, Class, CommentSubtype, ExceptionKind, Link, LinkKind, LinkOp, Outcome, Points,
    Priority, Stamp, TicketType, TriageAction,
};

/// Serde adapters that persist a [`RelPath`] as its validated string (`RelPath` itself carries no serde).
pub(crate) mod rel_path {
    use gob_git::RelPath;
    use serde::{Deserialize, Deserializer, Serializer};

    /// Write `p` as its slash-separated string.
    pub fn serialize<S: Serializer>(p: &RelPath, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(p.as_str())
    }

    /// Read a string and validate it as a [`RelPath`], refusing absolute or dot-segment paths.
    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<RelPath, D::Error> {
        RelPath::new(String::deserialize(d)?).map_err(serde::de::Error::custom)
    }
}

/// Serde adapters for a list of [`RelPath`]s, each validated on read.
pub(crate) mod rel_paths {
    use gob_git::RelPath;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    /// Write `ps` as a list of strings.
    pub fn serialize<S: Serializer>(ps: &[RelPath], s: S) -> Result<S::Ok, S::Error> {
        ps.iter()
            .map(RelPath::as_str)
            .collect::<Vec<_>>()
            .serialize(s)
    }

    /// Read a list of strings, validating each as a [`RelPath`].
    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Vec<RelPath>, D::Error> {
        Vec::<String>::deserialize(d)?
            .into_iter()
            .map(|p| RelPath::new(p).map_err(serde::de::Error::custom))
            .collect()
    }
}

/// Revision of the event file format written by this crate (`rev` in every file).
pub const EVENT_REV: u32 = 1;

/// The initial state of a ticket, carried by its `create` event.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CreateData {
    /// Title.
    pub title: String,
    /// Ticket type.
    #[serde(rename = "type")]
    pub ty: TicketType,
    /// Starting category: `triage` or `todo`.
    pub category: Category,
    /// Priority.
    pub priority: Priority,
    /// Class of service; absent means `standard`.
    #[serde(default, skip_serializing_if = "Class::is_standard")]
    pub class: Class,
    /// Due date.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub due: Option<Stamp>,
    /// Free-form flavour.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub flavour: Option<String>,
    /// Story points.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub points: Option<Points>,
    /// Parent ticket.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent: Option<TicketId>,
    /// Assignee.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub assignee: Option<String>,
    /// Story persona.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub persona: Option<String>,
    /// Story capability.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub capability: Option<String>,
    /// Story outcome text.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub outcome_text: Option<String>,
    /// Idempotency key of the `new` call.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub idempotency_key: Option<String>,
    /// Aliases (v1 ids).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub aliases: Vec<String>,
    /// Labels.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub labels: Vec<String>,
    /// Scope globs.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub scope: Vec<String>,
    /// Acceptance criteria texts.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub acceptance: Vec<String>,
    /// Markdown body.
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub body: String,
    /// Initial links.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub links: Vec<Link>,
}

/// A change to one frontmatter field; `old` lets the fold report concurrent conflicts.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FieldChange {
    /// Field name (see [`crate::schema::FIELDS`]).
    pub field: String,
    /// Value before the change; absent when the field was unset.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub old: Option<toml::Value>,
    /// Value after the change; absent when the field is unset by this change.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub new: Option<toml::Value>,
    /// Why, required for some fields.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    /// Acceptance edits only: for each criterion of `old`, its 1-based position in `new`, or 0 when removed.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub moved: Option<Vec<usize>>,
}

/// A category change; `done` carries the outcome.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TransitionData {
    /// Category before.
    pub from: Category,
    /// Category after.
    pub to: Category,
    /// Outcome, present exactly when `to` is `done`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub outcome: Option<Outcome>,
    /// Why.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// A comment on a ticket.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CommentData {
    /// Note, decision, question or answer.
    pub subtype: CommentSubtype,
    /// Markdown text.
    pub body: String,
}

/// Adding or removing a typed link.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct LinkData {
    /// Add or remove.
    pub op: LinkOp,
    /// Link kind as written from this ticket.
    pub link: LinkKind,
    /// The other ticket.
    pub target: TicketId,
}

/// An accepted or deferred finding (M1 kinds only).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ExceptionData {
    /// Accept or defer.
    pub exception: ExceptionKind,
    /// The rule id.
    pub rule: String,
    /// The site (path or symref) the exception covers.
    pub site: String,
    /// Why.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// A measurement offered for some acceptance criteria, written by frob-evidence.
///
/// The fold needs only `accepts`; every other key of the record belongs to
/// frob-evidence and rides along untouched in `record`, so the file keeps its
/// exact keys.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceData {
    /// 1-based acceptance criteria offered, numbered as the list stood when written.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub accepts: Vec<usize>,
    /// The rest of the record (provider, ref, digest, status, ...), owned by frob-evidence.
    #[serde(flatten)]
    pub record: toml::Table,
}

/// A close that bypassed the evidence guard (`--no-evidence --reason`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct EvidenceBypassData {
    /// Why the guard was bypassed.
    pub reason: String,
}

/// A ticket exempted from the changelog-fragment requirement (`--no-changelog --reason`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct ChangelogExemptData {
    /// Why the change needs no changelog note.
    pub reason: String,
}

/// A done close that skipped the branch-merged guard (`--no-land --reason`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct LandExemptData {
    /// Why the ticket is done although its branch holds commits not on the base.
    pub reason: String,
}

/// One digest recomputed by a scrub: the event file and the digest before and after.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct DigestChange {
    /// Repo-relative path of the event file whose `digest` changed.
    #[serde(with = "rel_path")]
    #[schemars(with = "String")]
    pub file: RelPath,
    /// The digest before the scrub.
    pub old: String,
    /// The digest over the scrubbed text.
    pub new: String,
}

/// A doctor repair rewrote files of this ticket to remove absolute home paths (audit only).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct ScrubData {
    /// Why the files were rewritten.
    pub reason: String,
    /// Repo-relative paths of the rewritten files.
    #[serde(with = "rel_paths")]
    #[schemars(with = "Vec<String>")]
    pub files: Vec<RelPath>,
    /// Digests recomputed over scrubbed evidence text.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub digests: Vec<DigestChange>,
}

/// One decision on a ticket in the triage inbox (`ticket triage`).
///
/// An accept, decline or duplicate rides in the same commit as the `transition`
/// (and, for a duplicate, `link`) event it explains; a snooze changes no field.
/// The fold ignores the event: the inbox reads it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TriageData {
    /// What was decided.
    pub action: TriageAction,
    /// A snooze hides the ticket from the inbox until this instant.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub until: Option<Stamp>,
    /// Why, when the verb was given a reason.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// A branch landed on a base ref.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct LandData {
    /// Full name of the ref that advanced.
    pub base_ref: String,
    /// The commit the base ref was advanced to.
    pub commit: String,
    /// The ticket branch that was landed.
    pub branch: String,
    /// Whether the base branch was pushed.
    pub pushed: bool,
}

/// What a `proposal` or `proposal-superseded` event records: a tracker edit held for review (mirror.md 3.5).
///
/// Stored by reference: only a digest of the value and a capped excerpt enter the ledger.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ProposalData {
    /// The tracker's event id for the edit: the idempotency key of the proposal.
    pub tracker_event: String,
    /// The tracker item (issue) id.
    pub item: String,
    /// The ticket field the edit touches.
    pub field: String,
    /// The tracker user id of the editor (never the login).
    pub actor_id: String,
    /// When the editor made the edit.
    pub time: Stamp,
    /// Digest of the full proposed value.
    pub digest: String,
    /// Capped, escaped excerpt of the value.
    pub excerpt: String,
    /// Where the text came from; always `tracker` for now.
    pub origin: String,
    /// Tracker event id of the proposal this one replaces (`proposal-superseded` only).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub supersedes: Option<String>,
}

/// What `proposal-accepted`, `proposal-declined` and `proposal-expired` record: a proposal closed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ProposalCloseData {
    /// The tracker event id of the proposal that closed.
    pub tracker_event: String,
    /// Why, when given.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// The kind-specific part of an event; the `kind` key selects the variant.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "kebab-case")]
pub enum EventBody {
    /// The ticket's birth: its initial field values.
    Create(Box<CreateData>),
    /// A frontmatter field changed.
    Field(FieldChange),
    /// The category changed.
    Transition(TransitionData),
    /// A comment was added.
    Comment(CommentData),
    /// A link was added or removed.
    Link(LinkData),
    /// A finding was accepted or deferred.
    Exception(ExceptionData),
    /// A measurement offered for acceptance criteria; binds them in the fold.
    Evidence(EvidenceData),
    /// The evidence guard was bypassed at close; audit only.
    EvidenceBypass(EvidenceBypassData),
    /// The ticket was exempted from the changelog-fragment requirement; audit only.
    ChangelogExempt(ChangelogExemptData),
    /// The ticket closed done without its branch merged into the base (`--no-land`); audit only.
    LandExempt(LandExemptData),
    /// The ticket's branch was landed; audit only.
    Land(LandData),
    /// A doctor repair scrubbed absolute home paths from the ticket's files; audit only.
    Scrub(ScrubData),
    // frob:ticket 01M44C546DQRE4D11HHPM0HX6M
    /// A triage decision (accept, decline, snooze, duplicate); the inbox reads it, the fold ignores it.
    Triage(TriageData),
    /// A tracker edit held as a proposal; the proposal fold reads it, the ticket fold ignores it.
    Proposal(ProposalData),
    /// A proposal replaced by a later edit of the same actor and field.
    ProposalSuperseded(ProposalData),
    /// A proposal accepted into the ticket.
    ProposalAccepted(ProposalCloseData),
    /// A proposal declined.
    ProposalDeclined(ProposalCloseData),
    /// A proposal that outlived `proposal_ttl_days`.
    ProposalExpired(ProposalCloseData),
    /// A kind this version does not interpret; it folds to no change.
    #[serde(other)]
    Other,
}

/// The on-disk shape of an event file: envelope plus body.
#[derive(Debug, Serialize, Deserialize)]
struct EventFile {
    #[serde(flatten)]
    body: EventBody,
    at: Stamp,
    actor: String,
    rev: u32,
}

/// One event of one ticket, with its id (the file stem).
#[derive(Debug, Clone, PartialEq)]
pub struct Event {
    /// Event id.
    pub id: EventId,
    /// When it happened (RFC 3339, whole seconds).
    pub at: Stamp,
    /// Git identity or configured actor: an audit label, not authorization.
    pub actor: String,
    /// Event format revision.
    pub rev: u32,
    /// The `kind` string as written in the file.
    pub kind: String,
    /// The parsed body.
    pub body: EventBody,
}

impl Event {
    /// A new event stamped `at`, with a fresh id.
    pub fn new(at: Stamp, actor: &str, body: EventBody) -> Self {
        let kind = kind_name(&body).to_owned();
        let event = Self {
            id: EventId::mint(),
            at: at.seconds(),
            actor: actor.to_owned(),
            rev: EVENT_REV,
            kind,
            body,
        };
        tracing::debug!(event = %event.id, kind = %event.kind, "event created");
        event
    }

    /// Render the event file (TOML).
    ///
    /// # Errors
    ///
    /// [`LedgerError::Malformed`] when the body cannot be written as TOML.
    pub fn to_toml(&self) -> Result<String> {
        let file = EventFile {
            body: self.body.clone(),
            at: self.at,
            actor: self.actor.clone(),
            rev: self.rev,
        };
        toml::to_string(&file).map_err(|e| LedgerError::malformed(self.path_label(), e.to_string()))
    }

    /// Parse the file `<id>.toml` whose text is `text`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Malformed`] on bad TOML, a missing envelope key or a bad value.
    pub fn parse(id: EventId, text: &str) -> Result<Self> {
        let label = format!("events/{id}.toml");
        let table: toml::Table = text
            .parse()
            .map_err(|e: toml::de::Error| LedgerError::malformed(&label, e.to_string()))?;
        let kind = table
            .get("kind")
            .and_then(toml::Value::as_str)
            .ok_or_else(|| LedgerError::malformed(&label, "missing `kind`"))?
            .to_owned();
        let file: EventFile = table
            .try_into()
            .map_err(|e: toml::de::Error| LedgerError::malformed(&label, e.to_string()))?;
        Ok(Self {
            id,
            at: file.at,
            actor: file.actor,
            rev: file.rev,
            kind,
            body: file.body,
        })
    }

    /// Ordering key: (ULID time, `at`, id), the fold order of the design.
    pub fn order_key(&self) -> (u64, i64, EventId) {
        (self.id.timestamp_ms(), self.at.unix(), self.id)
    }

    /// Repo-relative file name under the ticket directory.
    pub fn file_name(&self) -> String {
        format!("{}.toml", self.id)
    }

    fn path_label(&self) -> String {
        format!("events/{}.toml", self.id)
    }
}

/// A recorded changelog exemption: who exempted the ticket, when, and why.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ChangelogExemption {
    /// Who recorded the exemption.
    pub actor: String,
    /// When it was recorded.
    pub at: String,
    /// The reason given.
    pub reason: String,
}

/// The latest `changelog-exempt` event among `events`, if any (audit only; the fold ignores it).
pub fn changelog_exemption(events: &[Event]) -> Option<ChangelogExemption> {
    events.iter().rev().find_map(|e| match &e.body {
        EventBody::ChangelogExempt(d) => Some(ChangelogExemption {
            actor: e.actor.clone(),
            at: e.at.to_string(),
            reason: d.reason.clone(),
        }),
        _ => None,
    })
}

/// The latest `land-exempt` event among `events`, if any (audit only; the fold ignores it).
pub fn land_exemption(events: &[Event]) -> Option<ChangelogExemption> {
    events.iter().rev().find_map(|e| match &e.body {
        EventBody::LandExempt(d) => Some(ChangelogExemption {
            actor: e.actor.clone(),
            at: e.at.to_string(),
            reason: d.reason.clone(),
        }),
        _ => None,
    })
}

/// Sort events into fold order.
pub fn sort_events(events: &mut [Event]) {
    events.sort_by_key(Event::order_key);
}

/// The `kind` spelling of a body (`other` for uninterpreted kinds).
pub const fn kind_name(body: &EventBody) -> &'static str {
    match body {
        EventBody::Create(_) => "create",
        EventBody::Field(_) => "field",
        EventBody::Transition(_) => "transition",
        EventBody::Comment(_) => "comment",
        EventBody::Link(_) => "link",
        EventBody::Exception(_) => "exception",
        EventBody::Evidence(_) => "evidence",
        EventBody::EvidenceBypass(_) => "evidence-bypass",
        EventBody::ChangelogExempt(_) => "changelog-exempt",
        EventBody::LandExempt(_) => "land-exempt",
        EventBody::Land(_) => "land",
        EventBody::Scrub(_) => "scrub",
        EventBody::Triage(_) => "triage",
        EventBody::Proposal(_) => "proposal",
        EventBody::ProposalSuperseded(_) => "proposal-superseded",
        EventBody::ProposalAccepted(_) => "proposal-accepted",
        EventBody::ProposalDeclined(_) => "proposal-declined",
        EventBody::ProposalExpired(_) => "proposal-expired",
        EventBody::Other => "other",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn proposal_data(key: &str, supersedes: Option<&str>) -> ProposalData {
        ProposalData {
            tracker_event: key.into(),
            item: "I_1".into(),
            field: "title".into(),
            actor_id: "42".into(),
            time: "2026-11-01T00:00:00Z".parse().expect("stamp"),
            digest: "sha256:ab".into(),
            excerpt: "new title".into(),
            origin: "tracker".into(),
            supersedes: supersedes.map(str::to_owned),
        }
    }

    fn create() -> CreateData {
        CreateData {
            title: "Parse the thing".into(),
            ty: TicketType::Task,
            category: Category::Todo,
            priority: Priority::Medium,
            class: crate::model::Class::Standard,
            due: None,
            flavour: None,
            points: Some(Points::new(3).expect("points")),
            parent: None,
            assignee: None,
            persona: None,
            capability: None,
            outcome_text: None,
            idempotency_key: Some("k1".into()),
            aliases: vec!["T-0042".into()],
            labels: vec!["a".into()],
            scope: vec!["src/**".into()],
            acceptance: vec!["it works".into()],
            body: "line one\n\nline two\n".into(),
            links: vec![Link {
                kind: LinkKind::BlockedBy,
                target: TicketId::mint(),
            }],
        }
    }

    #[test]
    fn every_kind_round_trips() {
        let bodies = [
            EventBody::Create(Box::new(create())),
            EventBody::Field(FieldChange {
                field: "points".into(),
                old: Some(toml::Value::Integer(3)),
                new: Some(toml::Value::Integer(5)),
                reason: None,
                moved: None,
            }),
            EventBody::Field(FieldChange {
                field: "labels".into(),
                old: None,
                new: Some(toml::Value::Array(vec!["x".into()])),
                reason: Some("why".into()),
                moved: None,
            }),
            EventBody::Transition(TransitionData {
                from: Category::Todo,
                to: Category::Done,
                outcome: Some(Outcome::Fixed),
                reason: None,
            }),
            EventBody::Comment(CommentData {
                subtype: CommentSubtype::Decision,
                body: "go".into(),
            }),
            EventBody::Link(LinkData {
                op: LinkOp::Add,
                link: LinkKind::Relates,
                target: TicketId::mint(),
            }),
            EventBody::Exception(ExceptionData {
                exception: ExceptionKind::Accept,
                rule: "COV006".into(),
                site: "src/a.rs".into(),
                reason: Some("generated".into()),
            }),
            EventBody::Evidence(EvidenceData {
                accepts: vec![1, 3],
                record: "provider = \"command\"\nref = \"cargo test\"\npassed = true\nsize = 0\n"
                    .parse()
                    .expect("table"),
            }),
            EventBody::EvidenceBypass(EvidenceBypassData {
                reason: "docs only".into(),
            }),
            EventBody::ChangelogExempt(ChangelogExemptData {
                reason: "design document".into(),
            }),
            EventBody::LandExempt(LandExemptData {
                reason: "work lives on another branch".into(),
            }),
            EventBody::Land(LandData {
                base_ref: "refs/heads/main".into(),
                commit: "abc".into(),
                branch: "ticket/X".into(),
                pushed: false,
            }),
            EventBody::Scrub(ScrubData {
                reason: "absolute home paths".into(),
                files: vec![RelPath::new("tickets/X/events/E.toml").expect("rel")],
                digests: vec![DigestChange {
                    file: RelPath::new("tickets/X/events/E.toml").expect("rel"),
                    old: "a".into(),
                    new: "b".into(),
                }],
            }),
            EventBody::Triage(TriageData {
                action: TriageAction::Snooze,
                until: Some("2026-11-01T00:00:00Z".parse().expect("stamp")),
                reason: Some("after the release".into()),
            }),
            EventBody::Proposal(proposal_data("t1", None)),
            EventBody::ProposalSuperseded(proposal_data("t2", Some("t1"))),
            EventBody::ProposalAccepted(ProposalCloseData {
                tracker_event: "t2".into(),
                reason: None,
            }),
            EventBody::ProposalDeclined(ProposalCloseData {
                tracker_event: "t3".into(),
                reason: Some("no".into()),
            }),
            EventBody::ProposalExpired(ProposalCloseData {
                tracker_event: "t4".into(),
                reason: None,
            }),
        ];
        for body in bodies {
            let ev = Event::new(gob_time::Stamp::from_unix(1_800_000_000), "logan", body);
            let text = ev.to_toml().expect("render");
            assert!(text.starts_with("kind = "), "kind first: {text}");
            let back = Event::parse(ev.id, &text).expect("parse");
            assert_eq!(back, ev, "{text}");
        }
    }

    // frob:ticket 01M4069VZVMHVZ15RSPZQRNCXY
    #[test]
    fn create_without_a_class_is_standard_and_standard_is_never_written() {
        let old = "kind = \"create\"\ntitle = \"Old\"\ntype = \"task\"\ncategory = \"todo\"\npriority = \"medium\"\nat = \"2026-10-02T14:03:11Z\"\nactor = \"a\"\nrev = 1\n";
        let ev = Event::parse(EventId::mint(), old).expect("parse an event written before classes");
        let EventBody::Create(c) = &ev.body else {
            panic!("not a create: {:?}", ev.body)
        };
        assert_eq!(c.class, Class::Standard);
        let text = ev.to_toml().expect("render");
        assert!(!text.contains("class"), "{text}");
        let mut hot = create();
        hot.class = Class::Expedite;
        let text = Event::new(
            gob_time::Stamp::from_unix(1_800_000_000),
            "a",
            EventBody::Create(Box::new(hot)),
        )
        .to_toml()
        .expect("render");
        assert!(text.contains("class = \"expedite\""), "{text}");
    }

    #[test]
    fn unknown_kinds_parse_as_other() {
        let text = "kind = \"lease\"\nat = \"2026-10-02T14:03:11Z\"\nactor = \"a\"\nrev = 1\nverdict = \"passed\"\n";
        let ev = Event::parse(EventId::mint(), text).expect("parse");
        assert_eq!(ev.body, EventBody::Other);
        assert_eq!(ev.kind, "lease");
    }

    #[test]
    fn missing_envelope_is_malformed() {
        let err = Event::parse(EventId::mint(), "kind = \"comment\"\n").unwrap_err();
        assert!(err.to_string().starts_with("E-TICKET-FORMAT"));
    }
}
