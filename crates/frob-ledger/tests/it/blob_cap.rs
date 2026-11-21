//! Ledger blob reads refuse a blob over the size cap before loading it. (folded into the one `it` test binary)
// frob:ticket 01M7XXCT68PZ5DA86TY2TYMRJR

use frob_ledger::ledger::MAX_BLOB_BYTES;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, LedgerError, TicketId};
use gob_git::{CommitOptions, GitError, RelPath, Repo};

fn fresh() -> Ledger {
    let dir = tempfile::tempdir().expect("tempdir").keep();
    let repo = Repo::init(&dir).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(&dir).expect("discover");
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
    Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
}

fn ticket(ledger: &Ledger) -> TicketId {
    ledger
        .new_ticket(NewTicket::new("Capped", TicketType::Task))
        .expect("ticket")
        .ticket
        .front
        .id
}

/// Replace the ticket file with `len` bytes of body-ish padding and return the ledger tip.
fn pad_ticket(ledger: &Ledger, id: TicketId, len: u64) -> String {
    let cur = ledger
        .repo()
        .read_blob_at(
            &ledger.tip_hex().expect("tip").expect("some"),
            &format!("tickets/{id}/ticket.md"),
        )
        .expect("read")
        .expect("present");
    let mut bytes = cur;
    let want = usize::try_from(len).expect("len");
    bytes.resize(want.max(bytes.len()), b'x');
    ledger
        .repo()
        .commit_paths(
            "refs/heads/main",
            &[(
                RelPath::new(format!("tickets/{id}/ticket.md")).expect("path"),
                Some(bytes),
            )],
            "pad",
            &CommitOptions::default(),
        )
        .expect("commit");
    ledger.tip_hex().expect("tip").expect("some")
}

/// A ticket blob over the cap is refused with a typed error naming the cap, never buffered.
// frob:ticket 01M7XXCT68PZ5DA86TY2TYMRJR
// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.read_ticket_at
#[test]
fn a_ticket_blob_over_the_cap_is_refused_naming_the_cap() {
    let ledger = fresh();
    let id = ticket(&ledger);
    let tip = pad_ticket(&ledger, id, MAX_BLOB_BYTES + 1);
    let err = ledger.read_ticket_at(&tip, id).expect_err("over cap");
    match &err {
        LedgerError::Git(GitError::BlobTooLarge { size, cap, .. }) => {
            assert_eq!(*cap, MAX_BLOB_BYTES);
            assert_eq!(*size, MAX_BLOB_BYTES + 1);
        }
        other => panic!("expected BlobTooLarge, got {other:?}"),
    }
    assert!(err.to_string().contains(&MAX_BLOB_BYTES.to_string()));
}

/// A ticket blob under the cap reads as before.
// frob:ticket 01M7XXCT68PZ5DA86TY2TYMRJR
// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.read_ticket_at
#[test]
fn a_ticket_blob_under_the_cap_still_reads() {
    let ledger = fresh();
    let id = ticket(&ledger);
    let tip = ledger.tip_hex().expect("tip").expect("some");
    assert!(ledger.read_ticket_at(&tip, id).expect("read").is_some());
}
