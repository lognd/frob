//! `LeaseStore::rescope_waiting`: bounded waiting for an overlapping lease to go away.
// frob:ticket 01M4HW9J243ZJRMVYW51K18GCM

use std::path::PathBuf;
use std::time::Duration;

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

/// Release `ticket` from a second store over `root` after a short delay, on its own thread.
fn release_later(root: PathBuf, ticket: TicketId) -> std::thread::JoinHandle<()> {
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(700));
        store_in(&root, LeaseConfig::default())
            .release(ticket, None)
            .expect("release");
    })
}

/// Rescope `a` (waiting on the lease `releaser` drops); the lease and the reported holders.
fn rescope_then_join(
    store: &LeaseStore,
    a: TicketId,
    releaser: std::thread::JoinHandle<()>,
) -> (frob_lease::Lease, Vec<String>) {
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
    (lease, reports)
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
    let releaser = release_later(dir.path().to_path_buf(), b);
    let (lease, reports) = rescope_then_join(&store, a, releaser);
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
    let lease = store
        .rescope_waiting(
            a,
            &holder("alice"),
            &scope(&["x/**", "y/f.rs"]),
            store.config(),
            Duration::from_secs(30),
            |_| {},
        )
        .expect("bob's lease expired");
    assert_eq!(lease.scope, scope(&["x/**", "y/f.rs"]));
}

// frob:tests crates/frob-lease/src/model.rs::Waiter.is_live
#[test]
fn a_waiter_is_live_until_its_heartbeat_ttl_passes() {
    use frob_lease::Waiter;
    use gob_time::Stamp;
    let w = Waiter {
        ticket: TicketId::mint(),
        holder: holder("a"),
        scope: scope(&["x/**"]),
        enqueued_at: Stamp::from_unix(100),
        renewed_at: Stamp::from_unix(100),
        ttl_secs: 10,
    };
    assert!(Waiter::is_live(&w, Stamp::from_unix(105)));
    assert!(!Waiter::is_live(&w, Stamp::from_unix(110)));
}

// frob:tests crates/frob-lease/src/unmatched.rs::ScopeMiss.message
#[test]
fn a_scope_miss_message_names_the_glob_and_any_suggestion() {
    use frob_lease::unmatched::ScopeMiss;
    let miss = ScopeMiss {
        glob: "src/lib.rss".to_owned(),
        suggestions: vec!["src/lib.rs".to_owned()],
    };
    let text = ScopeMiss::message(&miss);
    assert!(text.contains("src/lib.rss"), "{text}");
    assert!(text.contains("did you mean `src/lib.rs`"), "{text}");
    let bare = ScopeMiss::message(&ScopeMiss {
        glob: "nothing/**".to_owned(),
        suggestions: vec![],
    });
    assert!(!bare.contains("did you mean"), "{bare}");
}

// frob:tests crates/frob-lease/src/fragment_kind.rs::FragmentKind.title
#[test]
fn fragment_kind_titles_are_capitalised_headings() {
    use frob_lease::FragmentKind;
    assert_eq!(FragmentKind::title(FragmentKind::Added), "Added");
    assert_eq!(FragmentKind::title(FragmentKind::Security), "Security");
}
