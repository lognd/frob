//! Spawn counting: per-runner, process-global and per-thread.

use std::cell::Cell;
use std::sync::atomic::{AtomicU64, Ordering};

static GLOBAL: AtomicU64 = AtomicU64::new(0);

thread_local! {
    static THREAD: Cell<u64> = const { Cell::new(0) };
}

/// Snapshot of a spawn counter, comparable across time.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct SpawnCount(pub u64);

impl SpawnCount {
    /// Snapshot of the process-global spawn counter.
    pub fn global() -> Self {
        Self(GLOBAL.load(Ordering::Relaxed))
    }

    /// Spawns recorded since `earlier`.
    pub fn since(self, earlier: SpawnCount) -> u64 {
        self.0.saturating_sub(earlier.0)
    }
}

/// Record one spawn in the global, thread and given per-runner counters.
pub(crate) fn record(runner: &AtomicU64) {
    runner.fetch_add(1, Ordering::Relaxed);
    GLOBAL.fetch_add(1, Ordering::Relaxed);
    THREAD.with(|c| c.set(c.get() + 1));
}

/// Run `f` and panic unless it spawned exactly `expected` children.
///
/// Counts spawns made by the calling thread only, so concurrently running
/// tests do not disturb each other.
///
/// # Panics
/// Panics when the observed spawn count differs from `expected`.
pub fn assert_spawns<T>(expected: u64, f: impl FnOnce() -> T) -> T {
    let before = THREAD.with(Cell::get);
    let out = f();
    let spawned = THREAD.with(Cell::get) - before;
    assert_eq!(spawned, expected, "unexpected spawn count");
    out
}
