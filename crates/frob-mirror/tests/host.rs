//! The concrete run host driven through `run::run` against the fake GitHub.

// frob:ticket 01M5EA0YFAACDY5BV70R2MH98S
#![allow(dead_code)]

#[path = "support/fake_github.rs"]
mod fake_github;

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::time::Duration;

use fake_github::{BOT_ID, FakeGithub};
use frob_mirror::adapter::{AdapterError, AdapterResult, IssueRef, IssueState};
use frob_mirror::budget::{BudgetConfig, RateLimit};
use frob_mirror::feed::{FeedPage, FeedSource};
use frob_mirror::fields::{FieldOwnership, FieldsConfig};
use frob_mirror::github::lookup::ListingSource;
use frob_mirror::github::read::{BodyRevisions, HistorySource, TimelineEvent};
use frob_mirror::host::{HostConfig, MirrorHost, Shared, Sources, TicketSource, TicketState};
use frob_mirror::keyring::Keyring;
use frob_mirror::lock::{LedgerCommit, read_watermark};
use frob_mirror::mapfile::{MapError, ShardStore, content_hash, read_shard};
use frob_mirror::outbox::{FieldSink, LedgerEvent, Mode, SinkError};
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, People, State, TicketFacts, project,
};
use frob_mirror::run::{RunConfig, RunOutcome, run};
use gob_trust::MachineKey;

#[derive(Default)]
struct Mem(HashMap<String, Vec<u8>>);

impl ShardStore for Mem {
    fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.0.get(key).cloned()
    }
    fn put_if(&mut self, key: &str, exp: Option<&str>, bytes: Vec<u8>) -> Result<(), MapError> {
        let found = self.get(key).map(|b| content_hash(&b));
        if found.as_deref() != exp {
            return Err(MapError::Conflict {
                key: key.into(),
                expected: exp.map(String::from),
                found,
            });
        }
        self.0.insert(key.into(), bytes);
        Ok(())
    }
}

fn projection(ulid: &str) -> IssueProjection {
    let facts = TicketFacts {
        identity: Identity {
            ulid: ulid.into(),
            handle: format!("~{ulid}"),
            aliases: vec![],
            repository: "https://example.invalid/r".into(),
            ledger_path: format!("tickets/{ulid}.md"),
        },
        title: format!("title {ulid}"),
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
        last_event: "01EV".into(),
    };
    project(&facts, &BTreeSet::new(), "test")
}

struct Quiet;

impl FeedSource for Quiet {
    fn page(&self, _: &str, _: Option<&str>) -> AdapterResult<FeedPage> {
        Ok(FeedPage {
            issues: vec![],
            next: None,
        })
    }
}

impl ListingSource for Quiet {
    fn page(&self, _: u64, _: u32) -> AdapterResult<Vec<frob_mirror::adapter::IssueSummary>> {
        Ok(vec![])
    }
}

impl HistorySource for Quiet {
    fn issue(&self, _: &IssueRef) -> AdapterResult<IssueState> {
        Err(AdapterError::NotFound)
    }
    fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
        Ok(vec![])
    }
    fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
        Ok(BodyRevisions::default())
    }
}

struct Tickets {
    events: Vec<LedgerEvent>,
    commits: Vec<LedgerCommit>,
}

impl TicketSource for Tickets {
    fn mirrored(&self) -> Vec<String> {
        vec!["U1".into()]
    }
    fn creatable(&self) -> Vec<(String, u64)> {
        vec![("U1".into(), 1)]
    }
    fn projection(&self, ulid: &str) -> Option<IssueProjection> {
        Some(projection(ulid))
    }
    fn events(&self) -> Vec<LedgerEvent> {
        self.events.clone()
    }
    fn state(&self, _: &str) -> Option<TicketState> {
        None
    }
    fn current(&self, _: &IssueState) -> BTreeMap<String, String> {
        BTreeMap::new()
    }
    fn commit_proposals(
        &mut self,
        _: &str,
        _: Vec<frob_ledger::event::Event>,
    ) -> Result<(), String> {
        Ok(())
    }
    fn commits(&self) -> Vec<LedgerCommit> {
        self.commits.clone()
    }
}

struct Sink(Shared<Vec<(u64, String, String)>>);

impl FieldSink for Sink {
    fn set_field(&mut self, n: u64, f: &str, v: &str) -> Result<String, SinkError> {
        self.0.with(|c| c.push((n, f.into(), v.into())));
        Ok(v.into())
    }
}

fn host_cfg() -> HostConfig {
    HostConfig {
        run_id: "r1".into(),
        now: 0,
        started: "2026-01-01T00:00:00Z".into(),
        bot_ids: vec![BOT_ID],
        repo_node_id: "R_1".into(),
        rate_limit: RateLimit {
            remaining: Some(1000),
            reset: Some(10_000),
        },
        mode: Mode::Incremental,
        max_ops: 10,
        proposals_per_run: 5,
        actor: "mirror".into(),
    }
}

fn run_cfg() -> RunConfig {
    RunConfig {
        run_id: "r1".into(),
        now: 100,
        lock_ttl_secs: 3600,
        commit_every: 2,
        sweep_k: 1,
        bot_id: BOT_ID,
        budget: BudgetConfig {
            spacing: Duration::ZERO,
            ..BudgetConfig::default()
        },
    }
}

struct World {
    store: Shared<Mem>,
    gh: Shared<FakeGithub>,
    calls: Shared<Vec<(u64, String, String)>>,
}

impl World {
    fn new() -> Self {
        Self {
            store: Shared::new(Mem::default()),
            gh: Shared::new(FakeGithub::new(1)),
            calls: Shared::new(Vec::new()),
        }
    }

    /// One mirror pass with the given ledger events.
    fn pass(&self, events: Vec<LedgerEvent>) {
        self.pass_with(events, vec![]);
    }

    /// One mirror pass with the given ledger events and commit log.
    fn pass_with(&self, events: Vec<LedgerEvent>, commits: Vec<LedgerCommit>) {
        let q = Quiet;
        let ring = Keyring::new("k1", MachineKey::from_bytes([1; 32]), vec![]).unwrap();
        let own = FieldOwnership::load(
            &FieldsConfig {
                owners: BTreeMap::new(),
                tracker_owned: vec![],
            },
            &[],
        )
        .unwrap();
        let src = Sources {
            feed: &q,
            listing: &q,
            history: &q,
            ring: &ring,
            ownership: &own,
        };
        let mut host = MirrorHost::new(
            self.store.clone(),
            self.gh.clone(),
            Tickets { events, commits },
            Sink(self.calls.clone()),
            src,
            host_cfg(),
        );
        let (mut store, gh) = (self.store.clone(), self.gh.clone());
        let out = run(&mut store, &gh, &mut host, &run_cfg()).unwrap();
        assert!(matches!(out, RunOutcome::Ran(_)), "{out:?}");
    }

    fn issue_of(&self, ulid: &str) -> Option<u64> {
        read_shard(&self.store, ulid)
            .unwrap()
            .and_then(|s| s.issue_number)
    }
}

fn ev(id: &str, field: &str, value: &str) -> LedgerEvent {
    LedgerEvent {
        ticket: "U1".into(),
        event: id.into(),
        field: field.into(),
        value: value.into(),
    }
}

// frob:tests MirrorHost.pending
// frob:tests MirrorHost.execute
// frob:tests create_issue
#[test]
fn a_new_ticket_gets_one_issue_and_a_second_pass_creates_no_more() {
    let w = World::new();
    w.pass(vec![]);
    let n = w.issue_of("U1").expect("issue number stored");
    w.pass(vec![]);
    assert_eq!(w.issue_of("U1"), Some(n));
    assert_eq!(w.gh.with(|g| g.snapshot().issues.len()), 1);
}

// frob:tests apply_op
// frob:tests MirrorHost.execute
#[test]
fn ledger_events_reach_the_tracker_once() {
    let w = World::new();
    w.pass(vec![]);
    let n = w.issue_of("U1").unwrap();
    w.pass(vec![ev("E1", "title", "new")]);
    assert_eq!(
        w.calls.with(|c| c.clone()),
        vec![(n, "title".to_owned(), "new".to_owned())]
    );
    w.pass(vec![ev("E1", "title", "new")]);
    assert_eq!(
        w.calls.with(|c| c.len()),
        1,
        "a converged ticket is not written again"
    );
}

// frob:tests MirrorHost.ledger_commits
#[test]
fn a_clean_pass_advances_the_watermark_to_the_ledger_head() {
    let w = World::new();
    let log = |ids: &[&str]| {
        ids.iter()
            .map(|id| LedgerCommit {
                id: (*id).into(),
                own: false,
            })
            .collect::<Vec<_>>()
    };
    w.pass_with(vec![], log(&["c1", "c2"]));
    let mark = read_watermark(&w.store).unwrap();
    assert_eq!(mark.map(|m| m.commit), Some("c2".to_owned()));
    w.pass_with(vec![], log(&["c1", "c2", "c3"]));
    let mark = read_watermark(&w.store).unwrap();
    assert_eq!(mark.map(|m| m.commit), Some("c3".to_owned()));
}

// frob:tests MirrorHost.close_duplicates
#[test]
fn close_duplicates_with_one_issue_closes_nothing() {
    let w = World::new();
    w.pass(vec![]);
    let q = Quiet;
    let ring = Keyring::new("k1", MachineKey::from_bytes([1; 32]), vec![]).unwrap();
    let own = FieldOwnership::load(
        &FieldsConfig {
            owners: BTreeMap::new(),
            tracker_owned: vec![],
        },
        &[],
    )
    .unwrap();
    let src = Sources {
        feed: &q,
        listing: &q,
        history: &q,
        ring: &ring,
        ownership: &own,
    };
    let host = MirrorHost::new(
        w.store.clone(),
        w.gh.clone(),
        Tickets {
            events: vec![],
            commits: vec![],
        },
        Sink(w.calls.clone()),
        src,
        host_cfg(),
    );
    let report = host.close_duplicates().unwrap();
    assert!(report.closed.is_empty());
}
