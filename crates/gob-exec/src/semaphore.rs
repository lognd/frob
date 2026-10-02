//! Counting semaphore on std primitives (no async runtime).

use std::sync::{Condvar, Mutex, PoisonError};

/// Counting semaphore bounding concurrent children.
#[derive(Debug)]
pub(crate) struct Semaphore {
    permits: Mutex<usize>,
    cv: Condvar,
}

/// RAII permit; returned to the semaphore on drop.
#[derive(Debug)]
pub(crate) struct Permit<'a>(&'a Semaphore);

impl Semaphore {
    /// Create a semaphore holding `n` permits.
    pub(crate) fn new(n: usize) -> Self {
        Self {
            permits: Mutex::new(n),
            cv: Condvar::new(),
        }
    }

    /// Block until a permit is free and take it.
    pub(crate) fn acquire(&self) -> Permit<'_> {
        let mut g = self.permits.lock().unwrap_or_else(PoisonError::into_inner);
        while *g == 0 {
            g = self.cv.wait(g).unwrap_or_else(PoisonError::into_inner);
        }
        *g -= 1;
        Permit(self)
    }
}

impl Drop for Permit<'_> {
    fn drop(&mut self) {
        let mut g = self
            .0
            .permits
            .lock()
            .unwrap_or_else(PoisonError::into_inner);
        *g += 1;
        self.0.cv.notify_one();
    }
}
