//! The ticket-branch layout: files at computed paths, events under `.events/<ULID>/`.

use frob_ledger::branch::init_branch;
use frob_ledger::model::TicketType;
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::{Layout, Ledger, LedgerConfig, TicketId};
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

/// Move the file of `id` to `to` in one ledger commit, as a reindex does.
fn move_card(ledger: &Ledger, from: &str, to: &str) {
    let repo = ledger.repo();
    let text = repo
        .read_blob_at(BRANCH, from)
        .expect("read")
        .expect("present");
    repo.commit_paths(
        BRANCH,
        &[
            (gob_git::RelPath::new(from).expect("from"), None),
            (gob_git::RelPath::new(to).expect("to"), Some(text)),
        ],
        "tickets(reindex): move",
        &gob_git::CommitOptions::default(),
    )
    .expect("move");
}

// frob:ticket 01M3ZX82TWWY2616S1Q5N48KNK
#[test]
fn a_moved_ticket_file_resolves_through_its_ulid_and_still_equals_the_fold() {
    let (_dir, ledger) = fixture();
    let made = ledger
        .new_ticket(NewTicket::new("Wander", TicketType::Task))
        .expect("new");
    let id = made.ticket.front.id;
    let other = ledger
        .new_ticket(NewTicket::new("Stay", TicketType::Task))
        .expect("other")
        .ticket
        .front
        .id;
    move_card(
        &ledger,
        "_unfiled/wander.md",
        "elsewhere/renamed-by-reindex.md",
    );
    let before = ledger.show(id).expect("show");
    assert_eq!(before.ticket.front.title, "Wander");
    let tip = ledger.repo().rev_parse(BRANCH).expect("tip").to_string();
    let events = ledger.read_events_at(&tip, id).expect("events");
    assert_eq!(
        frob_ledger::fold::fold(id, &events).expect("fold").ticket,
        before.ticket
    );
    let ids = ledger.ticket_ids_at(&tip).expect("ids");
    assert!(ids.contains(&id) && ids.contains(&other), "{ids:?}");
    assert!(
        ledger
            .ticket_exists_at(BRANCH, &id.to_string())
            .expect("exists")
    );
    assert!(
        !ledger
            .ticket_exists_at(BRANCH, &TicketId::mint().to_string())
            .expect("exists")
    );
    assert!(ledger.doctor(false).expect("doctor").is_clean());

    // A later write rewrites the file where it now is instead of recreating the old path.
    ledger
        .comment(id, frob_ledger::model::CommentSubtype::Note, "hi")
        .expect("comment");
    let all = files(&ledger);
    assert!(
        all.contains(&"elsewhere/renamed-by-reindex.md".to_owned()),
        "{all:?}"
    );
    assert!(!all.contains(&"_unfiled/wander.md".to_owned()), "{all:?}");
    assert!(ledger.doctor(false).expect("doctor").is_clean());
}

// frob:ticket 01M3ZX82TWWY2616S1Q5N48KNK
#[test]
fn the_doctor_flags_events_whose_ticket_file_is_gone() {
    let (_dir, ledger) = fixture();
    let id = ledger
        .new_ticket(NewTicket::new("Doomed", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    let repo = ledger.repo();
    repo.commit_paths(
        BRANCH,
        &[(
            gob_git::RelPath::new("_unfiled/doomed.md").expect("p"),
            None,
        )],
        "drop the card",
        &gob_git::CommitOptions::default(),
    )
    .expect("drop");
    let report = ledger.doctor(false).expect("doctor");
    assert_eq!(report.issues.len(), 1, "{report:?}");
    assert_eq!(report.issues[0].code, "E-DOCTOR-ORPHAN-EVENTS");
    assert_eq!(report.issues[0].ticket, id);
}

// frob:ticket 01M3ZX82TWWY2616S1Q5N48KNK
#[test]
fn the_merge_driver_finds_a_branch_ticket_by_its_frontmatter_id_and_unions_events() {
    use frob_ledger::event::{CommentData, Event, EventBody};
    let (_dir, ledger) = fixture();
    let made = ledger
        .new_ticket(NewTicket::new("Shared", TicketType::Task))
        .expect("new");
    let real = made.ticket.front.id;
    let tip = ledger.repo().rev_parse(BRANCH).expect("tip").to_string();
    let disk = tempfile::tempdir().expect("disk");
    let events_dir = disk.path().join(format!(".events/{real}"));
    std::fs::create_dir_all(&events_dir).expect("mkdir");
    for e in ledger.read_events_at(&tip, real).expect("events") {
        std::fs::write(events_dir.join(e.file_name()), e.to_toml().expect("toml")).expect("w");
    }
    let theirs = Event::new(
        gob_time::Clock::now(&gob_time::SystemClock),
        "b",
        EventBody::Comment(CommentData {
            subtype: frob_ledger::model::CommentSubtype::Note,
            body: "from the other side".into(),
        }),
    );
    let out = disk.path().join("ours.md");
    std::fs::write(
        &out,
        format!("+++\nid = \"{real}\"\n<<<<<<< ours\ntitle = \"a\"\n=======\ntitle = \"b\"\n>>>>>>> theirs\n+++\n"),
    )
    .expect("seed");
    let report = frob_ledger::merge::resolve(disk.path(), "_unfiled/shared.md", &out, vec![theirs])
        .expect("resolve");
    assert_eq!(
        (report.ticket, report.events, report.from_extra),
        (real, 2, 1)
    );
    let text = std::fs::read_to_string(&out).expect("read");
    assert!(!text.contains("<<<<<<<"), "{text}");
    let doc = frob_ledger::doc::parse("m", &text).expect("parse");
    assert_eq!(doc.front.id, real);
    // A path in a ULID directory still names its ticket without reading any document.
    let (layout, got) =
        frob_ledger::merge::locate(&format!("tickets/{real}/ticket.md"), &[]).expect("locate");
    assert_eq!((layout, got), (Layout::Dir, real));
    assert!(frob_ledger::merge::locate("a/b.md", &["no id here"]).is_err());
}
