//! Property tests for duplicate issues (mirror.md 3.7 duplicate row; model rows D0, F4, F5, F6).
//!
//! Seeded loops over the fake GitHub: lost and crashed creates never make two issues for one
//! ticket (S3), a late create after the retry makes at most one extra issue per uncertain create
//! and the next run closes it and still reads its history (L4), and a human editing the marker in
//! a later body revision never makes the mirror create a second issue (F4).

// frob:ticket 01M4052WS0WETQ6V4FZ9XENZPA
#![allow(dead_code)]

#[path = "support/fake_github.rs"]
mod fake_github;

use std::collections::{BTreeMap, BTreeSet, HashMap};

use fake_github::{BOT_ID, CrashPoint, FakeGithub, HUMAN_ID, Rng};
use frob_mirror::adapter::{AdapterResult, IssueRef, IssueState, IssueSummary, TrackerAdapter};
use frob_mirror::create::{CreateStep, Recovery, RecoveryEnv, create_issue, derive_nonce, recover};
use frob_mirror::cursor::{PendingCursor, begin_read};
use frob_mirror::dups::{
    claims_from_verdicts, close_duplicates, plan_duplicates, read_duplicate_history,
};
use frob_mirror::github::lookup::ListingSource;
use frob_mirror::github::read::{
    BodyRevision, BodyRevisions, HistorySource, TimelineEvent, creation_revision,
};
use frob_mirror::journal::value_digest;
use frob_mirror::keyring::{Keyring, MarkerFields};
use frob_mirror::mapfile::{MapError, Shard, ShardStore, content_hash};
use frob_mirror::marker::{evaluate, format_marker};
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, People, State, TicketFacts, project,
};
use gob_trust::MachineKey;

const START: &str = "2026-01-01T00:00:00Z";
const REPO: &str = "R_1";
const ULID: &str = "U1";
const SEEDS: u64 = 120;

/// In-memory shard store with compare-and-swap semantics.
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

/// The projection of the single ticket under test.
fn projection() -> IssueProjection {
    let facts = TicketFacts {
        identity: Identity {
            ulid: ULID.into(),
            handle: format!("~{ULID}"),
            aliases: vec![],
            repository: "https://example.invalid/r".into(),
            ledger_path: format!("tickets/{ULID}.md"),
        },
        title: format!("title {ULID}"),
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

fn ring() -> Keyring {
    Keyring::new("k1", MachineKey::from_bytes([1; 32]), vec![]).unwrap()
}

/// Shows each issue's creation revision as a signed marker for the nonce the fake logged for it.
/// With `edited`, a human rewrote the body in a later revision (F4): the current body carries no
/// marker, only the creation revision does.
struct Source<'a> {
    g: &'a FakeGithub,
    nonces: &'a [String],
    edited: bool,
}

impl Source<'_> {
    fn marked_body(&self, issue: &IssueRef) -> Option<String> {
        let n: u64 = issue.0.parse().unwrap();
        let logged = self
            .g
            .log()
            .iter()
            .find(|l| l.issue == n && l.entry.field == "nonce")
            .map(|l| l.entry.value_digest.clone())?;
        let nonce = self
            .nonces
            .iter()
            .find(|c| logged == value_digest(c).as_str())?;
        let m = ring().sign(MarkerFields {
            repo_node_id: REPO.into(),
            ulid: ULID.into(),
            nonce: nonce.clone(),
        });
        Some(format!("body\n<!-- {} -->", format_marker(&m)))
    }
}

impl HistorySource for Source<'_> {
    fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
        let mut st = self.g.read(issue)?;
        if let Some(body) = self.marked_body(issue) {
            st.body = if self.edited {
                "a human rewrote this body".into()
            } else {
                body
            };
        }
        Ok(st)
    }
    fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
        Ok(vec![TimelineEvent {
            id: "E5".into(),
            created_at: START.into(),
            actor_id: BOT_ID,
            field: "title".into(),
            value: "x".into(),
        }])
    }
    fn body_revisions(&self, issue: &IssueRef) -> AdapterResult<BodyRevisions> {
        let Some(body) = self.marked_body(issue) else {
            return Ok(BodyRevisions::default());
        };
        let mut revisions = vec![BodyRevision {
            id: "R1".into(),
            created_at: START.into(),
            editor_id: Some(BOT_ID),
            body: Some(body),
        }];
        if self.edited {
            revisions.push(BodyRevision {
                id: "R2".into(),
                created_at: START.into(),
                editor_id: Some(HUMAN_ID),
                body: Some("a human rewrote this body".into()),
            });
        }
        Ok(BodyRevisions {
            revisions,
            truncated: false,
        })
    }
}

struct Listing<'a>(&'a FakeGithub);

impl ListingSource for Listing<'_> {
    fn page(&self, creator_id: u64, page: u32) -> AdapterResult<Vec<IssueSummary>> {
        if page == 1 {
            self.0.list_by_creator(creator_id)
        } else {
            Ok(vec![])
        }
    }
}

/// A cursor position read from a stub timeline, as the create protocol holds across a create.
fn pending() -> PendingCursor {
    let g = FakeGithub::new(9);
    let nonces = [];
    let source = Source {
        g: &g,
        nonces: &nonces,
        edited: false,
    };
    let mut shard = Shard::new(ULID);
    shard.history_cursor = None;
    begin_read(&source, &IssueRef("1".into()), &shard)
        .unwrap()
        .pending
}

/// What goes wrong with a run's create request.
#[derive(Debug, Clone, Copy)]
enum Fault {
    Clean,
    Lose,
    Delay(u64),
    CrashBefore,
    CrashAfter,
}

/// One ticket's mirror state across repeated runs against one fake GitHub.
struct World {
    g: FakeGithub,
    store: Mem,
    shard: Shard,
    nonces: Vec<String>,
    attempts: u32,
    edited: bool,
}

impl World {
    fn new(seed: u64, edited: bool) -> Self {
        Self {
            g: FakeGithub::new(seed),
            store: Mem::default(),
            shard: Shard::new(ULID),
            nonces: vec![],
            attempts: 0,
            edited,
        }
    }

    /// One run: recover an uncertain create, then create when no issue is mapped.
    fn run(&mut self, fault: Fault) {
        if self.shard.create_uncertain.is_some() {
            let source = Source {
                g: &self.g,
                nonces: &self.nonces,
                edited: self.edited,
            };
            let listing = Listing(&self.g);
            let ring = ring();
            let env = RecoveryEnv {
                listing: &listing,
                source: &source,
                ring: &ring,
                bot_ids: &[BOT_ID],
                repo_node_id: REPO,
                now: 0,
            };
            let (Recovery::Adopted(s) | Recovery::NotLanded(s) | Recovery::Nothing(s)) =
                recover(&mut self.store, &env, self.shard.clone()).unwrap();
            self.shard = s;
        }
        if self.shard.issue_number.is_some() {
            return;
        }
        match fault {
            Fault::Clean => {}
            Fault::Lose => self.g.lose_next_create(),
            Fault::Delay(k) => self.g.delay_next_create(k),
            Fault::CrashBefore => self.g.crash_at(self.g.calls() + 1, CrashPoint::Before),
            Fault::CrashAfter => self.g.crash_at(self.g.calls() + 1, CrashPoint::After),
        }
        self.attempts += 1;
        let run_id = format!("r{}", self.attempts);
        self.nonces.push(derive_nonce(ULID, &run_id, START));
        let step = create_issue(
            &mut self.store,
            &mut self.g,
            self.shard.clone(),
            &projection(),
            &run_id,
            START,
            pending(),
        )
        .unwrap();
        self.shard = match step {
            CreateStep::Created(c) => c.shard,
            CreateStep::Uncertain(s) | CreateStep::Blocked(s) | CreateStep::Rejected(s, _) => s,
        };
    }

    fn issue_count(&self) -> usize {
        self.g.list_by_creator(BOT_ID).unwrap().len()
    }
}

/// A fault that never lands the create late.
fn prompt_fault(rng: &mut Rng) -> Fault {
    match rng.below(4) {
        0 => Fault::Clean,
        1 => Fault::Lose,
        2 => Fault::CrashBefore,
        _ => Fault::CrashAfter,
    }
}

// frob:tests create_issue
// frob:tests recover
#[test]
fn lost_creates_and_crashes_never_make_two_issues() {
    for seed in 0..SEEDS {
        let mut rng = Rng::new(seed);
        let mut w = World::new(seed, false);
        for _ in 0..rng.below(5) {
            let fault = prompt_fault(&mut rng);
            w.run(fault);
            assert!(
                w.issue_count() <= 1,
                "seed {seed}: {fault:?} made two issues"
            );
            w.g.advance(rng.below(4));
        }
        w.run(Fault::Clean);
        w.run(Fault::Clean);
        assert_eq!(w.issue_count(), 1, "seed {seed}: exactly one issue");
        assert_eq!(
            w.shard.issue_number,
            Some(1),
            "seed {seed}: map points at it"
        );
        assert!(w.shard.create_uncertain.is_none(), "seed {seed}");
    }
}

// frob:tests create_issue
// frob:tests recover
#[test]
fn a_human_editing_the_marker_later_never_causes_a_second_issue() {
    for seed in 0..SEEDS {
        let mut rng = Rng::new(1_000 + seed);
        let mut w = World::new(seed, true);
        for _ in 0..=rng.below(4) {
            let fault = prompt_fault(&mut rng);
            w.run(fault);
            assert!(
                w.issue_count() <= 1,
                "seed {seed}: {fault:?} made two issues"
            );
        }
        w.run(Fault::Clean);
        w.run(Fault::Clean);
        assert_eq!(w.issue_count(), 1, "seed {seed}: exactly one issue");
        if let Some(n) = w.shard.issue_number {
            let source = Source {
                g: &w.g,
                nonces: &w.nonces,
                edited: true,
            };
            let current = source.issue(&IssueRef(n.to_string())).unwrap();
            assert!(
                !current.body.contains("<!--"),
                "the marker is gone from the body"
            );
        }
    }
}

// frob:tests create_issue
// frob:tests recover
// frob:tests claims_from_verdicts
// frob:tests creation_revision
// frob:tests plan_duplicates
// frob:tests close_duplicates
// frob:tests read_duplicate_history
#[test]
fn late_creates_leave_bounded_extras_that_the_next_run_closes_and_reads() {
    let mut late_seen = 0;
    for seed in 0..SEEDS {
        let mut rng = Rng::new(2_000 + seed);
        let mut w = World::new(seed, false);
        for _ in 0..=rng.below(3) {
            w.run(Fault::Delay(1 + rng.below(8)));
            w.g.advance(rng.below(10));
            assert!(
                w.issue_count() <= w.attempts as usize,
                "seed {seed}: at most one issue per attempt"
            );
        }
        w.run(Fault::Clean);
        w.g.advance(50);
        w.run(Fault::Clean);
        let total = w.issue_count();
        assert!(total <= w.attempts as usize, "seed {seed}: bounded extras");
        late_seen += total.saturating_sub(1);

        // The next run lists every bot issue, claims the ones carrying our markers, and dedupes.
        let keys = ring();
        let claims = {
            let source = Source {
                g: &w.g,
                nonces: &w.nonces,
                edited: false,
            };
            let verdicts = w.g.list_by_creator(BOT_ID).unwrap().into_iter().map(|s| {
                let creation = creation_revision(&source, &s.issue, s.creator_id).unwrap();
                (s.issue, evaluate(&creation, &[BOT_ID], &keys, REPO, 0))
            });
            claims_from_verdicts(verdicts)
        };
        assert_eq!(
            claims.len(),
            total,
            "seed {seed}: every issue carries a marker"
        );
        let plan = plan_duplicates(&claims);
        let report = close_duplicates(&mut w.g, &plan);
        assert!(report.failed.is_empty(), "seed {seed}");
        assert_eq!(report.closed.len(), total - 1, "seed {seed}");
        let open: Vec<_> =
            w.g.list_by_creator(BOT_ID)
                .unwrap()
                .into_iter()
                .filter(|s| !w.g.read(&s.issue).unwrap().closed)
                .collect();
        assert_eq!(open.len(), 1, "seed {seed}: one open issue");
        assert_eq!(open[0].issue, plan.canonical[ULID], "seed {seed}");

        // A human edit on each closed duplicate is still captured.
        let mark = w.g.log().last().unwrap().event.clone();
        let cursors: BTreeMap<_, _> = plan
            .duplicates
            .iter()
            .map(|d| (d.issue.clone(), mark.clone()))
            .collect();
        for d in &plan.duplicates {
            w.g.human_edit_title(&d.issue, "human edit");
        }
        for (issue, history) in read_duplicate_history(&w.g, &plan, &cursors) {
            let entries = history.unwrap();
            assert_eq!(entries.len(), 1, "seed {seed}: {}", issue.0);
            assert_eq!(entries[0].actor_id, HUMAN_ID);
            assert_eq!(entries[0].field, "title");
        }
        let again = close_duplicates(&mut w.g, &plan);
        assert!(
            again.closed.is_empty(),
            "seed {seed}: closing is idempotent"
        );
    }
    assert!(late_seen > 0, "some seed must exercise a late landing");
}
