//! `doable` hides what another holder's epic claim covers, from the local view.

// frob:ticket 01M5DJ4K69T67D50C19B4NY6RM

use std::collections::HashMap;

use frob_ledger::claim_cover::Claim;
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::index::Summary;
use frob_ledger::model::{Category, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Layout, Ledger, LedgerConfig, TicketId};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

/// Leases that only report claims.
struct Claims(HashMap<TicketId, Claim>);

impl LeaseCheck for Claims {
    fn is_free(&self, _ticket: &Summary, _scope: &[String]) -> bool {
        true
    }

    fn claims(&self) -> HashMap<TicketId, Claim> {
        self.0.clone()
    }
}

/// A repository on `main` with an identity and an open ledger.
fn fixture() -> (tempfile::TempDir, Ledger) {
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
        MAIN,
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hello\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .with_layout(Layout::Dir);
    (dir, ledger)
}

/// Create a todo ticket of `ty` under `parent`.
fn make(ledger: &Ledger, title: &str, ty: TicketType, parent: Option<TicketId>) -> TicketId {
    let mut req = NewTicket::new(title, ty);
    req.category = Category::Todo;
    req.parent = parent;
    ledger.new_ticket(req).expect("create").ticket.front.id
}

// frob:tests frob_ledger::ops::Ledger::doable
#[test]
fn another_holders_epic_claim_hides_its_leaves_but_not_the_holders() {
    let (_dir, ledger) = fixture();
    let epic = make(&ledger, "epic", TicketType::Epic, None);
    let leaf = make(&ledger, "leaf", TicketType::Task, Some(epic));
    let free = make(&ledger, "free", TicketType::Task, None);

    let ids = |l: &dyn LeaseCheck| -> Vec<TicketId> {
        let mut v: Vec<_> = ledger
            .doable(l)
            .expect("doable")
            .iter()
            .map(|s| s.id)
            .collect();
        v.sort();
        v
    };
    let mut both = vec![leaf, free];
    both.sort();
    assert_eq!(ids(&NoLeases), both);

    let theirs = Claims(HashMap::from([(
        epic,
        Claim {
            holder: "someone else".into(),
        },
    )]));
    assert_eq!(ids(&theirs), vec![free], "covered leaf is hidden");

    let mine = Claims(HashMap::from([(
        epic,
        Claim {
            holder: "Test User".into(),
        },
    )]));
    assert_eq!(ids(&mine), both, "the holder still sees its own leaves");
}

// frob:tests frob_ledger::ops::Ledger::cover_map
#[test]
fn cover_map_feeds_split_and_move_notices() {
    let (_dir, ledger) = fixture();
    let epic = make(&ledger, "epic", TicketType::Epic, None);
    let leaf = make(&ledger, "leaf", TicketType::Task, Some(epic));
    let claims = HashMap::from([(
        epic,
        Claim {
            holder: "someone else".into(),
        },
    )]);
    let cover = ledger.cover_map(claims).expect("cover");
    assert!(cover.split_notice(epic, leaf).is_some());
    assert!(cover.move_warning(leaf, None).is_some());
    assert!(cover.move_warning(leaf, Some(epic)).is_none());
}
