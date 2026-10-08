//! The incremental index sync must equal a full rebuild, in both layouts.
// frob:ticket 01M4D6NE2VCV26EG54JD672RXD

use frob_ledger::index::{Index, ListFilter};
use frob_ledger::model::{Category, LinkKind, TicketType};
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::{Layout, Ledger, LedgerConfig, RefMode, TicketId};
use gob_git::{CommitOptions, RelPath, Repo, TreeRef};
use proptest::prelude::*;

const MAIN: &str = "refs/heads/main";

fn fixture(layout: Layout) -> (tempfile::TempDir, Ledger) {
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
    let cfg = LedgerConfig {
        mode: RefMode::Trunk,
        ..LedgerConfig::default()
    };
    (
        dir,
        Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock)).with_layout(layout),
    )
}

fn second_handle(dir: &std::path::Path, layout: Layout) -> Ledger {
    Ledger::open(
        Repo::discover(dir).expect("discover"),
        LedgerConfig {
            mode: RefMode::Trunk,
            ..LedgerConfig::default()
        },
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .with_layout(layout)
}

/// Repository path of the document of ticket `id` at the tip of `MAIN`.
fn card_path(ledger: &Ledger, id: TicketId) -> Option<String> {
    if ledger.layout() == Layout::Dir {
        return Some(format!("tickets/{id}/ticket.md"));
    }
    let repo = ledger.repo();
    let empty = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        .parse()
        .expect("oid");
    repo.diff_names(&TreeRef::Oid(empty), &TreeRef::Ref(MAIN.to_owned()))
        .expect("diff")
        .into_iter()
        .map(|c| c.path)
        .find(|p| {
            std::path::Path::new(p)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("md"))
                && repo
                    .read_blob_at(MAIN, p)
                    .ok()
                    .flatten()
                    .is_some_and(|b| String::from_utf8_lossy(&b).contains(&id.to_string()))
        })
}

fn raw_commit(ledger: &Ledger, changes: &[(String, Option<Vec<u8>>)], msg: &str) {
    let rel: Vec<_> = changes
        .iter()
        .map(|(p, b)| (RelPath::new(p.clone()).expect("path"), b.clone()))
        .collect();
    ledger
        .repo()
        .commit_paths(MAIN, &rel, msg, &CommitOptions::default())
        .expect("raw commit");
}

/// Everything the index answers, in a stable order.
fn dump(db: &std::path::Path, ledger: &Ledger) -> Vec<String> {
    let listed = ledger.list(&ListFilter::default()).expect("list");
    let index = Index::open(db).expect("open");
    let mut out: Vec<String> = listed.iter().map(|s| format!("{s:?}")).collect();
    for id in index.all_ids().expect("ids") {
        out.push(format!("{:?}", index.get(id).expect("get")));
        out.push(format!("{:?}", index.incoming(id).expect("incoming")));
    }
    let mut edges: Vec<String> = index
        .edges()
        .expect("edges")
        .iter()
        .map(|e| format!("{e:?}"))
        .collect();
    edges.sort();
    out.extend(edges);
    out
}

#[derive(Debug, Clone)]
enum Op {
    New(u8),
    NewExternal(u8),
    Update(u8, u8),
    Link(u8, u8),
    PmWrite(u8),
    RawDelete(u8),
    RawEdit(u8),
    RawMove(u8),
    Read,
    Check,
}

fn op() -> impl Strategy<Value = Op> {
    prop_oneof![
        3 => any::<u8>().prop_map(Op::New),
        2 => any::<u8>().prop_map(Op::NewExternal),
        3 => (any::<u8>(), any::<u8>()).prop_map(|(a, b)| Op::Update(a, b)),
        2 => (any::<u8>(), any::<u8>()).prop_map(|(a, b)| Op::Link(a, b)),
        3 => any::<u8>().prop_map(Op::PmWrite),
        1 => any::<u8>().prop_map(Op::RawDelete),
        2 => any::<u8>().prop_map(Op::RawEdit),
        1 => any::<u8>().prop_map(Op::RawMove),
        3 => Just(Op::Read),
        3 => Just(Op::Check),
    ]
}

fn pick(ids: &[TicketId], n: u8) -> Option<TicketId> {
    (!ids.is_empty()).then(|| ids[usize::from(n) % ids.len()])
}

/// Dump the incrementally synced index, wipe it so the next read rebuilds in full, and compare.
fn compare(db: &std::path::Path, ledger: &Ledger, other: &Ledger) {
    let incremental = dump(db, ledger);
    let mut idx = Index::open(db).expect("open");
    idx.rebuild("stale-key", &[], 7).expect("wipe");
    drop(idx);
    assert_eq!(
        incremental,
        dump(db, other),
        "incremental sync diverged from a rebuild"
    );
}

fn run(layout: Layout, ops: &[Op]) {
    let (dir, ledger) = fixture(layout);
    let other = second_handle(dir.path(), layout);
    let db = dir.path().join(".frob/tickets.sqlite");
    let mut ids: Vec<TicketId> = Vec::new();
    let mut serial = 0_u32;
    for step in ops {
        serial += 1;
        match step {
            Op::New(n) => {
                let t = NewTicket::new(format!("Ticket {serial}-{n}"), TicketType::Task);
                ids.push(ledger.new_ticket(t).expect("new").ticket.front.id);
            }
            Op::NewExternal(n) => {
                let t = NewTicket::new(format!("External {serial}-{n}"), TicketType::Task);
                ids.push(other.new_ticket(t).expect("new").ticket.front.id);
            }
            Op::Update(i, v) => {
                if let Some(id) = pick(&ids, *i) {
                    let patch = Patch {
                        add_labels: vec![format!("l{}", v % 4)],
                        ..Patch::default()
                    };
                    let _ = ledger.update(id, &patch);
                }
            }
            Op::Link(a, b) => {
                if let (Some(x), Some(y)) = (pick(&ids, *a), pick(&ids, *b))
                    && x != y
                {
                    let _ = other.link(x, LinkKind::BlockedBy, y);
                }
            }
            Op::PmWrite(n) => {
                // A pm object file next to the tickets, as a milestone or cycle commit writes it.
                let path = match layout {
                    Layout::Dir => format!("tickets/_milestones/M{n}/milestone.md"),
                    Layout::Branch => format!("_milestones/M{n}/milestone.md"),
                };
                raw_commit(
                    &ledger,
                    &[(path, Some(format!("v{serial}\n").into_bytes()))],
                    "pm",
                );
            }
            Op::RawDelete(i) => {
                if let Some(id) = pick(&ids, *i)
                    && let Some(p) = card_path(&ledger, id)
                    && ledger
                        .repo()
                        .read_blob_at(MAIN, &p)
                        .ok()
                        .flatten()
                        .is_some()
                {
                    raw_commit(&ledger, &[(p, None)], "delete");
                }
            }
            Op::RawEdit(i) => {
                if let Some(id) = pick(&ids, *i)
                    && let Some(p) = card_path(&ledger, id)
                    && let Some(b) = ledger.repo().read_blob_at(MAIN, &p).ok().flatten()
                {
                    let text = String::from_utf8_lossy(&b).replacen(
                        "priority = \"medium\"",
                        "priority = \"high\"",
                        1,
                    );
                    raw_commit(&ledger, &[(p, Some(text.into_bytes()))], "edit");
                }
            }
            Op::RawMove(i) => {
                if layout == Layout::Branch
                    && let Some(id) = pick(&ids, *i)
                    && let Some(p) = card_path(&ledger, id)
                    && let Some(b) = ledger.repo().read_blob_at(MAIN, &p).ok().flatten()
                {
                    let to = format!("_unfiled/moved-{serial}.md");
                    if to != p {
                        raw_commit(&ledger, &[(p, None), (to, Some(b))], "move");
                    }
                }
            }
            Op::Read => {
                ledger.list(&ListFilter::default()).expect("list");
            }
            Op::Check => compare(&db, &ledger, &other),
        }
    }
    compare(&db, &ledger, &other);
}

fn property(layout: Layout) {
    let config = ProptestConfig {
        cases: 4,
        ..ProptestConfig::default()
    };
    proptest!(config, |(ops in proptest::collection::vec(op(), 1..24))| {
        run(layout, &ops);
    });
}

// frob:tests crates/frob-ledger/src/index.rs::Index.patch
#[test]
fn incremental_equals_rebuild_dir() {
    property(Layout::Dir);
}

// frob:tests crates/frob-ledger/src/index.rs::Index.patch
#[test]
fn incremental_equals_rebuild_branch() {
    property(Layout::Branch);
}

fn counting(layout: Layout) {
    let (dir, ledger) = fixture(layout);
    let id = ledger
        .new_ticket(NewTicket::new("Counted", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    ledger.list(&ListFilter::default()).expect("list");
    let base = ledger.index_rebuilds();
    // A pm-style write and a foreign ticket write: neither may rebuild.
    let path = match layout {
        Layout::Dir => "tickets/_cycles/C1/cycle.md",
        Layout::Branch => "_cycles/C1/cycle.md",
    };
    raw_commit(&ledger, &[(path.to_owned(), Some(b"x\n".to_vec()))], "pm");
    let other = second_handle(dir.path(), layout);
    let second = other
        .new_ticket(NewTicket::new("Foreign", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    other
        .update(
            id,
            &Patch {
                sets: vec![("priority".into(), Some(toml::Value::String("high".into())))],
                ..Patch::default()
            },
        )
        .expect("update");
    let listed = ledger.list(&ListFilter::default()).expect("list");
    assert_eq!(
        ledger.index_rebuilds(),
        base,
        "reads after foreign writes must not rebuild"
    );
    assert_eq!(listed.len(), 2);
    assert!(
        listed
            .iter()
            .any(|s| s.id == second && s.category == Category::Todo)
    );
}

// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.index_rebuilds
#[test]
fn a_read_after_pm_and_foreign_writes_does_no_full_rebuild_dir() {
    counting(Layout::Dir);
}

// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.index_rebuilds
#[test]
fn a_read_after_pm_and_foreign_writes_does_no_full_rebuild_branch() {
    counting(Layout::Branch);
}
