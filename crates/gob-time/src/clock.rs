//! [`Clock`] and its two implementations; the only wall-clock reads in the workspace.

use std::fmt;
use std::sync::Arc;

use crate::{Day, Stamp};

/// A source of the current instant; `today` is always derived from `now`, never read separately.
pub trait Clock: fmt::Debug + Send + Sync {
    /// The current instant, whole seconds, UTC.
    fn now(&self) -> Stamp;

    /// The UTC calendar day of [`Clock::now`].
    fn today(&self) -> Day {
        Day::of(self.now())
    }
}

impl<C: Clock + ?Sized> Clock for Arc<C> {
    fn now(&self) -> Stamp {
        (**self).now()
    }
}

impl<C: Clock + ?Sized> Clock for &C {
    fn now(&self) -> Stamp {
        (**self).now()
    }
}

/// The system clock: every call reads the wall clock, so a verb should [`SystemClock::pin`] it once.
#[derive(Debug, Clone, Copy, Default)]
pub struct SystemClock;

impl SystemClock {
    /// Read the system time once and return a clock frozen at that instant: one command, one snapshot.
    pub fn pin() -> FixedClock {
        let at = SystemClock.now();
        tracing::debug!(%at, "clock pinned for the command");
        FixedClock::new(at)
    }

    /// Sub-second wall time in nanoseconds since the epoch, for entropy and unique names only; never store or compare it.
    pub fn entropy_nanos() -> u128 {
        crate::wall::unix_nanos()
    }
}

impl Clock for SystemClock {
    fn now(&self) -> Stamp {
        Stamp::from_timestamp(crate::wall::now())
    }
}

/// A clock frozen at one instant: a command's snapshot, or a test's chosen moment.
#[derive(Debug, Clone, Copy)]
pub struct FixedClock(Stamp);

impl FixedClock {
    /// A clock that always reads `at`.
    pub const fn new(at: Stamp) -> Self {
        Self(at)
    }
}

impl Clock for FixedClock {
    fn now(&self) -> Stamp {
        self.0
    }
}
