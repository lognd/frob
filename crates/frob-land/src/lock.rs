//! The land lock: one `flock` file under the common git dir, with a JSON sidecar naming the holder (frob:ticket 01M4W4R7PNWSRECR99078ATXCB).
//!
//! The sidecar (`land.lock.holder`) records the holder's pid, start time, current
//! stage and last-progress time. Two safety nets keep a wedged land from
//! blocking every other land forever:
//!
//! - a **progress watchdog** thread inside the holder: when no stage has been
//!   marked for [`LockOptions::stall_after`] and the holder has no live child
//!   process, it releases the lock and aborts the process;
//! - **stale-holder takeover** in a waiter: a holder whose pid is dead, or whose
//!   progress is older than twice the stall bound (its own watchdog had its
//!   chance), is terminated and, when the lock is still pinned, the lock file is
//!   replaced; every takeover is logged with its reason.

use gob_path::Shown;
use std::fs::{File, OpenOptions, TryLockError};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex, PoisonError};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use gob_diagnostics::{Refusal, RefusalClass};
use gob_time::{Clock, SystemClock};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::error::LandError;

/// How often a contended lock is retried while waiting.
const POLL: Duration = Duration::from_millis(25);

/// How often a waiter re-reads the holder sidecar to judge it.
const JUDGE_EVERY: Duration = Duration::from_secs(1);

/// How long a terminated holder gets to free the lock before the lock file is replaced.
const KILL_GRACE: Duration = Duration::from_secs(3);

/// Default idle-progress bound of a holder (`FROB_LAND_STALL_SECS` overrides it).
pub const DEFAULT_STALL_AFTER: Duration = Duration::from_mins(20);

/// Environment variable that sets the stall bound in seconds.
pub const STALL_ENV: &str = "FROB_LAND_STALL_SECS";

/// Process exit code of a land aborted by its own watchdog.
pub const EXIT_STALLED: i32 = 75;

/// Stable code of the refusal when the lock is busy.
pub const CODE_LOCKED: &str = "E-LAND-LOCKED";

/// What the sidecar of the land lock holds: who has the lock and how far they got.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct HolderRecord {
    /// Process id of the holder.
    pub pid: u32,
    /// Free text naming the actor and ticket.
    pub holder: String,
    /// Unix seconds when the lock was taken.
    pub started: i64,
    /// The stage the holder last reported (`acquired`, `merge`, `check`, `publish`, ...).
    pub stage: String,
    /// Unix seconds of the last reported progress.
    pub progress: i64,
    /// `debug` or `release`: the profile of the holder's binary.
    pub build: String,
}

/// A read-out of the land lock for `frob land --status`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct LockStatus {
    /// True when some process holds the lock.
    pub held: bool,
    /// The holder's record, when the sidecar could be read.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub record: Option<HolderRecord>,
    /// True when the holder's pid is alive.
    pub alive: bool,
    /// Seconds since the lock was taken.
    pub age_secs: i64,
    /// Seconds since the last reported progress.
    pub idle_secs: i64,
    /// One-line human summary.
    pub summary: String,
}

/// What a watchdog does when it declares the holder stalled.
#[derive(Clone)]
pub enum StallAction {
    /// Exit the process with [`EXIT_STALLED`] (the production behaviour).
    ExitProcess,
    /// Call a hook with the stalled stage instead (tests).
    Hook(Arc<dyn Fn(&str) + Send + Sync>),
}

impl std::fmt::Debug for StallAction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ExitProcess => f.write_str("ExitProcess"),
            Self::Hook(_) => f.write_str("Hook"),
        }
    }
}

/// How a waiter ends a stale holder; returns true when it was signalled.
pub type Terminator = Arc<dyn Fn(u32) -> bool + Send + Sync>;

/// Tuning of the lock's safety nets.
#[derive(Clone)]
pub struct LockOptions {
    /// Idle-progress bound of a holder; a waiter takes over after twice this.
    pub stall_after: Duration,
    /// How often the watchdog looks.
    pub tick: Duration,
    /// What the watchdog does on a stall.
    pub on_stall: StallAction,
    /// How a waiter ends a stale holder.
    pub terminate: Terminator,
}

impl Default for LockOptions {
    fn default() -> Self {
        let stall_after = std::env::var(STALL_ENV)
            .ok()
            .and_then(|s| s.trim().parse::<u64>().ok())
            .map_or(DEFAULT_STALL_AFTER, Duration::from_secs);
        Self {
            stall_after,
            tick: Duration::from_secs(5),
            on_stall: StallAction::ExitProcess,
            terminate: Arc::new(terminate_frob),
        }
    }
}

impl std::fmt::Debug for LockOptions {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LockOptions")
            .field("stall_after", &self.stall_after)
            .field("tick", &self.tick)
            .field("on_stall", &self.on_stall)
            .finish_non_exhaustive()
    }
}

/// Progress state shared between the lock handle and its watchdog.
#[derive(Debug)]
struct Shared {
    sidecar: PathBuf,
    record: Mutex<HolderRecord>,
    last: Mutex<Instant>,
    stalled: Mutex<bool>,
}

impl Shared {
    fn write(&self, record: &HolderRecord) -> Result<(), LandError> {
        write_record(&self.sidecar, record)
    }
}

/// The held land lock; released (and its sidecar removed) on drop.
#[derive(Debug)]
pub struct LandLock {
    _file: Arc<File>,
    shared: Arc<Shared>,
    stop: Option<Sender<()>>,
    watchdog: Option<JoinHandle<()>>,
}

impl LandLock {
    /// Path of the lock file below `common_dir`.
    pub fn path(common_dir: &Path) -> PathBuf {
        common_dir.join("frob").join("land.lock")
    }

    /// Path of the holder sidecar below `common_dir`.
    pub fn sidecar_path(common_dir: &Path) -> PathBuf {
        Self::path(common_dir).with_extension("lock.holder")
    }

    /// Take the lock with default [`LockOptions`], waiting up to `wait` for another land to finish.
    ///
    /// # Errors
    ///
    /// `E-LAND-LOCKED` (retryable) when the wait expires; I/O failures otherwise.
    pub fn acquire(common_dir: &Path, wait: Duration, holder: &str) -> Result<Self, LandError> {
        Self::acquire_with(common_dir, wait, holder, &LockOptions::default())
    }

    /// Take the lock, waiting up to `wait`, with a watchdog and stale-holder takeover per `opts`.
    ///
    /// `holder` is recorded in the sidecar so a refused caller can name who has it.
    ///
    /// # Errors
    ///
    /// `E-LAND-LOCKED` (retryable) when the wait expires; I/O failures otherwise.
    pub fn acquire_with(
        common_dir: &Path,
        wait: Duration,
        holder: &str,
        opts: &LockOptions,
    ) -> Result<Self, LandError> {
        let path = Self::path(common_dir);
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir)
                .map_err(|e| LandError::io(format!("creating {}", Shown::of(dir)), e))?;
        }
        let sidecar = Self::sidecar_path(common_dir);
        let mut file = open_lock(&path)?;
        let start = Instant::now();
        let mut last_judged: Option<Instant> = None;
        let mut taken_over: Option<Instant> = None;
        loop {
            match file.try_lock() {
                Ok(()) => break,
                Err(TryLockError::WouldBlock) => {
                    if start.elapsed() >= wait {
                        return Err(locked_refusal(&path, &sidecar));
                    }
                    if last_judged.is_none_or(|t| t.elapsed() >= JUDGE_EVERY) {
                        last_judged = Some(Instant::now());
                        file = judge_holder(&path, &sidecar, file, opts, &mut taken_over)?;
                    }
                    std::thread::sleep(POLL);
                }
                Err(TryLockError::Error(e)) => {
                    return Err(LandError::io(format!("locking {}", Shown::of(&path)), e));
                }
            }
        }
        let now = SystemClock.now().unix();
        let record = HolderRecord {
            pid: std::process::id(),
            holder: holder.to_owned(),
            started: now,
            stage: "acquired".to_owned(),
            progress: now,
            build: build_profile().to_owned(),
        };
        write_record(&sidecar, &record)?;
        tracing::info!(lock = %Shown::of(&path), holder, build = %record.build, "land lock taken");
        let file = Arc::new(file);
        let shared = Arc::new(Shared {
            sidecar,
            record: Mutex::new(record),
            last: Mutex::new(Instant::now()),
            stalled: Mutex::new(false),
        });
        let (stop, rx) = mpsc::channel::<()>();
        let watchdog = spawn_watchdog(file.clone(), shared.clone(), rx, opts.clone());
        Ok(Self {
            _file: file,
            shared,
            stop: Some(stop),
            watchdog,
        })
    }

    /// Report that the land entered `stage`: refreshes the sidecar and the watchdog's clock.
    pub fn progress(&self, stage: &str) {
        let mut record = self
            .shared
            .record
            .lock()
            .unwrap_or_else(PoisonError::into_inner);
        if *self
            .shared
            .stalled
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
        {
            return;
        }
        stage.clone_into(&mut record.stage);
        record.progress = SystemClock.now().unix();
        *self
            .shared
            .last
            .lock()
            .unwrap_or_else(PoisonError::into_inner) = Instant::now();
        tracing::info!(stage, pid = record.pid, "land progress");
        if let Err(e) = self.shared.write(&record) {
            tracing::warn!(error = %e, "land holder sidecar not updated");
        }
    }

    /// Read the lock's state without taking it: who holds it, at which stage, for how long.
    ///
    /// # Errors
    ///
    /// I/O failures opening the lock file.
    pub fn status(common_dir: &Path, clock: &dyn Clock) -> Result<LockStatus, LandError> {
        let path = Self::path(common_dir);
        let record = read_record(&Self::sidecar_path(common_dir));
        let held = match OpenOptions::new().write(true).open(&path) {
            Ok(file) => match file.try_lock() {
                Ok(()) => {
                    let _ = file.unlock();
                    false
                }
                Err(TryLockError::WouldBlock) => true,
                Err(TryLockError::Error(e)) => {
                    return Err(LandError::io(format!("locking {}", Shown::of(&path)), e));
                }
            },
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => false,
            Err(e) => return Err(LandError::io(format!("opening {}", Shown::of(&path)), e)),
        };
        let now = clock.now().unix();
        let alive = record.as_ref().is_some_and(|r| pid_alive(r.pid));
        let (age_secs, idle_secs) = record
            .as_ref()
            .map_or((0, 0), |r| (now - r.started, now - r.progress));
        let summary = match (&record, held) {
            (_, false) => "the land lock is free".to_owned(),
            (Some(r), true) => format!(
                "held by {} (pid {}{}, {} build), stage {}, held {}s, idle {}s",
                r.holder,
                r.pid,
                if alive { "" } else { ", DEAD" },
                r.build,
                r.stage,
                age_secs,
                idle_secs
            ),
            (None, true) => "held by an unknown land (no holder record)".to_owned(),
        };
        Ok(LockStatus {
            held,
            record: if held { record } else { None },
            alive,
            age_secs,
            idle_secs,
            summary,
        })
    }
}

impl Drop for LandLock {
    fn drop(&mut self) {
        drop(self.stop.take());
        if let Some(handle) = self.watchdog.take() {
            let _ = handle.join();
        }
        let stalled = *self
            .shared
            .stalled
            .lock()
            .unwrap_or_else(PoisonError::into_inner);
        if stalled {
            tracing::warn!("land lock was already released by the watchdog");
            return;
        }
        if let Err(e) = std::fs::remove_file(&self.shared.sidecar) {
            tracing::debug!(error = %e, "land lock sidecar not removed");
        }
        tracing::info!("land lock released");
    }
}

/// `release` or `debug`, by how this crate was compiled (the binary that holds the lock).
fn build_profile() -> &'static str {
    if cfg!(debug_assertions) {
        "debug"
    } else {
        "release"
    }
}

/// True when this binary is an unoptimized debug build, which lands several times slower.
#[must_use]
pub fn is_debug_build() -> bool {
    cfg!(debug_assertions)
}

fn open_lock(path: &Path) -> Result<File, LandError> {
    OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(path)
        .map_err(|e| LandError::io(format!("opening {}", Shown::of(path)), e))
}

fn locked_refusal(path: &Path, sidecar: &Path) -> LandError {
    let who = read_record(sidecar).map_or_else(
        || {
            std::fs::read_to_string(sidecar)
                .map_or_else(|_| "another land".to_owned(), |s| s.trim().to_owned())
        },
        |r| {
            format!(
                "{} (pid {}, stage {}, idle {}s)",
                r.holder,
                r.pid,
                r.stage,
                SystemClock.now().unix() - r.progress
            )
        },
    );
    tracing::warn!(lock = %Shown::of(path), holder = %who, "land lock is held");
    LandError::Refused(
        Refusal::new(
            CODE_LOCKED,
            RefusalClass::GuardRetryByWaiting,
            format!("the land lock is held by {who}"),
        )
        .with_remedy("rerun with --wait <secs> to wait for the lock, or `frob land --status`"),
    )
}

/// Atomically replace the sidecar with `record`.
fn write_record(sidecar: &Path, record: &HolderRecord) -> Result<(), LandError> {
    let text = serde_json::to_string(record)
        .map_err(|e| LandError::Config(format!("encoding the holder record: {e}")))?;
    gob_fs::write_atomic(sidecar, format!("{text}\n").as_bytes())
        .map_err(|e| LandError::io(format!("writing {}", Shown::of(sidecar)), e))
}

fn read_record(sidecar: &Path) -> Option<HolderRecord> {
    let text = std::fs::read_to_string(sidecar).ok()?;
    serde_json::from_str(text.trim()).ok()
}

/// Judge the current holder; terminate a stale one and, when it still pins the lock, replace the lock file.
fn judge_holder(
    path: &Path,
    sidecar: &Path,
    file: File,
    opts: &LockOptions,
    taken_over: &mut Option<Instant>,
) -> Result<File, LandError> {
    let Some(record) = read_record(sidecar) else {
        return Ok(file);
    };
    let idle = u64::try_from(SystemClock.now().unix() - record.progress).unwrap_or(0);
    let alive = pid_alive(record.pid);
    let busy = alive && has_live_children(record.pid);
    let stale = alive && !busy && Duration::from_secs(idle) >= opts.stall_after * 2;
    if let Some(at) = taken_over {
        if at.elapsed() >= KILL_GRACE {
            tracing::warn!(
                pid = record.pid,
                "stale holder still pins the lock; replacing the lock file"
            );
            *taken_over = None;
            return replace_lock(path, sidecar, &file);
        }
        return Ok(file);
    }
    if !alive {
        tracing::warn!(pid = record.pid, stage = %record.stage, "land lock holder is dead but the lock is pinned; taking over");
        *taken_over = Some(
            Instant::now()
                .checked_sub(KILL_GRACE)
                .unwrap_or_else(Instant::now),
        );
    } else if stale {
        tracing::warn!(
            pid = record.pid,
            stage = %record.stage,
            idle_secs = idle,
            "land lock holder made no progress for twice the stall bound; terminating it"
        );
        let signalled = (opts.terminate)(record.pid);
        tracing::warn!(
            pid = record.pid,
            signalled,
            "stale holder terminate attempted"
        );
        *taken_over = Some(Instant::now());
    }
    Ok(file)
}

/// Replace the lock file with a fresh inode so a pinned old one no longer blocks; only when `file` is still the one at `path`.
fn replace_lock(path: &Path, sidecar: &Path, file: &File) -> Result<File, LandError> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let same = match (std::fs::metadata(path), file.metadata()) {
            (Ok(a), Ok(b)) => a.ino() == b.ino() && a.dev() == b.dev(),
            _ => false,
        };
        if !same {
            return open_lock(path);
        }
    }
    #[cfg(not(unix))]
    let _ = file;
    let _ = std::fs::remove_file(path);
    let _ = std::fs::remove_file(sidecar);
    open_lock(path)
}

/// True when process `pid` exists.
pub(crate) fn pid_alive(pid: u32) -> bool {
    if cfg!(target_os = "linux") {
        Path::new(&format!("/proc/{pid}")).exists()
    } else {
        true
    }
}

/// True when process `pid` has a live child (any thread's children list is non-empty); Linux only.
fn has_live_children(pid: u32) -> bool {
    let Ok(tasks) = std::fs::read_dir(format!("/proc/{pid}/task")) else {
        return false;
    };
    tasks.flatten().any(|t| {
        std::fs::read_to_string(t.path().join("children")).is_ok_and(|s| !s.trim().is_empty())
    })
}

/// Default terminator: SIGKILL a process whose name says it is a frob binary, never this process.
fn terminate_frob(pid: u32) -> bool {
    if pid == std::process::id() {
        return false;
    }
    if cfg!(target_os = "linux") {
        let comm = std::fs::read_to_string(format!("/proc/{pid}/comm")).unwrap_or_default();
        if !comm.contains("frob") {
            tracing::warn!(
                pid,
                comm = comm.trim(),
                "stale holder is not a frob binary; not killing"
            );
            return false;
        }
    }
    let spec = gob_exec::Spec {
        program: gob_exec::Program::Tool {
            name: "kill".to_owned(),
        },
        args: vec!["-KILL".to_owned(), pid.to_string()],
        cwd: None,
        env: Vec::new(),
        timeout: Duration::from_secs(10),
        capture: true,
    };
    gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
        .run(&spec)
        .is_ok_and(|o| matches!(o.status, gob_exec::Outcome::Exited(0)))
}

/// Start the watchdog thread; none when the stall bound is zero.
fn spawn_watchdog(
    file: Arc<File>,
    shared: Arc<Shared>,
    rx: mpsc::Receiver<()>,
    opts: LockOptions,
) -> Option<JoinHandle<()>> {
    if opts.stall_after.is_zero() {
        return None;
    }
    std::thread::Builder::new()
        .name("land-watchdog".to_owned())
        .spawn(move || {
            loop {
                match rx.recv_timeout(opts.tick) {
                    Err(RecvTimeoutError::Timeout) => {}
                    Ok(()) | Err(RecvTimeoutError::Disconnected) => return,
                }
                let idle = shared
                    .last
                    .lock()
                    .unwrap_or_else(PoisonError::into_inner)
                    .elapsed();
                if idle < opts.stall_after || has_live_children(std::process::id()) {
                    continue;
                }
                let stage = shared
                    .record
                    .lock()
                    .unwrap_or_else(PoisonError::into_inner)
                    .stage
                    .clone();
                tracing::error!(%stage, ?idle, "land made no progress; the watchdog is releasing the lock and aborting");
                *shared.stalled.lock().unwrap_or_else(PoisonError::into_inner) = true;
                let _ = std::fs::remove_file(&shared.sidecar);
                let _ = file.unlock();
                match &opts.on_stall {
                    StallAction::ExitProcess => std::process::exit(EXIT_STALLED),
                    StallAction::Hook(hook) => hook(&stage),
                }
                return;
            }
        })
        .map_err(|e| tracing::error!(error = %e, "land watchdog not started"))
        .ok()
}
