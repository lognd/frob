//! `IssueProjection` (mirror.md 2.1): the tracker-independent description of one ticket.
//!
//! The producer folds a ticket's facts into one typed value; adapters route it to a tracker.
//! Nothing here is tracker-shaped: labels, priorities and relations stay typed.

// frob:ticket 01M3ZX832JK52FXBPPCCGTDRTG

use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};
use tracing::{debug, trace};

/// Ticket identity: what an adapter needs to find and link the ticket.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Identity {
    /// The ticket ULID (stored where the adapter can search for it).
    pub ulid: String,
    /// Short handle such as `~CGTDRTG`.
    pub handle: String,
    /// Other names the ticket answers to.
    pub aliases: Vec<String>,
    /// Repository URL.
    pub repository: String,
    /// Path of the ticket in the ledger.
    pub ledger_path: String,
}

/// One Given/When/Then acceptance criterion.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Criterion {
    /// The criterion text.
    pub text: String,
    /// Whether evidence is bound to it.
    pub bound: bool,
}

/// A piece of evidence: a link and its verdict.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvidenceItem {
    /// What the evidence is (test id, rule id, URL).
    pub reference: String,
    /// The verdict (`pass`, `fail`, ...).
    pub verdict: String,
}

/// The kind of a body section, in rendering order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SectionKind {
    /// Free-text summary.
    Summary,
    /// Acceptance criteria.
    Acceptance,
    /// Scope globs.
    Scope,
    /// Evidence links and verdicts.
    Evidence,
    /// Relation links rendered as text.
    Links,
    /// Notice that the body is generated.
    ManagedNotice,
}

/// One ordered, typed body section with its markdown.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Section {
    /// Which kind of section this is.
    pub kind: SectionKind,
    /// The heading adapters may show.
    pub heading: String,
    /// The section body as markdown.
    pub markdown: String,
}

/// Typed classification values (never pre-rendered labels).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Classification {
    /// Ticket type.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ticket_type: Option<String>,
    /// Labels.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub labels: Option<Vec<String>>,
    /// Priority.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub priority: Option<String>,
    /// Story points.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub points: Option<u32>,
    /// Milestone.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub milestone: Option<String>,
    /// Epic.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub epic: Option<String>,
}

/// Workflow category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Category {
    /// Not started.
    Todo,
    /// In progress.
    Doing,
    /// Finished.
    Done,
}

/// How a closed ticket ended.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    /// Completed.
    Done,
    /// Cut from scope.
    Dropped,
    /// Replaced by another ticket.
    Superseded,
    /// Duplicate of another ticket.
    Duplicate,
}

/// Ticket state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct State {
    /// Workflow category.
    pub category: Category,
    /// Outcome, once closed.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub outcome: Option<Outcome>,
    /// Reason text for the outcome.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// Relation kinds between tickets.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationKind {
    /// The parent ticket.
    Parent,
    /// A child ticket.
    Child,
    /// This ticket waits on the target.
    BlockedBy,
    /// The target waits on this ticket.
    Blocks,
    /// Loosely related.
    Relates,
    /// This ticket duplicates the target.
    Duplicates,
    /// This ticket supersedes the target.
    Supersedes,
}

/// A typed edge to another ticket.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Relation {
    /// The edge kind.
    pub kind: RelationKind,
    /// Target ULID.
    pub ulid: String,
    /// Target handle.
    pub handle: String,
}

/// Owner and assignee as frob identities.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct People {
    /// Reporter or owner.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub owner: Option<String>,
    /// Assignee.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub assignee: Option<String>,
}

/// Where a projection came from.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Provenance {
    /// Last ledger event ULID folded in.
    pub last_event: String,
    /// Digest of the projection (this field blanked), compared by divergence detection.
    pub render_digest: String,
    /// Producer version.
    pub producer_version: String,
}

/// The tracker-independent description of one ticket.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IssueProjection {
    /// Identity.
    pub identity: Identity,
    /// Title.
    pub title: String,
    /// Ordered typed sections.
    pub sections: Vec<Section>,
    /// Classification.
    pub classification: Classification,
    /// State.
    pub state: State,
    /// Typed relations, sorted.
    pub relations: Vec<Relation>,
    /// People.
    pub people: People,
    /// Provenance.
    pub provenance: Provenance,
    /// Names of fields withheld by `[mirror] exclude`; never sent.
    pub private: Vec<String>,
}

/// Everything the producer folds from the ledger for one ticket.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TicketFacts {
    /// Identity.
    pub identity: Identity,
    /// Title.
    pub title: String,
    /// Summary text (ticket body).
    pub summary: String,
    /// Acceptance criteria.
    pub acceptance: Vec<Criterion>,
    /// Scope globs.
    pub scope: Vec<String>,
    /// Evidence.
    pub evidence: Vec<EvidenceItem>,
    /// Classification.
    pub classification: Classification,
    /// State.
    pub state: State,
    /// Relations (any order).
    pub relations: Vec<Relation>,
    /// People.
    pub people: People,
    /// Last ledger event ULID.
    pub last_event: String,
}

/// Fields that `[mirror] exclude` may name.
pub const EXCLUDABLE: &[&str] = &[
    "summary",
    "acceptance",
    "scope",
    "evidence",
    "labels",
    "priority",
    "points",
    "milestone",
    "epic",
    "owner",
    "assignee",
    "reason",
];

fn md_list<I: IntoIterator<Item = String>>(items: I) -> String {
    items
        .into_iter()
        .map(|i| format!("- {i}"))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Apply exclusion to the non-section fields; `keep` records what it withholds.
fn redact(
    facts: &TicketFacts,
    keep: &mut impl FnMut(&str) -> bool,
) -> (Classification, People, State) {
    let mut c = facts.classification.clone();
    if !keep("labels") {
        c.labels = None;
    }
    if !keep("priority") {
        c.priority = None;
    }
    if !keep("points") {
        c.points = None;
    }
    if !keep("milestone") {
        c.milestone = None;
    }
    if !keep("epic") {
        c.epic = None;
    }
    let mut people = facts.people.clone();
    if !keep("owner") {
        people.owner = None;
    }
    if !keep("assignee") {
        people.assignee = None;
    }
    let mut state = facts.state.clone();
    if !keep("reason") {
        state.reason = None;
    }
    (c, people, state)
}

/// Fold `facts` into a projection, withholding fields named in `exclude` (recorded in `private`).
pub fn project(
    facts: &TicketFacts,
    exclude: &BTreeSet<String>,
    producer_version: &str,
) -> IssueProjection {
    let mut private: BTreeSet<String> = BTreeSet::new();
    let mut keep = |f: &str| -> bool {
        if exclude.contains(f) {
            trace!(field = f, "projection: field excluded");
            private.insert(f.to_owned());
            false
        } else {
            true
        }
    };

    let mut sections = Vec::new();
    if keep("summary") {
        sections.push(Section {
            kind: SectionKind::Summary,
            heading: "Summary".into(),
            markdown: facts.summary.clone(),
        });
    }
    if keep("acceptance") {
        let md = md_list(
            facts
                .acceptance
                .iter()
                .map(|c| format!("[{}] {}", if c.bound { "x" } else { " " }, c.text)),
        );
        sections.push(Section {
            kind: SectionKind::Acceptance,
            heading: "Acceptance".into(),
            markdown: md,
        });
    }
    if keep("scope") {
        let md = md_list(facts.scope.iter().map(|s| format!("`{s}`")));
        sections.push(Section {
            kind: SectionKind::Scope,
            heading: "Scope".into(),
            markdown: md,
        });
    }
    if keep("evidence") {
        let md = md_list(
            facts
                .evidence
                .iter()
                .map(|e| format!("{}: {}", e.reference, e.verdict)),
        );
        sections.push(Section {
            kind: SectionKind::Evidence,
            heading: "Evidence".into(),
            markdown: md,
        });
    }
    let mut relations = facts.relations.clone();
    relations.sort();
    relations.dedup();
    let links = md_list(
        relations
            .iter()
            .map(|r| format!("{:?} {}", r.kind, r.handle)),
    );
    sections.push(Section {
        kind: SectionKind::Links,
        heading: "Links".into(),
        markdown: links,
    });
    sections.push(Section {
        kind: SectionKind::ManagedNotice,
        heading: "Managed by frob".into(),
        markdown: "This issue is generated from the frob ledger; edit the ticket, not this issue."
            .into(),
    });
    let (c, people, state) = redact(facts, &mut keep);

    let mut p = IssueProjection {
        identity: facts.identity.clone(),
        title: facts.title.clone(),
        sections,
        classification: c,
        state,
        relations,
        people,
        provenance: Provenance {
            last_event: facts.last_event.clone(),
            render_digest: String::new(),
            producer_version: producer_version.to_owned(),
        },
        private: private.into_iter().collect(),
    };
    p.provenance.render_digest = digest(&p);
    debug!(ulid = %p.identity.ulid, digest = %p.provenance.render_digest, "projection built");
    p
}

/// Blake3 hex digest of the projection serialized with its own digest blanked.
pub fn digest(p: &IssueProjection) -> String {
    let mut q = p.clone();
    q.provenance.render_digest.clear();
    // Serializing plain derived structs cannot fail.
    let bytes = serde_json::to_vec(&q).unwrap_or_default();
    blake3::hash(&bytes).to_hex().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn facts() -> TicketFacts {
        TicketFacts {
            identity: Identity {
                ulid: "01M3ZX832JK52FXBPPCCGTDRTG".into(),
                handle: "~CGTDRTG".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/x".into(),
            },
            title: "T".into(),
            summary: "body".into(),
            acceptance: vec![Criterion {
                text: "Given a, when b, then c".into(),
                bound: false,
            }],
            scope: vec!["crates/x/**".into()],
            evidence: vec![EvidenceItem {
                reference: "t::a".into(),
                verdict: "pass".into(),
            }],
            classification: Classification {
                priority: Some("high".into()),
                points: Some(5),
                ..Default::default()
            },
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![
                Relation {
                    kind: RelationKind::Relates,
                    ulid: "B".into(),
                    handle: "~B".into(),
                },
                Relation {
                    kind: RelationKind::BlockedBy,
                    ulid: "A".into(),
                    handle: "~A".into(),
                },
            ],
            people: People {
                owner: Some("lognd".into()),
                assignee: None,
            },
            last_event: "EV1".into(),
        }
    }

    // frob:tests project
    #[test]
    fn sections_relations_typed_and_digest_stable() {
        let none = BTreeSet::new();
        let a = project(&facts(), &none, "1");
        let b = project(&facts(), &none, "1");
        assert_eq!(a, b);
        assert_eq!(a.provenance.render_digest, b.provenance.render_digest);
        assert_eq!(a.provenance.render_digest, digest(&a));
        let kinds: Vec<_> = a.sections.iter().map(|s| s.kind).collect();
        assert_eq!(
            kinds,
            [
                SectionKind::Summary,
                SectionKind::Acceptance,
                SectionKind::Scope,
                SectionKind::Evidence,
                SectionKind::Links,
                SectionKind::ManagedNotice
            ]
        );
        assert_eq!(a.relations[0].kind, RelationKind::BlockedBy);
        assert!(a.private.is_empty());
    }

    // frob:tests project
    #[test]
    fn excluded_field_is_absent_and_recorded_private() {
        let ex: BTreeSet<String> = ["points".to_owned(), "scope".to_owned()].into();
        let a = project(&facts(), &ex, "1");
        assert_eq!(a.classification.points, None);
        assert!(a.sections.iter().all(|s| s.kind != SectionKind::Scope));
        assert_eq!(a.private, ["points", "scope"]);
        let full = project(&facts(), &BTreeSet::new(), "1");
        assert_ne!(a.provenance.render_digest, full.provenance.render_digest);
    }
}
