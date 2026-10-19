//! The per-worktree guard against stacked full checks: one live `frob check` per checkout.
//!
//! Stacked `frob check --ticket` runs in one worktree starve the shared host, so a full run takes
//! `.frob/check.lock` (JSON: holder pid, start time, argv). A second run while the holder is alive
//! is refused naming all three; a dead holder's lock is reclaimed. `--allow-concurrent` skips the
//! lock and records the override in `.frob/check-overrides.log`.

use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// Lock file name under `<root>/.frob/`.
const LOCK_FILE: &str = "check.lock";
/// Append-only record of `--allow-concurrent` overrides under `<root>/.frob/`.
const OVERRIDE_LOG: &str = "check-overrides.log";
/// Attempts to claim a lock whose stale holder another run may be reclaiming at the same moment.
const CLAIM_ATTEMPTS: usize = 3;

/// Who holds the check lock, as written to the lock file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LockHolder {
    /// Process id of the holder.
    pub pid: u32,
    /// Unix seconds when the holder took the lock.
    pub started: u64,
    /// The holder's command line.
    pub argv: Vec<String>,
}

/// Why a full check could not take the worktree lock.
#[derive(Debug, thiserror::Error)]
pub enum LockError {
    /// Another live full check holds the lock.
    #[error(
        "another full `frob check` is already running in this worktree (pid {}, started at unix {}, argv: {})",
        .0.pid, .0.started, .0.argv.join(" ")
    )]
    Held(LockHolder),
    /// The lock file could not be created or read.
    #[error("cannot take the check lock {path:?}: {source}")]
    Io {
        /// The lock file.
        path: PathBuf,
        /// The underlying failure.
        source: std::io::Error,
    },
}

/// Holds `.frob/check.lock` until dropped; `None`-like (no file) when the override skipped it.
#[derive(Debug)]
pub struct CheckLock {
    path: Option<PathBuf>,
    pid: u32,
}

impl Drop for CheckLock {
    fn drop(&mut self) {
        if let Some(path) = &self.path {
            let ours = read_holder(path).is_some_and(|h| h.pid == self.pid);
            if ours {
                let _ = std::fs::remove_file(path);
                tracing::debug!(lock = ?path, "released the check lock");
            }
        }
    }
}

/// True when process `pid` exists (Linux `/proc`; elsewhere assumed alive, like the land lock).
#[must_use]
pub fn pid_alive(pid: u32) -> bool {
    if cfg!(target_os = "linux") {
        Path::new(&format!("/proc/{pid}")).exists()
    } else {
        true
    }
}

#[allow(
    clippy::disallowed_methods,
    reason = "the lock file is run state under .frob/, not walked content"
)]
fn read_holder(path: &Path) -> Option<LockHolder> {
    let mut text = String::new();
    std::fs::File::open(path)
        .ok()?
        .read_to_string(&mut text)
        .ok()?;
    serde_json::from_str(&text).ok()
}

/// Take the full-check lock for `root` as process `pid`; refuses within one read when a live holder exists.
///
/// With `allow_concurrent` no lock is taken and the override is appended to the run log.
///
/// # Errors
///
/// [`LockError::Held`] when a live process holds the lock, [`LockError::Io`] on filesystem failure.
pub fn acquire(
    root: &Path,
    pid: u32,
    argv: &[String],
    allow_concurrent: bool,
    clock: &dyn gob_time::Clock,
) -> Result<CheckLock, LockError> {
    let dir = root.join(".frob");
    let path = dir.join(LOCK_FILE);
    let io = |source| LockError::Io {
        path: path.clone(),
        source,
    };
    std::fs::create_dir_all(&dir).map_err(io)?;
    let me = LockHolder {
        pid,
        started: u64::try_from(clock.now().unix()).unwrap_or(0),
        argv: argv.to_vec(),
    };
    if allow_concurrent {
        let line = format!(
            "{} pid {} allow-concurrent: {}\n",
            me.started,
            pid,
            argv.join(" ")
        );
        let logged = OpenOptions::new()
            .create(true)
            .append(true)
            .open(dir.join(OVERRIDE_LOG))
            .and_then(|mut f| f.write_all(line.as_bytes()));
        if let Err(e) = logged {
            tracing::warn!(error = %e, "could not record the --allow-concurrent override");
        }
        tracing::warn!(
            pid,
            "--allow-concurrent: running a full check without the worktree lock"
        );
        return Ok(CheckLock { path: None, pid });
    }
    let body = serde_json::to_vec(&me).expect("LockHolder serializes");
    for _ in 0..CLAIM_ATTEMPTS {
        match OpenOptions::new().write(true).create_new(true).open(&path) {
            Ok(mut f) => {
                f.write_all(&body).map_err(io)?;
                tracing::debug!(lock = ?path, pid, "took the check lock");
                return Ok(CheckLock {
                    path: Some(path),
                    pid,
                });
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => match read_holder(&path) {
                Some(h) if pid_alive(h.pid) => return Err(LockError::Held(h)),
                stale => {
                    tracing::warn!(holder = ?stale, "reclaiming a stale check lock");
                    let _ = std::fs::remove_file(&path);
                }
            },
            Err(e) => return Err(io(e)),
        }
    }
    Err(io(std::io::Error::other(
        "lock contended by concurrent reclaimers",
    )))
}

#[cfg(test)]
mod tests {
    use super::{LOCK_FILE, LockError, acquire};
    use std::io::Read as _;

    fn clock() -> gob_time::FixedClock {
        gob_time::FixedClock::new(gob_time::Stamp::from_unix(1_000_000))
    }

    fn argv() -> Vec<String> {
        vec!["frob".into(), "check".into()]
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[test]
    fn live_holder_refuses_second_run_naming_pid() {
        let dir = tempfile::tempdir().unwrap();
        let first = acquire(dir.path(), std::process::id(), &argv(), false, &clock()).unwrap();
        let err = acquire(dir.path(), 4242, &argv(), false, &clock()).unwrap_err();
        let LockError::Held(h) = &err else {
            panic!("expected Held, got {err}");
        };
        assert_eq!(h.pid, std::process::id());
        assert!(err.to_string().contains(&std::process::id().to_string()));
        assert!(err.to_string().contains("frob check"));
        drop(first);
        assert!(!dir.path().join(".frob").join(LOCK_FILE).exists());
        acquire(dir.path(), 4242, &argv(), false, &clock()).unwrap();
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[cfg(target_os = "linux")]
    #[test]
    fn stale_lock_from_dead_pid_is_reclaimed() {
        let dir = tempfile::tempdir().unwrap();
        let dead = u32::MAX - 1;
        let stale = acquire(dir.path(), dead, &argv(), false, &clock()).unwrap();
        std::mem::forget(stale);
        let lock = acquire(dir.path(), std::process::id(), &argv(), false, &clock()).unwrap();
        drop(lock);
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[allow(
        clippy::disallowed_methods,
        reason = "test reads run state, not walked content"
    )]
    #[test]
    fn allow_concurrent_skips_lock_and_logs() {
        let dir = tempfile::tempdir().unwrap();
        let _held = acquire(dir.path(), std::process::id(), &argv(), false, &clock()).unwrap();
        let _second = acquire(dir.path(), 4242, &argv(), true, &clock()).unwrap();
        let mut log = String::new();
        std::fs::File::open(dir.path().join(".frob/check-overrides.log"))
            .unwrap()
            .read_to_string(&mut log)
            .unwrap();
        assert!(log.contains("allow-concurrent"));
    }
}
