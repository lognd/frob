//! The ticket-branch layout: files at computed paths, events under `.events/<ULID>/`.

use frob_ledger::branch::init_branch;
use frob_ledger::model::TicketType;
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::{Layout, Ledger, LedgerConfig};
use gob_git::{Repo, TreeRef};

const BRANCH: &str = "frob-tickets";
const EMPTY_TREE: &str = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";

/// A fixture repository with an orphan ticket branch and a ledger reading the branch layout.
fn fixture() -> (tempfile::TempDir, Ledger) {
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = Repo::init(dir.path()).expect("init");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir.path()).expect("discover");
    init_branch(&repo, BRANCH, 5).expect("branch init");
    let cfg = LedgerConfig {
        ref_name: BRANCH.to_owned(),
        ..LedgerConfig::default()
    };
    let ledger = Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock))
        .with_layout(Layout::Branch);
    (dir, ledger)
}

/// Every file path on the ticket branch tip, sorted.
fn files(ledger: &Ledger) -> Vec<String> {
    let repo = ledger.repo();
    let empty = EMPTY_TREE.parse().expect("oid");
    let mut out: Vec<String> = repo
        .diff_names(&TreeRef::Oid(empty), &TreeRef::Ref(BRANCH.to_owned()))
        .expect("diff")
        .into_iter()
        .map(|c| c.path)
        .collect();
    out.sort();
    out
}

// frob:ticket 01M3ZX82Q2N145P3DWVVY4E868
#[test]
fn a_ticket_under_an_epic_lands_in_the_epic_directory_with_events_under_dot_events() {
    let (_dir, ledger) = fixture();
    let epic = ledger
        .new_ticket(NewTicket::new("Parser Rewrite!", TicketType::Epic))
        .expect("epic");
    let mut req = NewTicket::new("Lex the input", TicketType::Task);
    req.parent = Some(epic.ticket.front.id);
    let child = ledger.new_ticket(req).expect("child");
    let id = child.ticket.front.id;
    let epic_id = epic.ticket.front.id;
    let ev = child.events[0].to_string();
    let all = files(&ledger);
    assert!(
        all.contains(&"parser-rewrite/EPIC.md".to_owned()),
        "{all:?}"
    );
    assert!(
        all.contains(&"parser-rewrite/lex-the-input.md".to_owned()),
        "{all:?}"
    );
    assert!(all.contains(&format!(".events/{id}/{ev}.toml")), "{all:?}");
    assert!(
        all.iter()
            .any(|p| p.starts_with(&format!(".events/{epic_id}/")))
    );
    assert!(all.iter().all(|p| !p.starts_with("tickets/")), "{all:?}");
}

// frob:ticket 01M3ZX82Q2N145P3DWVVY4E868
#[test]
fn a_ticket_without_an_epic_lands_in_unfiled() {
    let (_dir, ledger) = fixture();
    ledger
        .new_ticket(NewTicket::new("Loose end", TicketType::Task))
        .expect("ticket");
    assert!(files(&ledger).contains(&"_unfiled/loose-end.md".to_owned()));
}

// frob:ticket 01M3ZX82Q2N145P3DWVVY4E868
#[test]
fn sub_epics_are_flattened_and_a_title_change_does_not_move_the_file() {
    let (_dir, ledger) = fixture();
    let top = ledger
        .new_ticket(NewTicket::new("Top", TicketType::Epic))
        .expect("top");
    let mut sub = NewTicket::new("Sub", TicketType::Epic);
    sub.parent = Some(top.ticket.front.id);
    let sub = ledger.new_ticket(sub).expect("sub");
    let mut leaf = NewTicket::new("Leaf", TicketType::Task);
    leaf.parent = Some(sub.ticket.front.id);
    let leaf = ledger.new_ticket(leaf).expect("leaf");
    let all = files(&ledger);
    assert!(all.contains(&"top/sub.md".to_owned()), "{all:?}");
    assert!(all.contains(&"top/leaf.md".to_owned()), "{all:?}");
    let patch = Patch {
        sets: vec![(
            "title".to_owned(),
            Some(toml::Value::String("Renamed".into())),
        )],
        ..Patch::default()
    };
    ledger.update(leaf.ticket.front.id, &patch).expect("update");
    let after = files(&ledger);
    assert!(after.contains(&"top/leaf.md".to_owned()), "{after:?}");
    assert!(!after.contains(&"top/renamed.md".to_owned()), "{after:?}");
    let events = ledger.events(leaf.ticket.front.id).expect("events");
    assert_eq!(events.len(), 2);
}

// frob:ticket 01M3ZX82Q2N145P3DWVVY4E868
#[test]
fn two_tickets_with_one_slug_do_not_overwrite_each_other() {
    let (_dir, ledger) = fixture();
    let a = ledger
        .new_ticket(NewTicket::new("Same", TicketType::Task))
        .expect("a");
    let b = ledger
        .new_ticket(NewTicket::new("Same", TicketType::Task))
        .expect("b");
    let all = files(&ledger);
    let md: Vec<_> = all.iter().filter(|p| p.starts_with("_unfiled/")).collect();
    assert_eq!(md.len(), 2, "{all:?}");
    assert_ne!(a.ticket.front.id, b.ticket.front.id);
}
