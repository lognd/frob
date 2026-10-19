//! Self-tests for the fake GitHub (mirror.md 3.7); later property tests reuse `fake_github`.

// frob:ticket 01M4052WAB3H52W92NYG3AS571
#![allow(dead_code)]

mod fake_github;

use std::collections::BTreeSet;

use fake_github::{BOT_ID, Chaos, CrashPoint, FakeGithub, HUMAN_ID, Snapshot};
use frob_mirror::adapter::{AdapterError, CreateOutcome, IssueRef, TrackerAdapter};
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, Outcome, People, State, TicketFacts,
    project,
};

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

fn created(o: CreateOutcome) -> IssueRef {
    match o {
        CreateOutcome::Created(i) => i,
        other => panic!("expected Created, got {other:?}"),
    }
}

/// A mixed workload whose outcome depends only on the seed.
fn scenario(seed: u64) -> Snapshot {
    let mut g = FakeGithub::new(seed).with_chaos(Chaos {
        lose_create: 100,
        delay_create: 150,
        duplicate: 100,
        crash: 100,
    });
    let mut refs: Vec<IssueRef> = Vec::new();
    for k in 0..20 {
        let p = projection(&format!("U{k}"));
        if let CreateOutcome::Created(i) = g.create(&p, &format!("n{k}")) {
            refs.push(i);
        }
        if let Some(i) = refs.last() {
            let _ = g.update(i, &p);
            let _ = g.add_labels(i, &[format!("l{k}")]);
        }
        g.advance(1);
        let _ = g.list_by_creator(BOT_ID);
    }
    g.advance(10);
    g.snapshot()
}

// frob:tests create
// frob:tests update
// frob:tests add_labels
// frob:tests list_by_creator
#[test]
fn same_seed_replays_identically() {
    assert_eq!(scenario(42), scenario(42));
    assert_ne!(scenario(42), scenario(43));
}

// frob:tests create
// frob:tests list_by_creator
// frob:tests history_after
#[test]
fn delayed_create_lands_later_with_ordered_event_id() {
    let mut g = FakeGithub::new(1);
    g.delay_next_create(3);
    assert_eq!(g.create(&projection("A"), "nA"), CreateOutcome::Unknown);
    let b = created(g.create(&projection("B"), "nB"));
    assert_eq!(g.list_by_creator(BOT_ID).unwrap().len(), 1);
    let last_before = g.log().last().unwrap().event.clone();
    g.advance(2);
    assert_eq!(g.list_by_creator(BOT_ID).unwrap().len(), 1);
    g.advance(1);
    let listed = g.list_by_creator(BOT_ID).unwrap();
    assert_eq!(listed.len(), 2);
    assert_eq!(listed[1].issue, b, "newest first: the late issue is newest");
    let late = IssueRef("2".into());
    let h = g.history_after(&late, None).unwrap();
    assert!(h.iter().all(|e| e.event > last_before));
    assert!(h.windows(2).all(|w| w[0].event < w[1].event));
    assert_eq!(g.pending_creates(), 0);
}

// frob:tests create
#[test]
fn lost_create_never_lands_and_duplicate_makes_two() {
    let mut g = FakeGithub::new(1);
    g.lose_next_create();
    assert_eq!(g.create(&projection("A"), "n"), CreateOutcome::Unknown);
    g.advance(100);
    assert!(g.list_by_creator(BOT_ID).unwrap().is_empty());
    g.duplicate_next_write();
    created(g.create(&projection("A"), "n"));
    assert_eq!(g.list_by_creator(BOT_ID).unwrap().len(), 2);
}

// frob:tests create
// frob:tests close
// frob:tests read
#[test]
fn crash_before_drops_and_crash_after_applies() {
    let mut g = FakeGithub::new(1);
    let i = created(g.create(&projection("A"), "n"));
    g.crash_at(g.calls() + 1, CrashPoint::Before);
    assert!(g.close(&i, Outcome::Done).is_err());
    assert!(!g.read(&i).unwrap().closed);
    g.crash_at(g.calls() + 1, CrashPoint::After);
    assert!(g.close(&i, Outcome::Done).is_err());
    assert!(g.read(&i).unwrap().closed);
}

// frob:tests history_after
// frob:tests remove_labels
// frob:tests update
#[test]
fn adversaries_leave_human_history() {
    let mut g = FakeGithub::new(1);
    let i = created(g.create(&projection("A"), "n"));
    let mark = g.log().last().unwrap().event.clone();
    g.human_edit_title(&i, "hijack");
    g.human_edit_body(&i, "body");
    g.human_add_label(&i, "x");
    g.human_spoof_marker(&i, "n");
    let h = g.history_after(&i, Some(&mark)).unwrap();
    assert_eq!(h.len(), 4);
    assert!(h.iter().all(|e| e.actor_id == HUMAN_ID));
    let theirs = g.human_create_marked("t", "b", "n");
    let mine = g.list_by_creator(BOT_ID).unwrap();
    assert_eq!(mine.len(), 1);
    assert_eq!(g.list_by_creator(HUMAN_ID).unwrap()[0].issue, theirs);
    g.remove_labels(&i, &["x".into()]).unwrap();
    assert!(g.read(&i).unwrap().labels.is_empty());
}

// frob:tests read
// frob:tests list_by_creator
#[test]
fn call_budget_refuses_the_next_call() {
    let budget = 3;
    let g = FakeGithub::new(1).with_call_budget(budget);
    for _ in 0..budget {
        assert!(g.list_by_creator(BOT_ID).is_ok());
    }
    assert_eq!(g.list_by_creator(BOT_ID), Err(AdapterError::RateLimited));
    assert_eq!(g.refused(), 1);
    assert_eq!(g.calls(), budget + 1);
    assert_eq!(
        g.read(&IssueRef("1".into())),
        Err(AdapterError::RateLimited)
    );
    assert_eq!(g.refused(), 2);
}
