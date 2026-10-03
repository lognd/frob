//! Lease store behavior: locking, overlap, TTL, shared files, steal, contention, SCOPE001, verbs.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Barrier};

use frob_lease::{Holder, LeaseConfig, LeaseError, LeaseGuard, LeaseStore, scope001};
use frob_ledger::TicketId;
use frob_ledger::guards::LeaseCheck;
use frob_ledger::index::Summary;
use frob_ledger::model::{Category, Priority, Stamp, TicketType};
use gob_git::RelPath;

fn holder(actor: &str) -> Holder {
    Holder {
        actor: actor.to_owned(),
        worktree: PathBuf::from(format!("/wt/{actor}")),
    }
}

fn scope(globs: &[&str]) -> Vec<String> {
    globs.iter().map(|s| (*s).to_owned()).collect()
}

fn cfg(shared: &[&str]) -> LeaseConfig {
    LeaseConfig {
        shared_files: scope(shared),
        ..LeaseConfig::default()
    }
}

fn store_in(dir: &Path, cfg: LeaseConfig) -> LeaseStore {
    LeaseStore::open_at(&dir.join(".git"), dir.to_path_buf(), cfg).expect("store")
}

fn write(dir: &Path, rel: &str) {
    let p = dir.join(rel);
    std::fs::create_dir_all(p.parent().expect("parent")).expect("mkdir");
    std::fs::write(p, "x\n").expect("write");
}

#[test]
fn concurrent_overlapping_globs_grant_exactly_one() {
    for round in 0..10 {
        let dir = tempfile::tempdir().expect("tempdir");
        let barrier = Arc::new(Barrier::new(2));
        let handles: Vec<_> = ["alice", "bob"]
            .into_iter()
            .map(|who| {
                let root = dir.path().to_path_buf();
                let barrier = Arc::clone(&barrier);
                std::thread::spawn(move || {
                    let store = store_in(&root, LeaseConfig::default());
                    barrier.wait();
                    store.acquire(TicketId::mint(), &holder(who), &scope(&["src/newmod/**"]))
                })
            })
            .collect();
        let results: Vec<_> = handles
            .into_iter()
            .map(|h| h.join().expect("thread"))
            .collect();
        let ok = results.iter().filter(|r| r.is_ok()).count();
        let held = results
            .iter()
            .filter(|r| matches!(r, Err(LeaseError::Held { .. })))
            .count();
        assert_eq!((ok, held), (1, 1), "round {round}: {results:?}");
        assert_eq!(
            store_in(dir.path(), LeaseConfig::default())
                .list()
                .expect("list")
                .len(),
            1
        );
    }
}

#[test]
fn held_error_maps_to_retryable_refusal_naming_holder() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    store
        .acquire(TicketId::mint(), &holder("alice"), &scope(&["src/**"]))
        .expect("first");
    let err = store
        .acquire(TicketId::mint(), &holder("bob"), &scope(&["src/a.rs"]))
        .expect_err("overlap");
    let refusal = err.to_refusal().expect("refusal");
    assert_eq!(refusal.code, "E-LEASE-HELD");
    assert!(refusal.class.retryable());
    assert!(refusal.message.contains("alice"), "{}", refusal.message);
}

#[test]
fn same_holder_reacquire_is_already() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    let first = store
        .acquire(t, &holder("alice"), &scope(&["src/**"]))
        .expect("first");
    assert!(!first.already);
    let again = store
        .acquire(t, &holder("alice"), &scope(&["src/**"]))
        .expect("again");
    assert!(again.already);
    assert_eq!(again.lease.acquired_at, first.lease.acquired_at);
    let other = store.acquire(t, &holder("bob"), &scope(&["src/**"]));
    assert!(matches!(other, Err(LeaseError::Held { .. })));
}

static NOW: AtomicI64 = AtomicI64::new(1_800_000_000);

fn fake_now() -> Stamp {
    Stamp::from_unix(NOW.load(Ordering::SeqCst))
}

#[test]
fn ttl_expiry_frees_and_prunes() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(
        dir.path(),
        LeaseConfig {
            ttl_secs: 100,
            ..LeaseConfig::default()
        },
    )
    .with_clock(fake_now);
    let a = TicketId::mint();
    store
        .acquire(a, &holder("alice"), &scope(&["src/**"]))
        .expect("alice");
    NOW.fetch_add(99, Ordering::SeqCst);
    assert!(
        store
            .acquire(TicketId::mint(), &holder("bob"), &scope(&["src/**"]))
            .is_err()
    );
    NOW.fetch_add(2, Ordering::SeqCst);
    let b = TicketId::mint();
    store
        .acquire(b, &holder("bob"), &scope(&["src/**"]))
        .expect("expired lease is ignored");
    let live = store.list().expect("list");
    assert_eq!(live.len(), 1);
    assert_eq!(live[0].ticket, b);
    let lease_file = dir
        .path()
        .join(".git/frob/leases")
        .join(format!("{a}.toml"));
    assert!(!lease_file.exists(), "expired lease removed lazily");
}

#[test]
fn shared_files_are_exempt() {
    let dir = tempfile::tempdir().expect("tempdir");
    let shared = store_in(dir.path(), cfg(&["Cargo.lock"]));
    shared
        .acquire(
            TicketId::mint(),
            &holder("a"),
            &scope(&["Cargo.lock", "a/**"]),
        )
        .expect("a");
    shared
        .acquire(
            TicketId::mint(),
            &holder("b"),
            &scope(&["Cargo.lock", "b/**"]),
        )
        .expect("b shares Cargo.lock");

    let dir = tempfile::tempdir().expect("tempdir");
    let strict = store_in(dir.path(), cfg(&[]));
    strict
        .acquire(
            TicketId::mint(),
            &holder("a"),
            &scope(&["Cargo.lock", "a/**"]),
        )
        .expect("a");
    assert!(matches!(
        strict.acquire(
            TicketId::mint(),
            &holder("b"),
            &scope(&["Cargo.lock", "b/**"])
        ),
        Err(LeaseError::Held { .. })
    ));
}

#[test]
fn disjoint_scopes_coexist_and_release_frees() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let (a, b) = (TicketId::mint(), TicketId::mint());
    store
        .acquire(a, &holder("a"), &scope(&["crates/x/**"]))
        .expect("a");
    store
        .acquire(b, &holder("b"), &scope(&["crates/y/**"]))
        .expect("b");
    assert!(matches!(
        store.release(a, Some("mallory")),
        Err(LeaseError::Held { .. })
    ));
    assert!(store.release(a, Some("a")).expect("release").is_some());
    assert!(store.release(a, Some("a")).expect("again").is_none());
    store
        .acquire(TicketId::mint(), &holder("c"), &scope(&["crates/x/**"]))
        .expect("freed");
}

#[test]
fn steal_records_history_and_returns_previous() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    store
        .acquire(t, &holder("alice"), &scope(&["src/**"]))
        .expect("alice");
    let stolen = store
        .steal(t, &holder("bob"), "alice crashed")
        .expect("steal");
    assert_eq!(stolen.previous, holder("alice"));
    assert_eq!(stolen.lease.holder, holder("bob"));
    assert_eq!(stolen.lease.history.len(), 1);
    assert_eq!(stolen.lease.history[0].reason, "alice crashed");
    let reread = store.list().expect("list");
    assert_eq!(reread[0].history, stolen.lease.history);
    assert!(matches!(
        store.steal(TicketId::mint(), &holder("bob"), "none"),
        Err(LeaseError::NotHeld { .. })
    ));
}

#[test]
fn renew_extends_and_wip_limit_refuses() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default()).with_holder_limit(1);
    let t = TicketId::mint();
    store
        .acquire(t, &holder("a"), &scope(&["a/**"]))
        .expect("a");
    store.renew(t, &holder("a")).expect("renew");
    assert!(matches!(
        store.renew(t, &holder("b")),
        Err(LeaseError::Held { .. })
    ));
    assert!(matches!(
        store.acquire(TicketId::mint(), &holder("a"), &scope(&["b/**"])),
        Err(LeaseError::WipLimit { .. })
    ));
}

#[test]
fn contention_ranks_shared_files() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "Cargo.lock");
    write(dir.path(), "a/x.rs");
    write(dir.path(), "b/y.rs");
    let store = store_in(dir.path(), cfg(&["Cargo.lock"]));
    let (a, b, c) = (TicketId::mint(), TicketId::mint(), TicketId::mint());
    store
        .acquire(a, &holder("a"), &scope(&["Cargo.lock", "a/**"]))
        .expect("a");
    store
        .acquire(b, &holder("b"), &scope(&["Cargo.lock", "b/**"]))
        .expect("b");
    store
        .acquire(c, &holder("c"), &scope(&["Cargo.lock", "c/**"]))
        .expect("c");
    let report = store.contention().expect("contention");
    assert_eq!(report.len(), 1);
    assert_eq!(report[0].file, "Cargo.lock");
    assert_eq!(report[0].tickets.len(), 3);
}

fn summary(id: TicketId) -> Summary {
    Summary {
        id,
        handle: "~x".to_owned(),
        title: "t".to_owned(),
        ty: TicketType::Task,
        category: Category::Todo,
        outcome: None,
        priority: Priority::Medium,
        class: frob_ledger::model::Class::Standard,
        due: None,
        points: None,
        parent: None,
        created: Stamp::from_unix(1),
        updated: Stamp::from_unix(1),
        blocked: false,
    }
}

#[test]
fn guard_hides_overlapping_tickets() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let held = TicketId::mint();
    store
        .acquire(held, &holder("a"), &scope(&["src/**"]))
        .expect("a");
    let guard = LeaseGuard::new(store).expect("guard");
    assert!(!guard.is_free(&summary(TicketId::mint()), &scope(&["src/lib.rs"])));
    assert!(guard.is_free(&summary(TicketId::mint()), &scope(&["docs/**"])));
    assert!(
        guard.is_free(&summary(held), &scope(&["src/**"])),
        "own lease never blocks"
    );
}

#[test]
fn scope001_flags_outside_paths_only() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    let lease = store
        .acquire(t, &holder("a"), &scope(&["crates/x/**"]))
        .expect("a")
        .lease;
    let paths: Vec<RelPath> = ["crates/x/src/lib.rs", "crates/y/lib.rs", "Cargo.lock"]
        .iter()
        .map(|p| RelPath::new(*p).expect("relpath"))
        .collect();
    let findings = scope001(&paths, &lease, &scope(&["Cargo.lock"]));
    assert_eq!(findings.len(), 1);
    assert_eq!(findings[0].rule.as_str(), "SCOPE001");
    assert!(findings[0].message.contains("crates/y/lib.rs"));
}

#[test]
fn verbs_list_leases_and_contention() {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("init");
    let (store, _) = frob_lease::open_store(dir.path(), LeaseConfig::default()).expect("open");
    store
        .acquire(TicketId::mint(), &holder("a"), &scope(&["src/**"]))
        .expect("a");
    let cli = frob_lease::register(gob_cli::Cli::new("frob", "0.0.0"));
    let (code, out, err) = gob_cli::run_for_test(&cli, &["lease", "list"], dir.path());
    assert_eq!(code, 0, "{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(
        v["data"]["leases"].as_array().map(Vec::len),
        Some(1),
        "{out}"
    );
    let (code, out, err) = gob_cli::run_for_test(&cli, &["ticket", "contention"], dir.path());
    assert_eq!(code, 0, "{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(
        v["data"]["files"].as_array().map(Vec::len),
        Some(0),
        "{out}"
    );
}

#[test]
fn rescope_widens_the_lease_file_and_scope001_stops_firing() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    store
        .acquire(t, &holder("a"), &scope(&["crates/x/**"]))
        .expect("a");
    let paths = [RelPath::new("crates/y/lib.rs").expect("relpath")];
    let before = store.live_lease(t).expect("read").expect("lease");
    assert_eq!(scope001(&paths, &before, &[]).len(), 1);
    let wider = scope(&["crates/x/**", "crates/y/**"]);
    let lease = store
        .rescope(t, &holder("a"), &wider, store.config())
        .expect("rescope");
    assert_eq!(lease.scope, wider);
    let reread = store_in(dir.path(), LeaseConfig::default())
        .live_lease(t)
        .expect("read")
        .expect("lease");
    assert_eq!(reread.scope, wider);
    assert!(
        reread
            .history
            .last()
            .expect("history")
            .reason
            .starts_with("rescope:")
    );
    assert!(scope001(&paths, &reread, &[]).is_empty());
}

#[test]
fn rescope_into_another_live_lease_is_refused_and_leaves_the_lease() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let (a, b) = (TicketId::mint(), TicketId::mint());
    store
        .acquire(a, &holder("alice"), &scope(&["crates/x/**"]))
        .expect("a");
    store
        .acquire(b, &holder("bob"), &scope(&["crates/y/**"]))
        .expect("b");
    let err = store
        .rescope(
            a,
            &holder("alice"),
            &scope(&["crates/x/**", "crates/y/lib.rs"]),
            store.config(),
        )
        .expect_err("overlap");
    match err {
        LeaseError::Held {
            holder: h, ticket, ..
        } => {
            assert_eq!(h, holder("bob"));
            assert_eq!(ticket, b);
        }
        other => panic!("{other:?}"),
    }
    let kept = store.live_lease(a).expect("read").expect("lease");
    assert_eq!(kept.scope, scope(&["crates/x/**"]));
}

#[test]
fn rescope_narrows_is_idempotent_and_refuses_non_holders() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    store
        .acquire(t, &holder("alice"), &scope(&["a/**", "b/**"]))
        .expect("a");
    let narrow = scope(&["a/**"]);
    let lease = store
        .rescope(t, &holder("alice"), &narrow, store.config())
        .expect("narrow");
    assert_eq!(lease.scope, narrow);
    let again = store
        .rescope(t, &holder("alice"), &narrow, store.config())
        .expect("again");
    assert_eq!(again.history.len(), lease.history.len());
    assert!(matches!(
        store.rescope(
            t,
            &holder("mallory"),
            &scope(&["a/**", "z/**"]),
            store.config()
        ),
        Err(LeaseError::Held { .. })
    ));
    assert!(matches!(
        store.rescope(TicketId::mint(), &holder("alice"), &narrow, store.config()),
        Err(LeaseError::NotHeld { .. })
    ));
}

// frob:tests crates/frob-lease/src/lib.rs::open_store
#[test]
fn open_store_uses_the_callers_config_not_the_file() {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("init");
    std::fs::write(dir.path().join("frob.toml"), "[lease]\nshared_files = []\n").expect("toml");
    let (store, _) = frob_lease::open_store(dir.path(), cfg(&["Cargo.lock"])).expect("open");
    store
        .acquire(
            TicketId::mint(),
            &holder("a"),
            &scope(&["a/**", "Cargo.lock"]),
        )
        .expect("a");
    store
        .acquire(
            TicketId::mint(),
            &holder("b"),
            &scope(&["b/**", "Cargo.lock"]),
        )
        .expect("b shares Cargo.lock");
    assert!(store.contention().expect("contention").is_empty());
}

// frob:tests crates/frob-lease/src/overlap.rs::scopes_overlap
#[test]
fn two_tickets_each_leasing_their_own_fragment_do_not_conflict() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let (a, b) = (TicketId::mint(), TicketId::mint());
    let frag = |t: TicketId| format!("changelog.d/{t}.added.md");
    write(dir.path(), &frag(a));
    write(dir.path(), &frag(b));
    store
        .acquire(a, &holder("alice"), &scope(&["crates/x/**", &frag(a)]))
        .expect("a");
    store
        .acquire(
            b,
            &holder("bob"),
            &scope(&["crates/y/**", &frag(b), "changelog.d/**"]),
        )
        .expect("b: a legacy changelog.d/** scope is ignored, not an error");
    let c = TicketId::mint();
    store
        .acquire(
            c,
            &holder("carol"),
            &scope(&["changelog.d/*.added.md", &frag(c)]),
        )
        .expect("c: foreign-covering globs never contend");
}

// frob:tests crates/frob-lease/src/store.rs::rescope
#[test]
fn widening_to_a_glob_covering_other_fragments_is_refused_with_a_teaching_message() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    store
        .acquire(t, &holder("a"), &scope(&["crates/x/**"]))
        .expect("a");
    for glob in [
        "changelog.d/**",
        "changelog.d/*",
        "changelog.d/",
        "changelog.d/*.added.md",
    ] {
        let err = store
            .rescope(
                t,
                &holder("a"),
                &scope(&["crates/x/**", glob]),
                store.config(),
            )
            .expect_err(glob);
        assert!(
            matches!(err, LeaseError::FragmentGlob { .. }),
            "{glob}: {err:?}"
        );
        let msg = err.to_string();
        assert!(
            msg.contains("own") && msg.contains("needs no lease"),
            "{msg}"
        );
        assert_eq!(
            err.to_refusal().expect("refusal").code,
            "E-LEASE-FRAGMENT-GLOB"
        );
    }
    let own = format!("changelog.d/{t}.added.md");
    store
        .rescope(
            t,
            &holder("a"),
            &scope(&["crates/x/**", &own]),
            store.config(),
        )
        .expect("the exact own fragment is fine");
    let kept = store.live_lease(t).expect("read").expect("lease");
    assert_eq!(kept.scope, scope(&["crates/x/**", &own]));
}

// frob:tests crates/frob-lease/src/rule.rs::scope001
#[test]
fn scope001_allows_the_own_fragment_only() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    let t = TicketId::mint();
    let lease = store
        .acquire(t, &holder("a"), &scope(&["crates/x/**", "changelog.d/**"]))
        .expect("legacy scope still acquires")
        .lease;
    let own = format!("changelog.d/{t}.fixed.md");
    let other = "changelog.d/01ARZ3NDEKTSV4RRFFQ69G5FAV.fixed.md";
    let paths = [
        RelPath::new(own.as_str()).expect("own"),
        RelPath::new(other).expect("other"),
        RelPath::new(format!("changelog.d/{t}.nope.md")).expect("bad"),
    ];
    let hits = scope001(&paths, &lease, &[]);
    assert_eq!(hits.len(), 2, "{hits:?}");
    assert!(hits.iter().all(|f| !f.message.starts_with(&own)));
}

// frob:ticket 01M4069VZVMHVZ15RSPZQRNCXY
// frob:tests crates/frob-lease/src/store.rs::LeaseStore.with_expedite_max
#[test]
fn the_expedite_lane_defaults_to_one_and_is_configurable() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    assert_eq!(store.expedite_max(), 1);
    assert_eq!(store.with_expedite_max(3).expedite_max(), 3);
}

// frob:tests crates/frob-lease/src/config.rs::default_shared_files
#[test]
fn unset_shared_files_default_to_the_lockfiles_and_an_explicit_empty_list_replaces_them() {
    assert!(
        LeaseConfig::default()
            .shared_files
            .contains(&"Cargo.lock".to_owned())
    );
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), LeaseConfig::default());
    store
        .acquire(
            TicketId::mint(),
            &holder("a"),
            &scope(&["a/**", "Cargo.lock"]),
        )
        .expect("a");
    store
        .acquire(
            TicketId::mint(),
            &holder("b"),
            &scope(&["b/**", "Cargo.lock"]),
        )
        .expect("b leases without E-LEASE-HELD");

    let parsed: LeaseConfig = toml::from_str("shared_files = []").expect("parse");
    assert!(parsed.shared_files.is_empty());
    let unset: LeaseConfig = toml::from_str("ttl_secs = 1").expect("parse");
    assert_eq!(
        unset.shared_files,
        frob_lease::config::default_shared_files()
    );
}

// frob:tests crates/frob-lease/src/config.rs::overlap_is_lockfiles
// frob:tests crates/frob-lease/src/config.rs::is_lockfile
#[test]
fn a_lockfile_only_overlap_names_shared_files_in_the_remedy() {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = store_in(dir.path(), cfg(&[]));
    store
        .acquire(
            TicketId::mint(),
            &holder("a"),
            &scope(&["a/**", "Cargo.lock"]),
        )
        .expect("a");
    let err = store
        .acquire(
            TicketId::mint(),
            &holder("b"),
            &scope(&["b/**", "Cargo.lock"]),
        )
        .expect_err("held");
    assert!(frob_lease::config::overlap_is_lockfiles(
        "Cargo.lock, crates/x/uv.lock"
    ));
    assert!(frob_lease::config::overlap_is_lockfiles(
        "Cargo.lock and Cargo.lock"
    ));
    assert!(!frob_lease::config::overlap_is_lockfiles(
        "Cargo.lock, src/a.rs"
    ));
    assert!(frob_lease::config::is_lockfile("sub/go.sum"));
    let cli = gob_cli::CliError::from(err);
    let gob_cli::CliError::Refusal(r) = cli else {
        panic!("not a refusal")
    };
    assert_eq!(r.code, "E-LEASE-HELD");
    let remedy = r.remedy.expect("remedy");
    assert!(remedy.contains("[lease] shared_files"), "{remedy}");

    let store = store_in(dir.path(), cfg(&[]));
    let err = store
        .acquire(TicketId::mint(), &holder("c"), &scope(&["a/x.rs"]))
        .expect_err("held on source");
    let gob_cli::CliError::Refusal(r) = gob_cli::CliError::from(err) else {
        panic!("not a refusal")
    };
    assert!(!r.remedy.expect("remedy").contains("shared_files"));
}
