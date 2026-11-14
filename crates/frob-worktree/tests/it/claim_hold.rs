//! Hold, resume and reclaim records written through `Workspace` and read back (system git required).
// frob:ticket 01M5E0F8MC9XT2PCCB9XG6E8X3

use std::sync::Arc;

use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::claim_window::ClaimWindows;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_worktree::{Workspace, WorktreeConfig, WorktreeError};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_time::{Clock, Day};

const DAY: i64 = 86_400;

// frob:tests crates/frob-worktree/src/claim_hold.rs::Workspace.hold_claim
// frob:tests crates/frob-worktree/src/claim_hold.rs::Workspace.resume_claim
// frob:tests crates/frob-worktree/src/claim_hold.rs::Workspace.record_reclaim
// frob:tests crates/frob-worktree/src/claim_hold.rs::Workspace.claim_record
#[test]
fn hold_resume_and_reclaim_round_trip() {
    let tmp = tempfile::tempdir().expect("tmp");
    let root = tmp.path().join("repo");
    std::fs::create_dir(&root).expect("dir");
    let repo = Repo::init(&root).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("cfg");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("cfg");
    drop(repo);
    let repo = Repo::discover(&root).expect("repo");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("README.md").expect("rel"),
            Some(b"hi\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("commit");
    let clock = Arc::new(gob_time::SystemClock);
    let ledger = Ledger::open(repo.clone(), LedgerConfig::default(), clock.clone());
    let leases = LeaseStore::open(&repo, LeaseConfig::default(), clock).expect("leases");
    let wt = WorktreeConfig::load(&root).expect("config");
    let ws = Workspace {
        ledger: &ledger,
        leases: &leases,
        config: &wt,
    };
    let id = ledger
        .new_ticket(NewTicket::new("Hold me", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id
        .to_string();
    let now = gob_time::SystemClock.now().unix();
    let windows = ClaimWindows::default();
    assert!(!ws.claim_record(&id).expect("record").held_at(now));

    let end = Day::from_unix(now + 3 * DAY);
    let hold = ws
        .hold_claim(&id, end, "on leave", now, 0, &windows)
        .expect("hold");
    let rec = ws.claim_record(&id).expect("record");
    assert!(rec.held_at(now + 1));
    assert_eq!(
        rec.hold.as_ref().map(|h| h.reason.as_str()),
        Some("on leave")
    );
    assert!((rec.hold.expect("hold").until - hold.until).abs() <= 5);

    let bad = ws
        .hold_claim(&id, end, " ", now, 0, &windows)
        .expect_err("empty reason");
    assert!(matches!(bad, WorktreeError::Usage(_)), "{bad}");

    assert!(ws.resume_claim(&id, now + 1).expect("resume"));
    assert!(!ws.claim_record(&id).expect("record").held_at(now + 2));
    assert!(!ws.resume_claim(&id, now + 2).expect("resume again"));

    assert_eq!(ws.claim_record(&id).expect("record").reclaimed_at, None);
    ws.record_reclaim(&id, "ann").expect("reclaim");
    assert!(ws.claim_record(&id).expect("record").reclaimed_at.is_some());
}
