//! `LeaseStore::rescope_waiting`: bounded waiting for an overlapping lease to go away.
// frob:ticket 01M4HW9J243ZJRMVYW51K18GCM

use std::path::PathBuf;
use std::time::{Duration, Instant};

use frob_lease::{Holder, LeaseConfig, LeaseError, LeaseStore};
use frob_ledger::TicketId;

fn holder(actor: &str) -> Holder {
    Holder {
        actor: actor.to_owned(),
        worktree: PathBuf::from(format!("/wt/{actor}")),
    }
}

fn scope(globs: &[&str]) -> Vec<String> {
    globs.iter().map(|s| (*s).to_owned()).collect()
}

fn store_in(dir: &std::path::Path, cfg: LeaseConfig) -> LeaseStore {
    LeaseStore::open_at(
        &dir.join(".git"),
        dir.to_path_buf(),
        cfg,
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .expect("store")
}

/// Two leased tickets: alice on `x/**`, bob on `y/**`.
fn two(store: &LeaseStore) -> (TicketId, TicketId) {
    let (a, b) = (TicketId::mint(), TicketId::mint());
    store
        .acquire(a, &holder("alice"), &scope(&["x/**"]))
        .expect("a");
    store
        .acquire(b, &holder("bob"), &scope(&["y/**"]))
        .expect("b");
    (a, b)
}

// frob:tests crates/frob-lease/src/wait.rs::LeaseStore.rescope_waiting
#[test]
fn a_release_mid_wait_unblocks_the_rescope_and_reports_the_holder_once() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let (a, b) = two(&store);
    let root = dir.path().to_path_buf();
    let releaser = std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(700));
        store_in(&root, LeaseConfig::default())
            .release(b, None)
            .expect("release");
    });
    let mut reports = Vec::new();
    let lease = store
        .rescope_waiting(
            a,
            &holder("alice"),
            &scope(&["x/**", "y/f.rs"]),
            store.config(),
            Duration::from_secs(30),
            |e| reports.push(e.to_string()),
        )
        .expect("rescoped after release");
    releaser.join().expect("join");
    assert_eq!(lease.scope, scope(&["x/**", "y/f.rs"]));
    assert_eq!(reports.len(), 1, "{reports:?}");
    assert!(reports[0].contains("bob"), "{reports:?}");
}

// frob:tests crates/frob-lease/src/wait.rs::LeaseStore.rescope_waiting
#[test]
fn timeout_returns_the_held_error_and_zero_wait_tries_once() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let (a, b) = two(&store);
    for wait in [Duration::ZERO, Duration::from_millis(600)] {
        let start = Instant::now();
        let err = store
            .rescope_waiting(
                a,
                &holder("alice"),
                &scope(&["x/**", "y/f.rs"]),
                store.config(),
                wait,
                |_| {},
            )
            .expect_err("still held");
        assert!(
            matches!(err, LeaseError::Held { ticket, .. } if ticket == b),
            "{err:?}"
        );
        assert!(start.elapsed() >= wait);
        assert!(start.elapsed() < wait + Duration::from_secs(3));
    }
    let kept = store.live_lease(a).expect("read").expect("lease");
    assert_eq!(kept.scope, scope(&["x/**"]));
}

// frob:tests crates/frob-lease/src/wait.rs::LeaseStore.rescope_waiting
#[test]
fn a_holder_whose_lease_expires_mid_wait_unblocks_the_rescope() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let short = store_in(
        dir.path(),
        LeaseConfig {
            ttl_secs: 1,
            ..LeaseConfig::default()
        },
    );
    let (a, b) = (TicketId::mint(), TicketId::mint());
    store
        .acquire(a, &holder("alice"), &scope(&["x/**"]))
        .expect("a");
    short
        .acquire(b, &holder("bob"), &scope(&["y/**"]))
        .expect("b");
    store
        .rescope_waiting(
            a,
            &holder("alice"),
            &scope(&["x/**", "y/f.rs"]),
            store.config(),
            Duration::from_secs(30),
            |_| {},
        )
        .expect("bob's lease expired");
}
