//! Create protocol against the fake GitHub (mirror.md 3.3 "Create protocol"; F3, F5).

// frob:ticket 01M4052S7VEWJEYG78GNA1Z28V
#![allow(dead_code)]

#[path = "support/fake_github.rs"]
mod fake_github;

use std::collections::{BTreeSet, HashMap};

use fake_github::{BOT_ID, CrashPoint, FakeGithub};
use frob_mirror::adapter::{AdapterResult, IssueRef, IssueState, IssueSummary, TrackerAdapter};
use frob_mirror::create::{CreateStep, Recovery, RecoveryEnv, create_issue, derive_nonce, recover};
use frob_mirror::cursor::{Committed, begin_read};
use frob_mirror::github::lookup::ListingSource;
use frob_mirror::github::read::{BodyRevisions, HistorySource, TimelineEvent};
use frob_mirror::journal::value_digest;
use frob_mirror::keyring::{Keyring, MarkerFields};
use frob_mirror::mapfile::{MapError, Shard, ShardStore, content_hash, read_shard};
use frob_mirror::marker::format_marker;
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, People, State, TicketFacts, project,
};
use gob_trust::MachineKey;

const START: &str = "2026-01-01T00:00:00Z";
const REPO: &str = "R_1";

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

fn ring() -> Keyring {
    Keyring::new("k1", MachineKey::from_bytes([1; 32]), vec![]).unwrap()
}

/// Reads the fake and shows each issue's creation body as a signed marker for the nonce the
/// fake logged for it, as the real adapter embeds one.
struct Source<'a> {
    g: &'a FakeGithub,
    ulid: &'a str,
    nonces: Vec<String>,
}

impl HistorySource for Source<'_> {
    fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
        let mut st = self.g.read(issue)?;
        let n: u64 = issue.0.parse().unwrap();
        let logged = self
            .g
            .log()
            .iter()
            .find(|l| l.issue == n && l.entry.field == "nonce")
            .map(|l| l.entry.value_digest.clone());
        if let Some(nonce) = self
            .nonces
            .iter()
            .find(|c| logged.as_deref() == Some(value_digest(c).as_str()))
        {
            let m = ring().sign(MarkerFields {
                repo_node_id: REPO.into(),
                ulid: self.ulid.into(),
                nonce: nonce.clone(),
            });
            st.body = format!("body\n<!-- {} -->", format_marker(&m));
        }
        Ok(st)
    }
    fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
        Ok(vec![TimelineEvent {
            id: "E5".into(),
            created_at: START.into(),
            actor_id: 2,
            field: "title".into(),
            value: "x".into(),
        }])
    }
    fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
        Ok(BodyRevisions::default())
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

fn recover_with(g: &FakeGithub, store: &mut Mem, shard: Shard, nonces: Vec<String>) -> Recovery {
    let ulid = shard.ulid.clone();
    let source = Source {
        g,
        ulid: &ulid,
        nonces,
    };
    let listing = Listing(g);
    let ring = ring();
    let env = RecoveryEnv {
        listing: &listing,
        source: &source,
        ring: &ring,
        bot_ids: &[BOT_ID],
        repo_node_id: REPO,
        now: 0,
    };
    recover(store, &env, shard).unwrap()
}

fn pending_none() -> frob_mirror::cursor::PendingCursor {
    let g = FakeGithub::new(9);
    let source = Source {
        g: &g,
        ulid: "X",
        nonces: vec![],
    };
    let mut shard = Shard::new("X");
    shard.history_cursor = None;
    let read = begin_read(&source, &IssueRef("1".into()), &shard).unwrap();
    // The stub timeline holds one event, so this is a real position.
    read.pending
}

// frob:tests create_issue
#[test]
fn timed_out_create_blocks_a_second_create_before_recovery() {
    let mut g = FakeGithub::new(1);
    let mut store = Mem::default();
    g.lose_next_create();
    let step = create_issue(
        &mut store,
        &mut g,
        Shard::new("U1"),
        &projection("U1"),
        "r1",
        START,
        pending_none(),
    )
    .unwrap();
    let CreateStep::Uncertain(shard) = step else {
        panic!("expected Uncertain")
    };
    assert!(shard.create_uncertain.is_some());
    let before = g.calls();
    let step = create_issue(
        &mut store,
        &mut g,
        shard,
        &projection("U1"),
        "r2",
        START,
        pending_none(),
    )
    .unwrap();
    assert!(matches!(step, CreateStep::Blocked(_)));
    assert_eq!(g.calls(), before, "no second create request");
    let stored = read_shard(&store, "U1").unwrap().unwrap();
    assert!(stored.create_uncertain.is_some(), "the flag is durable");
}

// frob:tests recover
#[test]
fn recovery_adopts_the_issue_matching_the_nonce() {
    let mut g = FakeGithub::new(1);
    let mut store = Mem::default();
    let call = g.calls() + 1;
    g.crash_at(call, CrashPoint::After);
    let step = create_issue(
        &mut store,
        &mut g,
        Shard::new("U1"),
        &projection("U1"),
        "r1",
        START,
        pending_none(),
    )
    .unwrap();
    let CreateStep::Uncertain(shard) = step else {
        panic!("expected Uncertain")
    };
    let nonce = derive_nonce("U1", "r1", START);
    let r = recover_with(&g, &mut store, shard, vec![nonce]);
    let Recovery::Adopted(adopted) = r else {
        panic!("expected Adopted, got {r:?}")
    };
    assert_eq!(adopted.issue_number, Some(1));
    assert!(adopted.create_uncertain.is_none());
    let stored = read_shard(&store, "U1").unwrap().unwrap();
    assert_eq!(stored, adopted);
}

// frob:tests recover
#[test]
fn a_spoofed_or_foreign_nonce_is_not_adopted() {
    let mut g = FakeGithub::new(1);
    let mut store = Mem::default();
    g.lose_next_create();
    let step = create_issue(
        &mut store,
        &mut g,
        Shard::new("U1"),
        &projection("U1"),
        "r1",
        START,
        pending_none(),
    )
    .unwrap();
    let CreateStep::Uncertain(shard) = step else {
        panic!("expected Uncertain")
    };
    g.human_create_marked("t", "b", &derive_nonce("U1", "r1", START));
    let r = recover_with(&g, &mut store, shard, vec![derive_nonce("U1", "r1", START)]);
    assert!(matches!(r, Recovery::NotLanded(_)), "{r:?}");
}

// frob:tests create_issue
// frob:tests recover
#[test]
fn a_late_create_after_a_retry_leaves_at_most_one_extra_issue() {
    let mut g = FakeGithub::new(1);
    let mut store = Mem::default();
    g.delay_next_create(5);
    let step = create_issue(
        &mut store,
        &mut g,
        Shard::new("U1"),
        &projection("U1"),
        "r1",
        START,
        pending_none(),
    )
    .unwrap();
    let CreateStep::Uncertain(shard) = step else {
        panic!("expected Uncertain")
    };
    let n1 = derive_nonce("U1", "r1", START);
    let r = recover_with(&g, &mut store, shard, vec![n1]);
    let Recovery::NotLanded(shard) = r else {
        panic!("expected NotLanded, got {r:?}")
    };
    let step = create_issue(
        &mut store,
        &mut g,
        shard,
        &projection("U1"),
        "r2",
        START,
        pending_none(),
    )
    .unwrap();
    assert!(matches!(step, CreateStep::Created(_)));
    g.advance(10);
    let listed = g.list_by_creator(BOT_ID).unwrap();
    assert_eq!(listed.len(), 2, "the original plus at most one extra");
}

// frob:tests create_issue
#[test]
fn the_cursor_taken_before_listing_is_the_one_stored() {
    let mut g = FakeGithub::new(1);
    let mut store = Mem::default();
    let pending = pending_none();
    let held = pending.position().cloned().expect("a position was read");
    let step = create_issue(
        &mut store,
        &mut g,
        Shard::new("U1"),
        &projection("U1"),
        "r1",
        START,
        pending.clone(),
    )
    .unwrap();
    let CreateStep::Created(created) = step else {
        panic!("expected Created")
    };
    assert_eq!(created.pending, pending, "held across the create");
    assert_eq!(
        created.shard.history_cursor, None,
        "not stored before the proposals commit"
    );
    let shard = created
        .store_cursor(&mut store, Committed::confirm())
        .unwrap();
    assert_eq!(
        shard.history_cursor.as_deref(),
        Some(held.event().0.as_str())
    );
    assert_eq!(shard.issue_number, Some(1));
    assert_eq!(read_shard(&store, "U1").unwrap().unwrap(), shard);
}
