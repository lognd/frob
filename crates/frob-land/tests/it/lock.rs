//! The land lock's safety nets: progress watchdog, stale-holder takeover, status (frob:ticket 01M4W4R7PNWSRECR99078ATXCB).

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use frob_land::{LandLock, LockOptions, StallAction};

/// Options whose stall hook asserts the stage is `check` and raises the returned flag.
fn flagging_options(stall_ms: u64) -> (Arc<AtomicBool>, LockOptions) {
    let fired = Arc::new(AtomicBool::new(false));
    let mut opts = quick(stall_ms);
    opts.on_stall = raise_on_check(fired.clone());
    (fired, opts)
}

/// A stall hook that asserts the stalled stage is `check` and sets `flag`.
fn raise_on_check(flag: Arc<AtomicBool>) -> StallAction {
    StallAction::Hook(Arc::new(move |stage| {
        assert_eq!(stage, "check");
        flag.store(true, Ordering::SeqCst);
    }))
}

fn quick(stall_ms: u64) -> LockOptions {
    LockOptions {
        stall_after: Duration::from_millis(stall_ms),
        tick: Duration::from_millis(20),
        on_stall: StallAction::Hook(Arc::new(|_| {})),
        terminate: Arc::new(|_| false),
    }
}

// frob:tests crates/frob-land/src/lock.rs::LandLock
#[test]
fn a_land_blocked_forever_is_aborted_by_the_watchdog_and_frees_the_lock() {
    let dir = tempfile::tempdir().expect("tempdir");
    let (fired, opts) = flagging_options(150);
    let stuck = LandLock::acquire_with(dir.path(), Duration::ZERO, "a landing ~stuck", &opts)
        .expect("first lock");
    stuck.progress("check");
    let next = LandLock::acquire_with(
        dir.path(),
        Duration::from_secs(10),
        "b landing ~next",
        &quick(60_000),
    )
    .expect("a waiter gets the lock once the watchdog frees it");
    assert!(fired.load(Ordering::SeqCst), "watchdog fired");
    drop(stuck);
    let status = LandLock::status(dir.path(), &gob_time::SystemClock).expect("status");
    assert!(
        status.held,
        "the dropped stuck handle did not release the waiter's lock"
    );
    assert_eq!(status.record.expect("record").holder, "b landing ~next");
    drop(next);
}

// frob:tests crates/frob-land/src/lock.rs::LandLock
#[test]
fn progress_reaches_the_sidecar_and_the_status_readout() {
    let dir = tempfile::tempdir().expect("tempdir");
    let lock = LandLock::acquire_with(dir.path(), Duration::ZERO, "a landing ~x", &quick(0))
        .expect("lock");
    lock.progress("check");
    let status = LandLock::status(dir.path(), &gob_time::SystemClock).expect("status");
    assert!(status.held && status.alive);
    let record = status.record.expect("record");
    assert_eq!(
        (record.stage.as_str(), record.pid),
        ("check", std::process::id())
    );
    assert!(status.summary.contains("stage check"), "{}", status.summary);
    drop(lock);
    let free = LandLock::status(dir.path(), &gob_time::SystemClock).expect("status");
    assert!(!free.held);
}

// frob:tests crates/frob-land/src/lock.rs::LandLock
#[test]
fn a_waiter_takes_over_a_holder_whose_progress_is_stale() {
    let dir = tempfile::tempdir().expect("tempdir");
    // A holder without a watchdog (as an old binary would be), whose record says it stalled long ago.
    let held = LandLock::acquire_with(dir.path(), Duration::ZERO, "old landing ~wedged", &quick(0))
        .expect("holder");
    let sidecar = LandLock::sidecar_path(dir.path());
    let text = std::fs::read_to_string(&sidecar).expect("sidecar");
    let mut record: frob_land::HolderRecord = serde_json::from_str(text.trim()).expect("json");
    record.progress -= 3_600;
    std::fs::write(&sidecar, serde_json::to_string(&record).expect("encode")).expect("write");

    let slot = Arc::new(Mutex::new(Some(held)));
    let killed = Arc::new(Mutex::new(Vec::new()));
    let (slot2, killed2) = (slot.clone(), killed.clone());
    let mut opts = quick(1_000);
    opts.terminate = Arc::new(move |pid| {
        killed2.lock().expect("lock").push(pid);
        drop(slot2.lock().expect("lock").take());
        true
    });
    let next = LandLock::acquire_with(
        dir.path(),
        Duration::from_secs(10),
        "b landing ~next",
        &opts,
    )
    .expect("takeover");
    assert_eq!(*killed.lock().expect("lock"), vec![std::process::id()]);
    drop(next);
}

// frob:tests crates/frob-land/src/lock.rs::LandLock
#[test]
fn a_busy_lock_refusal_names_the_stage() {
    let dir = tempfile::tempdir().expect("tempdir");
    let held = LandLock::acquire_with(dir.path(), Duration::ZERO, "a landing ~x", &quick(0))
        .expect("lock");
    held.progress("check");
    let err = LandLock::acquire(dir.path(), Duration::ZERO, "b").expect_err("busy");
    let text = format!("{err:?}");
    assert!(text.contains("stage check"), "{text}");
}

// frob:tests crates/frob-land/src/lock.rs::LandLock
#[test]
fn a_worktree_style_common_dir_with_dotdots_survives_its_admin_dir_vanishing() {
    let dir = tempfile::tempdir().expect("tempdir");
    let admin = dir.path().join("worktrees").join("T1");
    std::fs::create_dir_all(&admin).expect("admin dir");
    // What `git rev-parse --git-common-dir` yields inside a linked worktree.
    let common = admin.join("..").join("..");
    let lock =
        LandLock::acquire_with(&common, Duration::ZERO, "a landing ~wt", &quick(0)).expect("lock");
    // The land removes the worktree (and its admin dir) while still holding the lock.
    std::fs::remove_dir_all(&admin).expect("remove admin");
    lock.progress("publish");
    let real = gob_exec::canonical(dir.path()).expect("canon");
    let status = LandLock::status(&real, &gob_time::SystemClock).expect("status");
    assert!(status.held);
    assert_eq!(status.record.expect("record").stage, "publish");
    assert!(LandLock::sidecar_path(&real).exists());
}
