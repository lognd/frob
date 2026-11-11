//! The per-worktree guard against stacked full checks: one live `frob check` per checkout.
//!
//! Stacked `frob check --ticket` runs in one worktree starve the shared host, so a full run takes
//! `.frob/check.lock` (JSON: holder pid, start time, argv). A second run while the holder is alive
//! is refused naming all three; a dead holder's lock is reclaimed. `--allow-concurrent` skips the
//! lock and records the override in `.frob/check-overrides.log`.
//!
//! The post-commit hook's detached background check is *speculative* (it only warms the memo). It
//! never blocks an explicit run: an explicit `frob check` that meets a live speculative holder waits
//! for it to finish (the memo it warms makes the explicit run faster), while a speculative run that
//! meets any live holder is refused and exits.

use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use gob_exec::pid_alive;
use serde::{Deserialize, Serialize};

/// Lock file name under `<root>/.frob/`.
const LOCK_FILE: &str = "check.lock";
/// Append-only record of `--allow-concurrent` overrides under `<root>/.frob/`.
const OVERRIDE_LOG: &str = "check-overrides.log";
/// Environment variable the post-commit hook sets on its detached check to mark it speculative.
///
/// The hook script in `frob-worktree` spells the same name; keep the two in step.
pub const SPECULATIVE_ENV: &str = "FROB_SPECULATIVE_CHECK";
/// How long an explicit check waits for a live speculative holder before giving up.
const SUPERSEDE_WAIT: Duration = Duration::from_mins(15);
/// Poll interval while waiting for a speculative holder to finish.
const POLL: Duration = Duration::from_millis(100);
/// Grace for a freshly created lock file whose body is still being written.
const PARTIAL_WRITE_GRACE: Duration = Duration::from_millis(50);
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
    /// True when the holder is the hook's background check, which explicit runs wait out.
    #[serde(default)]
    pub speculative: bool,
}

/// Whether a check run was asked for (explicit) or started by the post-commit hook (speculative).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    /// A user, script or agent ran `frob check`.
    Explicit,
    /// The post-commit hook's detached background check.
    Speculative,
}

impl Role {
    /// The role of this process, read from [`SPECULATIVE_ENV`].
    #[must_use]
    pub fn from_env() -> Self {
        if std::env::var_os(SPECULATIVE_ENV).is_some_and(|v| !v.is_empty()) {
            Self::Speculative
        } else {
            Self::Explicit
        }
    }
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
                std::fs::remove_file(path).ok();
                tracing::debug!(lock = ?path, "released the check lock");
            }
        }
    }
}

/// Write the holder record into the freshly claimed lock file.
fn write_body(mut file: std::fs::File, body: &[u8]) -> std::io::Result<()> {
    file.write_all(body)
}

/// Drop a lock file whose holder is gone; a failure surfaces on the next claim attempt.
fn discard_stale_lock(path: &Path) {
    std::fs::remove_file(path).ok();
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

/// The live full-check holder in the worktree at `root`, or `None` when no lock exists or its holder is dead.
///
/// Read-only: unlike `acquire` it never reclaims a stale lock.
#[must_use]
pub fn live_holder(root: &Path) -> Option<LockHolder> {
    let holder = read_holder(&root.join(".frob").join(LOCK_FILE))?;
    let alive = pid_alive(holder.pid);
    tracing::debug!(pid = holder.pid, alive, root = ?root, "check lock inspected");
    alive.then_some(holder)
}

/// Take the full-check lock for `root` as process `pid`; refuses within one read when a live holder exists.
///
/// With `allow_concurrent` no lock is taken and the override is appended to the run log. An
/// [`Role::Explicit`] run waits (up to 15 minutes) for a live speculative holder instead of refusing.
///
/// # Errors
///
/// [`LockError::Held`] when a live process holds the lock, [`LockError::Io`] on filesystem failure.
pub fn acquire(
    root: &Path,
    pid: u32,
    argv: &[String],
    allow_concurrent: bool,
    role: Role,
    clock: &dyn gob_time::Clock,
) -> Result<CheckLock, LockError> {
    acquire_waiting(
        root,
        pid,
        argv,
        allow_concurrent,
        role,
        clock,
        SUPERSEDE_WAIT,
    )
}

/// [`acquire`] with an explicit bound on how long an explicit run waits for a speculative holder.
fn acquire_waiting(
    root: &Path,
    pid: u32,
    argv: &[String],
    allow_concurrent: bool,
    role: Role,
    clock: &dyn gob_time::Clock,
    max_wait: Duration,
) -> Result<CheckLock, LockError> {
    let dir = root.join(".frob");
    std::fs::create_dir_all(&dir).map_err(|source| LockError::Io {
        path: dir.join(LOCK_FILE),
        source,
    })?;
    let me = LockHolder {
        pid,
        started: u64::try_from(clock.now().unix()).unwrap_or(0),
        argv: argv.to_vec(),
        speculative: role == Role::Speculative,
    };
    if allow_concurrent {
        record_override(&dir, &me, argv);
        return Ok(CheckLock { path: None, pid });
    }
    claim_loop(&dir.join(LOCK_FILE), &me, role, max_wait)
}

/// Log the `--allow-concurrent` override beside the lock so the bypass leaves a trail.
fn record_override(dir: &Path, me: &LockHolder, argv: &[String]) {
    let line = format!(
        "{} pid {} allow-concurrent: {}\n",
        me.started,
        me.pid,
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
        pid = me.pid,
        "--allow-concurrent: running a full check without the worktree lock"
    );
}

/// Claim the lock file at `path` for `me`, waiting on a speculative holder and reclaiming stale ones.
fn claim_loop(
    path: &Path,
    me: &LockHolder,
    role: Role,
    max_wait: Duration,
) -> Result<CheckLock, LockError> {
    let pid = me.pid;
    let io = |source| LockError::Io {
        path: path.to_path_buf(),
        source,
    };
    let body = serde_json::to_vec(me).expect("LockHolder serializes");
    let deadline = Instant::now() + max_wait;
    let mut attempts = 0;
    while attempts < CLAIM_ATTEMPTS {
        match OpenOptions::new().write(true).create_new(true).open(path) {
            Ok(f) => {
                write_body(f, &body).map_err(io)?;
                tracing::debug!(lock = ?path, pid, "took the check lock");
                return Ok(CheckLock {
                    path: Some(path.to_path_buf()),
                    pid,
                });
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
                let mut holder = read_holder(path);
                if holder.is_none() {
                    // The holder may have created the file but not yet written its body.
                    std::thread::sleep(PARTIAL_WRITE_GRACE);
                    holder = read_holder(path);
                }
                match holder {
                    Some(h) if pid_alive(h.pid) => {
                        if role == Role::Explicit && h.speculative && Instant::now() < deadline {
                            tracing::info!(
                                holder = h.pid,
                                "waiting for the speculative background check to finish"
                            );
                            std::thread::sleep(POLL);
                            continue;
                        }
                        return Err(LockError::Held(h));
                    }
                    stale => {
                        tracing::warn!(holder = ?stale, "reclaiming a stale check lock");
                        discard_stale_lock(path);
                        attempts += 1;
                    }
                }
            }
            Err(e) => return Err(io(e)),
        }
    }
    Err(io(std::io::Error::other(
        "lock contended by concurrent reclaimers",
    )))
}

#[cfg(test)]
mod tests {
    use super::{LOCK_FILE, LockError, Role, acquire, acquire_waiting};
    use std::io::Read as _;
    use std::time::Duration;

    // frob:tests crates/frob-check/src/concurrent.rs::Role.from_env
    #[test]
    fn from_env_reads_the_speculative_marker() {
        let expected = if std::env::var_os(super::SPECULATIVE_ENV).is_some_and(|v| !v.is_empty()) {
            Role::Speculative
        } else {
            Role::Explicit
        };
        assert_eq!(Role::from_env(), expected);
    }

    fn clock() -> gob_time::FixedClock {
        gob_time::FixedClock::new(gob_time::Stamp::from_unix(1_000_000))
    }

    /// Drop `guard` on a background thread after `delay`.
    fn release_after<T: Send + 'static>(guard: T, delay: Duration) -> std::thread::JoinHandle<()> {
        std::thread::spawn(move || {
            std::thread::sleep(delay);
            drop(guard);
        })
    }

    fn argv() -> Vec<String> {
        vec!["frob".into(), "check".into()]
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[test]
    fn live_holder_refuses_second_run_naming_pid() {
        let dir = tempfile::tempdir().unwrap();
        let first = acquire(
            dir.path(),
            std::process::id(),
            &argv(),
            false,
            Role::Explicit,
            &clock(),
        )
        .unwrap();
        let err = acquire(dir.path(), 4242, &argv(), false, Role::Explicit, &clock()).unwrap_err();
        let LockError::Held(h) = &err else {
            panic!("expected Held, got {err}");
        };
        assert_eq!(h.pid, std::process::id());
        assert!(err.to_string().contains(&std::process::id().to_string()));
        assert!(err.to_string().contains("frob check"));
        drop(first);
        assert!(!dir.path().join(".frob").join(LOCK_FILE).exists());
        acquire(dir.path(), 4242, &argv(), false, Role::Explicit, &clock()).unwrap();
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[cfg(target_os = "linux")]
    #[test]
    fn stale_lock_from_dead_pid_is_reclaimed() {
        let dir = tempfile::tempdir().unwrap();
        let dead = u32::MAX - 1;
        let stale = acquire(dir.path(), dead, &argv(), false, Role::Explicit, &clock()).unwrap();
        std::mem::forget(stale);
        let lock = acquire(
            dir.path(),
            std::process::id(),
            &argv(),
            false,
            Role::Explicit,
            &clock(),
        )
        .unwrap();
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
        let _held = acquire(
            dir.path(),
            std::process::id(),
            &argv(),
            false,
            Role::Explicit,
            &clock(),
        )
        .unwrap();
        let _second = acquire(dir.path(), 4242, &argv(), true, Role::Explicit, &clock()).unwrap();
        let mut log = String::new();
        std::fs::File::open(dir.path().join(".frob/check-overrides.log"))
            .unwrap()
            .read_to_string(&mut log)
            .unwrap();
        assert!(log.contains("allow-concurrent"));
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[test]
    fn explicit_run_waits_for_a_live_speculative_holder() {
        let dir = tempfile::tempdir().unwrap();
        let spec = acquire(
            dir.path(),
            std::process::id(),
            &argv(),
            false,
            Role::Speculative,
            &clock(),
        )
        .unwrap();
        let releaser = release_after(spec, Duration::from_millis(300));
        // Before the fix this was refused with Held (E-CHECK-CONCURRENT).
        let lock = acquire_waiting(
            dir.path(),
            4242,
            &argv(),
            false,
            Role::Explicit,
            &clock(),
            Duration::from_secs(30),
        );
        releaser.join().unwrap();
        assert!(
            lock.is_ok(),
            "explicit run must outwait the speculative one"
        );
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[test]
    fn speculative_run_never_waits_and_explicit_holders_are_not_waited_on() {
        let dir = tempfile::tempdir().unwrap();
        let _explicit = acquire(
            dir.path(),
            std::process::id(),
            &argv(),
            false,
            Role::Explicit,
            &clock(),
        )
        .unwrap();
        let spec = acquire(
            dir.path(),
            4242,
            &argv(),
            false,
            Role::Speculative,
            &clock(),
        );
        assert!(matches!(spec, Err(LockError::Held(_))));
        let other = acquire_waiting(
            dir.path(),
            4243,
            &argv(),
            false,
            Role::Explicit,
            &clock(),
            Duration::from_secs(30),
        );
        assert!(matches!(other, Err(LockError::Held(_))));
    }

    // frob:tests crates/frob-check/src/concurrent.rs::acquire
    #[test]
    fn explicit_wait_is_bounded() {
        let dir = tempfile::tempdir().unwrap();
        let _spec = acquire(
            dir.path(),
            std::process::id(),
            &argv(),
            false,
            Role::Speculative,
            &clock(),
        )
        .unwrap();
        let r = acquire_waiting(
            dir.path(),
            4242,
            &argv(),
            false,
            Role::Explicit,
            &clock(),
            Duration::from_millis(250),
        );
        assert!(matches!(r, Err(LockError::Held(_))));
    }

    #[test]
    fn speculative_env_name_matches_the_hook() {
        assert_eq!(super::SPECULATIVE_ENV, "FROB_SPECULATIVE_CHECK");
    }
}
