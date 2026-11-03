//! At 50k tickets a read after a foreign write patches the index; it never rebuilds it.
// frob:ticket 01M5CW063S30GRFG41DERAA0Q8

use std::time::{Duration, Instant};

use frob_ledger::index::ListFilter;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Layout, Ledger, LedgerConfig, RefMode, TicketId};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";
const TICKETS: usize = 50_000;
/// Generous wall-clock budget for one incremental read at scale.
const READ_BUDGET: Duration = Duration::from_secs(5);

fn open(dir: &std::path::Path) -> Ledger {
    let cfg = LedgerConfig {
        mode: RefMode::Trunk,
        ..LedgerConfig::default()
    };
    Ledger::open(
        Repo::discover(dir).expect("discover"),
        cfg,
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .with_layout(Layout::Dir)
}

/// A repository on `main` holding one root commit.
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
    let ledger = open(dir.path());
    ledger
        .repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new("README.md").expect("path"),
                Some(b"hello\n".to_vec()),
            )],
            "root",
            &CommitOptions::default(),
        )
        .expect("root commit");
    (dir, ledger)
}

/// The `n`th copy of the model ticket document under a fresh id, as a commit change.
fn copy_doc(text: &str, model: TicketId, n: usize) -> (RelPath, Option<Vec<u8>>) {
    let id = TicketId::mint();
    let doc = text
        .replace(&model.to_string(), &id.to_string())
        .replace("Model", &format!("Ticket {n}"));
    (
        RelPath::new(format!("tickets/{id}/ticket.md")).expect("path"),
        Some(doc.into_bytes()),
    )
}

/// `TICKETS` copies of the model document, each under a fresh id.
fn copy_docs(text: &str, model: TicketId) -> Vec<(RelPath, Option<Vec<u8>>)> {
    (0..TICKETS).map(|n| copy_doc(text, model, n)).collect()
}

/// Commit `TICKETS` copies of a real ticket document, each under a fresh id, in one commit.
fn seed(ledger: &Ledger) {
    let model = ledger
        .new_ticket(NewTicket::new("Model", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    let path = format!("tickets/{model}/ticket.md");
    let text = String::from_utf8(
        ledger
            .repo()
            .read_blob_at(MAIN, &path)
            .expect("read")
            .expect("model doc"),
    )
    .expect("utf8");
    let changes = copy_docs(&text, model);
    ledger
        .repo()
        .commit_paths(MAIN, &changes, "seed", &CommitOptions::default())
        .expect("seed commit");
}

/// A second handle creates a ticket, returning its id.
fn foreign_write(root: &std::path::Path) -> TicketId {
    open(root)
        .new_ticket(NewTicket::new("Foreign", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id
}

/// List every ticket, returning the summaries and how long the read took.
fn timed_list(ledger: &Ledger) -> (Vec<frob_ledger::index::Summary>, std::time::Duration) {
    let start = Instant::now();
    let all = ledger.list(&ListFilter::default()).expect("list");
    (all, start.elapsed())
}

// frob:tests crates/frob-ledger/src/index.rs::Index.patch
// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.index_rebuilds
#[test]
#[ignore = "perf: seeds 50k tickets; run with nextest --run-ignored only"]
fn a_read_after_a_foreign_write_at_50k_tickets_patches_without_rebuilding() {
    let (dir, ledger) = fixture();
    seed(&ledger);
    let first = ledger.list(&ListFilter::default()).expect("list");
    assert!(first.len() > TICKETS, "seeded tickets are indexed");
    let base = ledger.index_rebuilds();

    let fresh = foreign_write(dir.path());
    let (after, took) = timed_list(&ledger);
    assert_eq!(
        ledger.index_rebuilds(),
        base,
        "a read after one foreign write must not rebuild the index"
    );
    assert_eq!(after.len(), first.len() + 1);
    assert!(after.iter().any(|s| s.id == fresh));
    assert!(took < READ_BUDGET, "incremental read took {took:?}");
}
