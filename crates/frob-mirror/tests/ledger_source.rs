//! The concrete ledger-side `TicketSource` over a real ledger in a temp repository.

// frob:ticket 01M5EBMAWCRQ2S1GGPYACC0466

use std::collections::BTreeSet;
use std::sync::Arc;

use frob_ledger::event::{EventBody, ProposalData};
use frob_ledger::mirror_map::shard_path;
use frob_ledger::model::{Category as LCategory, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use frob_mirror::host::TicketSource;
use frob_mirror::ledger_source::{FIELD_STATE, FIELD_TITLE, LedgerTickets};
use frob_mirror::projection::{Category, Classification, Identity, People, State, TicketFacts};
use gob_git::{CommitOptions, RelPath, Repo};

fn fresh() -> (tempfile::TempDir, Ledger) {
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = Repo::init(dir.path()).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir.path()).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hi\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        Arc::new(gob_time::SystemClock),
    );
    (dir, ledger)
}

fn make(ledger: &Ledger, title: &str) -> TicketId {
    let mut req = NewTicket::new(title, TicketType::Task);
    req.category = LCategory::Todo;
    ledger.new_ticket(req).expect("create").ticket.front.id
}

fn facts(ledger: &Ledger, id: TicketId) -> Option<TicketFacts> {
    let view = ledger.show(id).ok()?;
    Some(TicketFacts {
        identity: Identity {
            ulid: id.to_string(),
            handle: "~T".into(),
            aliases: vec![],
            repository: "r".into(),
            ledger_path: "p".into(),
        },
        title: view.ticket.front.title.clone(),
        summary: String::new(),
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
    })
}

fn map(ledger: &Ledger, id: TicketId, issue: u64) {
    let r = ledger.ledger_write_ref().expect("write ref");
    ledger
        .repo()
        .commit_paths(
            &r,
            &[(
                RelPath::new(shard_path(id)).expect("path"),
                Some(format!("issue = {issue}\n").into_bytes()),
            )],
            "map",
            &CommitOptions::default(),
        )
        .expect("shard");
}

#[test]
fn ledger_source_reads_and_records() {
    // frob:tests LedgerTickets.mirrored
    // frob:tests LedgerTickets.creatable
    // frob:tests LedgerTickets.projection
    // frob:tests LedgerTickets.events
    // frob:tests LedgerTickets.state
    // frob:tests LedgerTickets.commit_proposals
    // frob:tests LedgerTickets.commits
    let (_dir, ledger) = fresh();
    let a = make(&ledger, "mapped one");
    let b = make(&ledger, "fresh two");
    map(&ledger, a, 7);

    let mut src = LedgerTickets::new(&ledger, Box::new(facts), BTreeSet::new(), "test");
    assert_eq!(src.mirrored(), vec![a.to_string()]);
    let creatable = src.creatable();
    assert_eq!(creatable.len(), 1);
    assert_eq!(creatable[0].0, b.to_string());

    let p = src.projection(&a.to_string()).expect("projection");
    assert_eq!(p.title, "mapped one");
    assert!(src.projection("not-a-ulid").is_none());

    let events = src.events();
    assert!(
        events.iter().any(|e| e.ticket == a.to_string()
            && e.field == FIELD_TITLE
            && e.value == "mapped one")
    );
    assert!(events.windows(2).all(|w| w[0].event <= w[1].event));

    let st = src.state(&a.to_string()).expect("state");
    assert_eq!(
        st.projection.get(FIELD_TITLE).map(String::as_str),
        Some("mapped one")
    );
    assert_eq!(
        st.projection.get(FIELD_STATE).map(String::as_str),
        Some("open")
    );
    let before = st.existing.len();

    let before_commits = src.commits();
    assert!(before_commits.iter().all(|c| !c.own));

    let prop = ProposalData {
        tracker_event: "t1".into(),
        item: "7".into(),
        field: "title".into(),
        actor_id: "9".into(),
        time: gob_time::Stamp::from_unix(0),
        digest: "d".into(),
        excerpt: "x".into(),
        origin: "tracker".into(),
        supersedes: None,
    };
    src.commit_proposals(
        &a.to_string(),
        vec![frob_ledger::event::Event::new(
            gob_time::Stamp::from_unix(0),
            "mirror",
            EventBody::Proposal(prop),
        )],
    )
    .expect("recorded");
    assert_eq!(
        src.state(&a.to_string()).expect("state").existing.len(),
        before + 1
    );
    let after = src.commits();
    assert_eq!(after.len(), before_commits.len() + 1);
    assert!(after.last().expect("last").own);
}
