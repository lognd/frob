//! `mirror recreate`: a person-run replacement of an issue the tracker deleted (mirror.md 3.3).
//!
//! The mirror never recreates an issue by itself. A person runs recreate for a ticket whose issue
//! returned 410; the old identity is dropped from the shard and a new issue is made through the
//! create protocol, after which the ticket is mirrored again. A 404 is refused: the token may
//! simply be unable to see the issue, so it is not known to be deleted. This module is the
//! transport-free core; the verb wiring supplies the store, adapter and projection.

// frob:ticket 01M4052V7BG4YBHSW863YZEJ9X

use std::fmt;

use frob_mirror::adapter::{AdapterError, IssueRef, TrackerAdapter};
use frob_mirror::blind::{Disposition, classify};
use frob_mirror::create::{CreateError, CreateStep, create_issue};
use frob_mirror::cursor::PendingCursor;
use frob_mirror::mapfile::{MapError, ShardStore, read_shard, write_shard};
use frob_mirror::projection::IssueProjection;
use tracing::{info, warn};

/// Why a recreate did not run to a create.
#[derive(Debug, PartialEq, Eq)]
pub enum RecreateRefusal {
    /// No shard, or the shard names no issue: there is nothing to recreate.
    NotMirrored,
    /// The issue still reads fine: it is not deleted.
    StillExists(String),
    /// The issue returned 404: it may be invisible to the token, not deleted.
    MayBeInvisible(String),
    /// The issue moved (301); the location must be verified, not recreated.
    Moved(String),
}

impl fmt::Display for RecreateRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotMirrored => write!(f, "ticket has no mirrored issue to recreate"),
            Self::StillExists(i) => write!(f, "issue {i} still exists; nothing to recreate"),
            Self::MayBeInvisible(i) => write!(
                f,
                "issue {i} returned 404: it may be invisible to this token, not deleted; \
                 recreate only follows a 410"
            ),
            Self::Moved(to) => write!(f, "issue moved to {to}; verify the move, do not recreate"),
        }
    }
}

/// Failures of a recreate that are not refusals.
#[derive(Debug, PartialEq, Eq)]
pub enum RecreateError {
    /// Refused before any change.
    Refused(RecreateRefusal),
    /// The probe of the old issue failed without a status meaning.
    Probe(AdapterError),
    /// The shard could not be read or committed.
    Map(MapError),
    /// The create protocol failed.
    Create(CreateError),
}

impl fmt::Display for RecreateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Refused(r) => write!(f, "{r}"),
            Self::Probe(e) => write!(f, "probing the old issue failed: {e}"),
            Self::Map(e) => write!(f, "map store: {e}"),
            Self::Create(e) => write!(f, "create: {e}"),
        }
    }
}

/// Recreate the issue of ticket `ulid` after a 410, through the create protocol.
///
/// The old issue is probed first: only a 410 (`Disposition::Unmirrored`) proceeds. The shard's
/// tracker identity and cursors are dropped, then `create_issue` runs; on a confirmed create the
/// returned step's shard names the new issue.
///
/// # Errors
/// `RecreateError::Refused` unless the old issue is gone (410); other variants for store, probe
/// and create failures.
pub fn recreate<S: ShardStore, A: TrackerAdapter>(
    store: &mut S,
    adapter: &mut A,
    ulid: &str,
    projection: &IssueProjection,
    run_id: &str,
    started: &str,
    pending: PendingCursor,
) -> Result<CreateStep, RecreateError> {
    let mut shard = read_shard(store, ulid)
        .map_err(RecreateError::Map)?
        .ok_or(RecreateError::Refused(RecreateRefusal::NotMirrored))?;
    let Some(number) = shard.issue_number else {
        warn!(ulid, "recreate: refused, shard names no issue");
        return Err(RecreateError::Refused(RecreateRefusal::NotMirrored));
    };
    let old = IssueRef(number.to_string());
    match adapter.read(&old) {
        Ok(_) => {
            warn!(ulid, issue = %old.0, "recreate: refused, issue still exists");
            return Err(RecreateError::Refused(RecreateRefusal::StillExists(old.0)));
        }
        Err(e) => match classify(&e) {
            Some(Disposition::Unmirrored) => {}
            Some(Disposition::NotVisible) => {
                warn!(ulid, issue = %old.0, "recreate: refused, 404 may be invisible");
                return Err(RecreateError::Refused(RecreateRefusal::MayBeInvisible(
                    old.0,
                )));
            }
            Some(Disposition::Moved(to)) => {
                warn!(ulid, issue = %old.0, %to, "recreate: refused, issue moved");
                return Err(RecreateError::Refused(RecreateRefusal::Moved(to)));
            }
            None => return Err(RecreateError::Probe(e)),
        },
    }
    info!(ulid, issue = %old.0, "recreate: issue gone (410), dropping old identity");
    shard.issue_number = None;
    shard.node_id = None;
    shard.location = None;
    shard.history_cursor = None;
    shard.observed.clear();
    write_shard(store, &shard).map_err(RecreateError::Map)?;
    let step = create_issue(store, adapter, shard, projection, run_id, started, pending)
        .map_err(RecreateError::Create)?;
    info!(ulid, "recreate: create protocol finished");
    Ok(step)
}

#[cfg(test)]
mod tests {
    use std::collections::{BTreeSet, HashMap};

    use frob_mirror::adapter::{
        AdapterResult, Capabilities, CreateOutcome, EventId, HistoryEntry, HistoryRetention,
        Inventory, IssueState, IssueSummary, MarkdownDialect, StateReasons,
    };
    use frob_mirror::cursor::begin_read;
    use frob_mirror::github::read::{BodyRevisions, HistorySource, TimelineEvent};
    use frob_mirror::mapfile::{Shard, content_hash};
    use frob_mirror::projection::{
        Category, Classification, Identity, People, RelationKind, State, TicketFacts, project,
    };

    use super::*;

    #[derive(Default)]
    struct Mem(HashMap<String, Vec<u8>>);

    impl ShardStore for Mem {
        fn get(&self, key: &str) -> Option<Vec<u8>> {
            self.0.get(key).cloned()
        }
        fn put_if(
            &mut self,
            key: &str,
            expected: Option<&str>,
            bytes: Vec<u8>,
        ) -> Result<(), MapError> {
            let found = self.get(key).map(|b| content_hash(&b));
            if found.as_deref() != expected {
                return Err(MapError::Conflict {
                    key: key.into(),
                    expected: expected.map(String::from),
                    found,
                });
            }
            self.0.insert(key.into(), bytes);
            Ok(())
        }
    }

    /// Reads of the old issue fail with `read_err`; creates yield issue 99.
    struct Fake {
        read_err: Option<AdapterError>,
        creates: usize,
    }

    impl TrackerAdapter for Fake {
        fn capabilities(&self) -> Capabilities {
            Capabilities {
                native_sub_issues: false,
                native_links: false,
                custom_fields: false,
                state_reasons: StateReasons::Unsupported,
                history_retention: HistoryRetention::None,
                markdown: MarkdownDialect::Github,
            }
        }
        fn create(&mut self, _: &IssueProjection, _: &str) -> CreateOutcome {
            self.creates += 1;
            CreateOutcome::Created(IssueRef("99".into()))
        }
        fn update(&mut self, _: &IssueRef, _: &IssueProjection) -> AdapterResult<()> {
            Ok(())
        }
        fn close(
            &mut self,
            _: &IssueRef,
            _: frob_mirror::projection::Outcome,
        ) -> AdapterResult<()> {
            Ok(())
        }
        fn list_by_creator(&self, _: u64) -> AdapterResult<Vec<IssueSummary>> {
            Ok(vec![])
        }
        fn read(&self, i: &IssueRef) -> AdapterResult<IssueState> {
            match &self.read_err {
                Some(e) => Err(e.clone()),
                None => Ok(IssueState {
                    issue: i.clone(),
                    title: String::new(),
                    body: String::new(),
                    labels: vec![],
                    assignees: vec![],
                    closed: false,
                }),
            }
        }
        fn history_after(
            &self,
            _: &IssueRef,
            _: Option<&EventId>,
        ) -> AdapterResult<Vec<HistoryEntry>> {
            Ok(vec![])
        }
        fn add_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
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

    struct NoHistory;

    impl HistorySource for NoHistory {
        fn issue(&self, i: &IssueRef) -> AdapterResult<IssueState> {
            Ok(IssueState {
                issue: i.clone(),
                title: String::new(),
                body: String::new(),
                labels: vec![],
                assignees: vec![],
                closed: false,
            })
        }
        fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
            Ok(vec![])
        }
        fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
            Ok(BodyRevisions::default())
        }
    }

    fn projection() -> IssueProjection {
        let facts = TicketFacts {
            identity: Identity {
                ulid: "U1".into(),
                handle: "~U1".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/U1.md".into(),
            },
            title: "t".into(),
            summary: "s".into(),
            acceptance: vec![],
            scope: vec![],
            evidence: vec![],
            classification: Classification::default(),
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![],
            people: People::default(),
            last_event: "E".into(),
        };
        project(&facts, &BTreeSet::new(), "test")
    }

    fn store_with_issue(n: u64) -> Mem {
        let mut s = Mem::default();
        let mut shard = Shard::new("U1");
        shard.issue_number = Some(n);
        shard.history_cursor = Some("E1".into());
        write_shard(&mut s, &shard).unwrap();
        s
    }

    fn run(store: &mut Mem, adapter: &mut Fake) -> Result<CreateStep, RecreateError> {
        let shard = read_shard(store, "U1").unwrap().unwrap();
        let pending = begin_read(&NoHistory, &IssueRef("1".into()), &shard)
            .unwrap()
            .pending;
        recreate(
            store,
            adapter,
            "U1",
            &projection(),
            "run1",
            "2026-01-01T00:00:00Z",
            pending,
        )
    }

    #[test]
    fn a_410_issue_is_recreated_and_the_shard_points_at_the_new_one() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::recreate
        let mut store = store_with_issue(7);
        let mut adapter = Fake {
            read_err: Some(AdapterError::Gone),
            creates: 0,
        };
        let step = run(&mut store, &mut adapter).unwrap();
        assert!(matches!(step, CreateStep::Created(_)));
        assert_eq!(adapter.creates, 1);
        let shard = read_shard(&store, "U1").unwrap().unwrap();
        assert_eq!(shard.issue_number, Some(99));
        assert!(shard.create_uncertain.is_none());
        assert_eq!(shard.history_cursor, None);
    }

    #[test]
    fn a_404_issue_is_refused_as_possibly_invisible() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::recreate
        let mut store = store_with_issue(7);
        let mut adapter = Fake {
            read_err: Some(AdapterError::NotFound),
            creates: 0,
        };
        let err = run(&mut store, &mut adapter).unwrap_err();
        assert_eq!(
            err,
            RecreateError::Refused(RecreateRefusal::MayBeInvisible("7".into()))
        );
        assert!(err.to_string().contains("invisible"));
        assert!(err.to_string().contains("not deleted"));
        assert_eq!(adapter.creates, 0);
        let shard = read_shard(&store, "U1").unwrap().unwrap();
        assert_eq!(shard.issue_number, Some(7));
    }

    #[test]
    fn a_live_issue_is_refused() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::recreate
        let mut store = store_with_issue(7);
        let mut adapter = Fake {
            read_err: None,
            creates: 0,
        };
        let err = run(&mut store, &mut adapter).unwrap_err();
        assert!(matches!(
            err,
            RecreateError::Refused(RecreateRefusal::StillExists(_))
        ));
        assert_eq!(adapter.creates, 0);
    }
}
