//! The land lock: one `flock` file under the common git dir, with a sidecar naming the holder.

use std::fs::{File, OpenOptions, TryLockError};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use gob_diagnostics::{Refusal, RefusalClass};

use crate::error::LandError;

/// How often a contended lock is retried while waiting.
const POLL: Duration = Duration::from_millis(25);

/// Stable code of the refusal when the lock is busy.
pub const CODE_LOCKED: &str = "E-LAND-LOCKED";

/// The held land lock; released (and its sidecar removed) on drop.
#[derive(Debug)]
pub struct LandLock {
    _file: File,
    sidecar: PathBuf,
}

impl LandLock {
    /// Path of the lock file below `common_dir`.
    pub fn path(common_dir: &Path) -> PathBuf {
        common_dir.join("frob").join("land.lock")
    }

    /// Take the lock, waiting up to `wait` for another land to finish.
    ///
    /// `holder` is written to `land.lock.holder` so a refused caller can name
    /// who has it.
    ///
    /// # Errors
    ///
    /// `E-LAND-LOCKED` (retryable) when the wait expires; I/O failures otherwise.
    pub fn acquire(common_dir: &Path, wait: Duration, holder: &str) -> Result<Self, LandError> {
        let path = Self::path(common_dir);
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir)
                .map_err(|e| LandError::io(format!("creating {}", dir.display()), e))?;
        }
        let sidecar = path.with_extension("lock.holder");
        let file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .open(&path)
            .map_err(|e| LandError::io(format!("opening {}", path.display()), e))?;
        let start = Instant::now();
        loop {
            match file.try_lock() {
                Ok(()) => break,
                Err(TryLockError::WouldBlock) => {
                    if start.elapsed() >= wait {
                        let who = std::fs::read_to_string(&sidecar)
                            .map_or_else(|_| "another land".to_owned(), |s| s.trim().to_owned());
                        tracing::warn!(lock = %path.display(), holder = %who, "land lock is held");
                        return Err(LandError::Refused(
                            Refusal::new(
                                CODE_LOCKED,
                                RefusalClass::GuardRetryByWaiting,
                                format!("the land lock is held by {who}"),
                            )
                            .with_remedy("rerun with --wait <secs> to wait for the lock"),
                        ));
                    }
                    std::thread::sleep(POLL);
                }
                Err(TryLockError::Error(e)) => {
                    return Err(LandError::io(format!("locking {}", path.display()), e));
                }
            }
        }
        std::fs::write(&sidecar, format!("{holder}\n"))
            .map_err(|e| LandError::io(format!("writing {}", sidecar.display()), e))?;
        tracing::info!(lock = %path.display(), holder, "land lock taken");
        Ok(Self {
            _file: file,
            sidecar,
        })
    }
}

impl Drop for LandLock {
    fn drop(&mut self) {
        if let Err(e) = std::fs::remove_file(&self.sidecar) {
            tracing::debug!(error = %e, "land lock sidecar not removed");
        }
        tracing::info!("land lock released");
    }
}
