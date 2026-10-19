//! The tracker adapter trait and capabilities record (mirror.md 2.1, 3.2 to 3.4).
//!
//! One adapter per tracker translates an `IssueProjection` into tracker operations. Edits are
//! additive (labels and assignees are added or removed one by one, never replaced wholesale) and
//! every read the identity protocol needs (listing by creator, history after an event id) is
//! part of the trait, so a fake adapter can replay recorded API fixtures offline.

// frob:ticket 01M3ZX83AB2JADBKWFA9SY4J60

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, trace};

use crate::projection::{IssueProjection, Outcome, Relation, RelationKind};

/// How long a tracker keeps issue history.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HistoryRetention {
    /// History is kept for the life of the issue.
    Forever,
    /// History is kept for this many days.
    Days(u32),
    /// The tracker exposes no history.
    None,
}

/// The markup dialect a tracker renders.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MarkdownDialect {
    /// GitHub flavoured markdown.
    Github,
    /// GitLab flavoured markdown.
    Gitlab,
    /// Jira wiki markup.
    JiraWiki,
    /// Plain text only.
    Plain,
}

/// Whether closing an issue carries a reason (completed, not planned, duplicate).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StateReasons {
    /// Close reasons are recorded natively.
    Native,
    /// Close reasons are not available.
    Unsupported,
}

/// What a tracker can hold natively; the mapping is checked against it at load.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Capabilities {
    /// Parent and child edges exist natively.
    pub native_sub_issues: bool,
    /// Blocked-by, blocks and relates edges exist natively.
    pub native_links: bool,
    /// Typed custom fields exist.
    pub custom_fields: bool,
    /// Whether closing carries a reason.
    pub state_reasons: StateReasons,
    /// How long history stays readable.
    pub history_retention: HistoryRetention,
    /// The markup the tracker renders.
    pub markdown: MarkdownDialect,
}

/// A tracker-side issue number or key.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct IssueRef(pub String);

/// A tracker event id; history is read strictly after one.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct EventId(pub String);

/// Outcome of a create; `Unknown` makes the ticket create-uncertain (mirror.md 3.3).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreateOutcome {
    /// The tracker confirmed the issue.
    Created(IssueRef),
    /// The tracker definitely rejected the create.
    Failed(String),
    /// Timeout, 5xx or crash: the issue may or may not exist.
    Unknown,
}

/// The tracker's view of one issue.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IssueState {
    /// The issue reference.
    pub issue: IssueRef,
    /// Title as shown.
    pub title: String,
    /// Body as shown.
    pub body: String,
    /// Labels present.
    pub labels: Vec<String>,
    /// Assignees present (tracker user logins).
    pub assignees: Vec<String>,
    /// Whether the issue is closed.
    pub closed: bool,
}

/// An issue in a creator listing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IssueSummary {
    /// The issue reference.
    pub issue: IssueRef,
    /// Title as shown.
    pub title: String,
    /// Creator user id.
    pub creator_id: u64,
    /// Creation time, RFC 3339.
    pub created_at: String,
}

/// One history entry (mirror.md 3.3 "Own writes").
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoryEntry {
    /// The event id.
    pub event: EventId,
    /// Actor user id.
    pub actor_id: u64,
    /// The field changed.
    pub field: String,
    /// Digest of the new value.
    pub value_digest: String,
}

/// The tracker's managed vocabulary, read by schema and inventory validation.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Inventory {
    /// Managed labels that exist.
    pub labels: Vec<String>,
    /// Milestones that exist.
    pub milestones: Vec<String>,
    /// Issue types that exist.
    pub issue_types: Vec<String>,
}

/// Failures an adapter reports.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum AdapterError {
    /// The tracker moved the issue (301); the new location is carried.
    #[error("issue moved to {0}")]
    Moved(String),
    /// The tracker answered not found; never read as "deleted" (token blindness).
    #[error("not found")]
    NotFound,
    /// The tracker reports the issue deleted (410).
    #[error("issue gone")]
    Gone,
    /// The tracker throttled the call.
    #[error("rate limited")]
    RateLimited,
    /// Any other tracker or transport failure.
    #[error("tracker error: {0}")]
    Other(String),
}

/// Result alias for adapter calls.
pub type AdapterResult<T> = Result<T, AdapterError>;

/// One tracker. Writes are additive; implementations journal before mutating.
pub trait TrackerAdapter {
    /// Declare what this tracker holds natively.
    fn capabilities(&self) -> Capabilities;
    /// Create an issue for `projection`, carrying `nonce` in the creation revision.
    fn create(&mut self, projection: &IssueProjection, nonce: &str) -> CreateOutcome;
    /// Update title and body from `projection`.
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn update(&mut self, issue: &IssueRef, projection: &IssueProjection) -> AdapterResult<()>;
    /// Close with an outcome-derived reason.
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn close(&mut self, issue: &IssueRef, reason: Outcome) -> AdapterResult<()>;
    /// List the bot's issues by creator, newest first (read-your-writes, never search).
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn list_by_creator(&self, creator_id: u64) -> AdapterResult<Vec<IssueSummary>>;
    /// Read one issue.
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn read(&self, issue: &IssueRef) -> AdapterResult<IssueState>;
    /// Read history entries strictly after `after` (all when `None`).
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn history_after(
        &self,
        issue: &IssueRef,
        after: Option<&EventId>,
    ) -> AdapterResult<Vec<HistoryEntry>>;
    /// Add labels (never replaces the set).
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn add_labels(&mut self, issue: &IssueRef, labels: &[String]) -> AdapterResult<()>;
    /// Remove labels (never replaces the set).
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn remove_labels(&mut self, issue: &IssueRef, labels: &[String]) -> AdapterResult<()>;
    /// Add assignees (never replaces the set).
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn add_assignees(&mut self, issue: &IssueRef, who: &[String]) -> AdapterResult<()>;
    /// Remove assignees (never replaces the set).
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn remove_assignees(&mut self, issue: &IssueRef, who: &[String]) -> AdapterResult<()>;
    /// Create a native link of `kind` from `issue` to `target`.
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn link(
        &mut self,
        issue: &IssueRef,
        kind: RelationKind,
        target: &IssueRef,
    ) -> AdapterResult<()>;
    /// Read the tracker's schema and managed-vocabulary inventory.
    ///
    /// # Errors
    /// Returns an [`AdapterError`] when the tracker call fails.
    fn inventory(&self) -> AdapterResult<Inventory>;
}

/// Where each relation of a projection goes.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RelationRouting {
    /// Relations created as native tracker edges.
    pub native: Vec<Relation>,
    /// Relations rendered as body links because the tracker lacks a native form.
    pub body_links: Vec<Relation>,
}

/// Route relations by `caps`: parent and child need native sub-issues, the rest native links.
pub fn route_relations(caps: &Capabilities, relations: &[Relation]) -> RelationRouting {
    let mut out = RelationRouting::default();
    for r in relations {
        let native = match r.kind {
            RelationKind::Parent | RelationKind::Child => caps.native_sub_issues,
            _ => caps.native_links,
        };
        trace!(kind = ?r.kind, handle = %r.handle, native, "relation routed");
        if native {
            out.native.push(r.clone());
        } else {
            out.body_links.push(r.clone());
        }
    }
    debug!(
        native = out.native.len(),
        body = out.body_links.len(),
        "relations routed"
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::projection::{
        Category, Classification, Identity, People, State, TicketFacts, project,
    };
    use std::collections::BTreeSet;

    /// Offline adapter that records the operations it was asked to perform.
    struct Fake {
        caps: Capabilities,
        ops: Vec<String>,
    }

    impl TrackerAdapter for Fake {
        fn capabilities(&self) -> Capabilities {
            self.caps
        }
        fn create(&mut self, p: &IssueProjection, nonce: &str) -> CreateOutcome {
            self.ops.push(format!("create {} {nonce}", p.identity.ulid));
            CreateOutcome::Created(IssueRef("1".into()))
        }
        fn update(&mut self, i: &IssueRef, _: &IssueProjection) -> AdapterResult<()> {
            self.ops.push(format!("update {}", i.0));
            Ok(())
        }
        fn close(&mut self, i: &IssueRef, _: Outcome) -> AdapterResult<()> {
            self.ops.push(format!("close {}", i.0));
            Ok(())
        }
        fn list_by_creator(&self, _: u64) -> AdapterResult<Vec<IssueSummary>> {
            Ok(vec![])
        }
        fn read(&self, _: &IssueRef) -> AdapterResult<IssueState> {
            Err(AdapterError::NotFound)
        }
        fn history_after(
            &self,
            _: &IssueRef,
            _: Option<&EventId>,
        ) -> AdapterResult<Vec<HistoryEntry>> {
            Ok(vec![])
        }
        fn add_labels(&mut self, i: &IssueRef, l: &[String]) -> AdapterResult<()> {
            self.ops.push(format!("add_labels {} {}", i.0, l.join(",")));
            Ok(())
        }
        fn remove_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn add_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn remove_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn link(&mut self, _: &IssueRef, _: RelationKind, _: &IssueRef) -> AdapterResult<()> {
            Ok(())
        }
        fn inventory(&self) -> AdapterResult<Inventory> {
            Ok(Inventory::default())
        }
    }

    fn caps(sub: bool, links: bool) -> Capabilities {
        Capabilities {
            native_sub_issues: sub,
            native_links: links,
            custom_fields: false,
            state_reasons: StateReasons::Native,
            history_retention: HistoryRetention::Forever,
            markdown: MarkdownDialect::Github,
        }
    }

    fn rel(kind: RelationKind, h: &str) -> Relation {
        Relation {
            kind,
            ulid: format!("U{h}"),
            handle: h.into(),
        }
    }

    fn recorded_projection() -> IssueProjection {
        let facts = TicketFacts {
            identity: Identity {
                ulid: "01ABC".into(),
                handle: "~ABC".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/01ABC.md".into(),
            },
            title: "t".into(),
            summary: "s".into(),
            acceptance: vec![],
            scope: vec![],
            evidence: vec![],
            classification: Classification {
                labels: Some(vec!["area:mirror".into()]),
                ..Classification::default()
            },
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![rel(RelationKind::Parent, "~P")],
            people: People::default(),
            last_event: "01EV".into(),
        };
        project(&facts, &BTreeSet::new(), "test")
    }

    // frob:tests capabilities
    // frob:tests create
    // frob:tests update
    // frob:tests close
    #[test]
    fn fake_adapter_produces_operations_offline() {
        let p = recorded_projection();
        let mut a = Fake {
            caps: caps(false, false),
            ops: vec![],
        };
        let CreateOutcome::Created(i) = a.create(&p, "n1") else {
            panic!("create")
        };
        a.add_labels(&i, p.classification.labels.as_deref().unwrap())
            .unwrap();
        a.update(&i, &p).unwrap();
        a.close(&i, Outcome::Done).unwrap();
        assert_eq!(a.capabilities().markdown, MarkdownDialect::Github);
        assert_eq!(
            a.ops,
            [
                "create 01ABC n1",
                "add_labels 1 area:mirror",
                "update 1",
                "close 1"
            ]
        );
    }

    // frob:tests route_relations
    #[test]
    fn no_native_sub_issues_falls_back_to_body_links() {
        let p = recorded_projection();
        let a = Fake {
            caps: caps(false, true),
            ops: vec![],
        };
        let r = route_relations(&a.capabilities(), &p.relations);
        assert!(r.native.is_empty());
        assert_eq!(r.body_links, p.relations);
        assert!(!a.capabilities().native_sub_issues);
    }

    // frob:tests list_by_creator
    // frob:tests history_after
    // frob:tests add_labels
    // frob:tests remove_labels
    // frob:tests add_assignees
    // frob:tests remove_assignees
    // frob:tests link
    // frob:tests inventory
    #[test]
    fn read_and_additive_edit_calls_succeed_offline() {
        let mut a = Fake {
            caps: caps(true, true),
            ops: vec![],
        };
        let i = IssueRef("1".into());
        assert!(a.list_by_creator(7).unwrap().is_empty());
        assert!(a.history_after(&i, None).unwrap().is_empty());
        a.add_labels(&i, &[]).unwrap();
        a.remove_labels(&i, &[]).unwrap();
        a.add_assignees(&i, &[]).unwrap();
        a.remove_assignees(&i, &[]).unwrap();
        a.link(&i, RelationKind::Relates, &i).unwrap();
        assert_eq!(a.inventory().unwrap(), Inventory::default());
    }

    // frob:tests route_relations
    #[test]
    fn native_kinds_route_by_capability() {
        let rels = [
            rel(RelationKind::Parent, "~P"),
            rel(RelationKind::BlockedBy, "~B"),
        ];
        let r = route_relations(&caps(true, false), &rels);
        assert_eq!(r.native, [rels[0].clone()]);
        assert_eq!(r.body_links, [rels[1].clone()]);
    }
}
