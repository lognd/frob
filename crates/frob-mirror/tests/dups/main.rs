//! Duplicate closing against the fake GitHub (mirror.md 3.3; F6).

// frob:ticket 01M4052SBZCJ3MRHGTPAFW4QP1
#![allow(dead_code)]

#[path = "../support/fake_github.rs"]
mod fake_github;

use std::collections::BTreeMap;

use fake_github::{BOT_ID, FakeGithub, HUMAN_ID};
use frob_mirror::adapter::{CreateOutcome, IssueRef, TrackerAdapter};
use frob_mirror::dups::{Claim, close_duplicates, plan_duplicates, read_duplicate_history};
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, People, State, TicketFacts, project,
};

fn projection() -> IssueProjection {
    let facts = TicketFacts {
        identity: Identity {
            ulid: "U1".into(),
            handle: "~U1".into(),
            aliases: vec![],
            repository: "https://example.invalid/r".into(),
            ledger_path: "tickets/U1.md".into(),
        },
        title: "title".into(),
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
    project(&facts, &std::collections::BTreeSet::new(), "test")
}

/// Two bot issues for one ULID (the second created by a duplicated write) and their claims.
fn two_issues(g: &mut FakeGithub) -> Vec<Claim> {
    g.duplicate_next_write();
    assert!(matches!(
        g.create(&projection(), "n"),
        CreateOutcome::Created(_)
    ));
    g.list_by_creator(BOT_ID)
        .unwrap()
        .into_iter()
        .map(|s| Claim {
            issue: s.issue,
            ulid: "U1".into(),
        })
        .collect()
}

// frob:tests plan_duplicates
// frob:tests close_duplicates
#[test]
fn lowest_number_canonical_other_closed_as_duplicate() {
    let mut g = FakeGithub::new(1);
    let claims = two_issues(&mut g);
    let plan = plan_duplicates(&claims);
    assert_eq!(plan.canonical["U1"], IssueRef("1".into()));
    let report = close_duplicates(&mut g, &plan);
    assert_eq!(report.closed, [IssueRef("2".into())]);
    assert!(g.read(&IssueRef("2".into())).unwrap().closed);
    assert!(!g.read(&IssueRef("1".into())).unwrap().closed);
    let h = g.history_after(&IssueRef("2".into()), None).unwrap();
    assert!(h.iter().any(|e| e.field == "state"));
    assert!(h.iter().all(|e| e.field != "body" || e.actor_id == BOT_ID));
    let again = close_duplicates(&mut g, &plan);
    assert!(again.closed.is_empty());
    assert_eq!(again.already_closed.len(), 1);
}

// frob:tests read_duplicate_history
#[test]
fn edit_on_closed_duplicate_is_captured() {
    let mut g = FakeGithub::new(1);
    let plan = plan_duplicates(&two_issues(&mut g));
    close_duplicates(&mut g, &plan);
    let dup = IssueRef("2".into());
    let mark = g.log().last().unwrap().event.clone();
    g.human_edit_title(&dup, "human edit");
    let cursors = BTreeMap::from([(dup.clone(), mark)]);
    let read = read_duplicate_history(&g, &plan, &cursors);
    assert_eq!(read.len(), 1);
    let entries = read[0].1.as_ref().unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].actor_id, HUMAN_ID);
    assert_eq!(entries[0].field, "title");
}

// frob:tests close_duplicates
#[test]
fn reopened_duplicate_is_closed_again() {
    let mut g = FakeGithub::new(1);
    let plan = plan_duplicates(&two_issues(&mut g));
    close_duplicates(&mut g, &plan);
    let dup = IssueRef("2".into());
    g.human_set_closed(&dup, false);
    assert!(!g.read(&dup).unwrap().closed);
    let report = close_duplicates(&mut g, &plan);
    assert_eq!(report.closed, std::slice::from_ref(&dup));
    assert!(g.read(&dup).unwrap().closed);
}
