//! The freshness probe state behind `frob refresh` (`distributed-tickets.md` section 5): a per-clone `refresh.toml`, a non-blocking lock, exponential backoff and a bounded `git ls-remote`.
// frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2

use std::collections::BTreeMap;
use std::fs::{self, File, TryLockError};
use std::io;
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_git::{GitError, RemoteProbe, Repo};
use gob_path::Shown;
use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

use crate::config::SyncTable;

/// Longest backoff doubling exponent; keeps the shift in range whatever `failures` grows to.
const MAX_SHIFT: u32 = 20;

/// What the last probe found, as stored in `refresh.toml`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ProbeClass {
    /// Never probed (no state file).
    #[default]
    Unknown,
    /// The remote answered and has the base branch.
    Ok,
    /// The remote could not be reached (`W-SYNC-OFFLINE`).
    Offline,
    /// The probe hit its timeout (`W-SYNC-TIMEOUT`).
    Timeout,
    /// Credentials were refused or would have needed a prompt (`W-SYNC-AUTH`).
    Auth,
    /// The host rate-limited the probe (`W-SYNC-RATE`).
    Rate,
    /// The remote answered but lacks the base branch (`E-SYNC-NO-BASE`).
    NoBase,
}

impl ProbeClass {
    /// Whether this class is a retryable failure that grows the backoff.
    #[must_use]
    pub fn is_retryable_failure(self) -> bool {
        matches!(
            self,
            Self::Offline | Self::Timeout | Self::Auth | Self::Rate
        )
    }

    /// The stable diagnostic code of this class, or `None` when there is nothing to report.
    #[must_use]
    pub fn code(self) -> Option<&'static str> {
        match self {
            Self::Unknown | Self::Ok => None,
            Self::Offline => Some("W-SYNC-OFFLINE"),
            Self::Timeout => Some("W-SYNC-TIMEOUT"),
            Self::Auth => Some("W-SYNC-AUTH"),
            Self::Rate => Some("W-SYNC-RATE"),
            Self::NoBase => Some("E-SYNC-NO-BASE"),
        }
    }
}

/// The cached outcome of the last probe of one clone's remote.
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct RefreshState {
    /// Unix seconds of the last probe attempt; 0 when never probed.
    pub probed_at: i64,
    /// Unix seconds of the last probe the remote answered (`Ok` or `NoBase`); 0 when none did. Failed probes leave it, so it measures how old the ticket view is.
    #[serde(default)]
    pub last_ok_at: i64,
    /// What that probe found.
    pub class: ProbeClass,
    /// The remote that was probed.
    pub remote: String,
    /// The base branch that was required on it.
    pub base: String,
    /// Remote ref name to object id as of the last answer.
    pub oids: BTreeMap<String, String>,
    /// Consecutive retryable failures; drives the backoff.
    pub failures: u32,
    /// Unix seconds before which an automatic probe is not due.
    pub next_attempt_at: i64,
    /// Human text of the last problem (empty when ok).
    pub detail: String,
}

/// How eagerly [`probe`] may skip the network.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProbeMode {
    /// Skip while inside the ttl or a backoff window.
    Auto,
    /// An explicit `frob refresh`: skip only inside a failure backoff window.
    Explicit,
    /// `--force`: always probe.
    Force,
}

/// Why [`probe`] returned without a fresh answer, or that it got one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProbeOutcome {
    /// The remote was asked and the state updated.
    Probed {
        /// Whether any remote oid differs from the previous state.
        changed: bool,
    },
    /// The cache was fresh enough (or backing off); no network was used.
    Cached,
    /// Another refresh holds the lock; the cache was used.
    Busy,
    /// The repository has no such remote: `local-only`, nothing to probe.
    LocalOnly,
}

/// The result of one [`probe`] call.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProbeReport {
    /// What happened.
    pub outcome: ProbeOutcome,
    /// The state after the call.
    pub state: RefreshState,
}

/// Where the shared per-clone state file lives under the repository's common dir.
#[must_use]
pub fn state_path(common_dir: &Path) -> PathBuf {
    common_dir.join("frob").join("refresh.toml")
}

fn lock_path(common_dir: &Path) -> PathBuf {
    common_dir.join("frob").join("refresh.lock")
}

impl RefreshState {
    /// Read the cache; a missing or unreadable file is "unknown" because the cache is disposable.
    #[must_use]
    pub fn load(common_dir: &Path) -> Self {
        let path = state_path(common_dir);
        match fs::read_to_string(&path) {
            Ok(text) => toml::from_str(&text).unwrap_or_else(|e| {
                warn!(path = %Shown::of(&path), error = %e, "refresh state unreadable; treating as unknown");
                Self::default()
            }),
            Err(e) if e.kind() == io::ErrorKind::NotFound => {
                debug!(path = %Shown::of(&path), "no refresh state yet");
                Self::default()
            }
            Err(e) => {
                warn!(path = %Shown::of(&path), error = %e, "refresh state not readable; treating as unknown");
                Self::default()
            }
        }
    }

    /// Write the cache atomically (temp file then rename).
    ///
    /// # Errors
    /// The I/O error when the directory or file cannot be written.
    pub fn save(&self, common_dir: &Path) -> io::Result<()> {
        let path = state_path(common_dir);
        let dir = path.parent().unwrap_or(common_dir);
        fs::create_dir_all(dir)?;
        let tmp = path.with_extension("toml.tmp");
        let text = toml::to_string(self).map_err(io::Error::other)?;
        fs::write(&tmp, text)?;
        fs::rename(&tmp, &path)?;
        debug!(path = %Shown::of(&path), class = ?self.class, "refresh state saved");
        Ok(())
    }

    /// One-line status from the cache alone, e.g. `frob:ok`, `frob:2h-stale` or `frob:unknown`.
    #[must_use]
    pub fn status_line(&self, now: i64, ttl_secs: u32) -> String {
        match self.class {
            ProbeClass::Unknown => "frob:unknown".to_owned(),
            ProbeClass::NoBase => "frob:no-base".to_owned(),
            ProbeClass::Ok => {
                let age = (now - self.probed_at).max(0);
                if age <= i64::from(ttl_secs) {
                    "frob:ok".to_owned()
                } else {
                    format!("frob:{}-stale", human_age(age))
                }
            }
            failed => {
                let age = (now - self.probed_at).max(0);
                format!(
                    "frob:{}-stale {}",
                    human_age(age),
                    failed.code().unwrap_or("W-SYNC")
                )
            }
        }
    }
}

/// Seconds as a coarse age: `45s`, `12m`, `2h`, `3d`.
#[must_use]
pub fn human_age(secs: i64) -> String {
    match secs {
        s if s < 60 => format!("{s}s"),
        s if s < 3600 => format!("{}m", s / 60),
        s if s < 86_400 => format!("{}h", s / 3600),
        s => format!("{}d", s / 86_400),
    }
}

/// Seconds to wait after `failures` consecutive failures: `ttl` doubling each time, capped at `max`.
#[must_use]
pub fn backoff_secs(failures: u32, ttl_secs: u32, max_secs: u32) -> u32 {
    let shift = failures.saturating_sub(1).min(MAX_SHIFT);
    let wait = u64::from(ttl_secs) << shift;
    u32::try_from(wait.min(u64::from(max_secs))).unwrap_or(max_secs)
}

/// Failure-text markers meaning credentials were refused or unavailable.
const AUTH: [&str; 6] = [
    "permission denied",
    "authentication failed",
    "terminal prompts disabled",
    "could not read username",
    "publickey",
    "access denied",
];
/// Failure-text markers meaning the host throttled us.
const RATE: [&str; 3] = ["429", "rate limit", "too many requests"];

/// Sort a failed probe's text into auth, rate-limit or offline.
#[must_use]
pub fn classify_failure(text: &str) -> ProbeClass {
    let t = text.to_ascii_lowercase();
    if AUTH.iter().any(|m| t.contains(m)) {
        ProbeClass::Auth
    } else if RATE.iter().any(|m| t.contains(m)) {
        ProbeClass::Rate
    } else {
        ProbeClass::Offline
    }
}

/// The ls-remote patterns of one probe: `HEAD`, the base, the ledger branch (orphan mode) and ticket/parked branches.
#[must_use]
pub fn probe_patterns(base: &str, ledger_branch: Option<&str>) -> Vec<String> {
    let mut v = vec!["HEAD".to_owned(), format!("refs/heads/{base}")];
    if let Some(b) = ledger_branch {
        v.push(format!("refs/heads/{b}"));
    }
    v.push("refs/heads/ticket/*".to_owned());
    v.push("refs/heads/parked/*".to_owned());
    v
}

/// Held while one refresh runs; dropping it releases the lock.
#[derive(Debug)]
pub struct RefreshLock {
    _file: File,
}

impl RefreshLock {
    /// Take the per-clone lock without blocking; `Ok(None)` means another refresh holds it.
    ///
    /// # Errors
    /// The I/O error when the lock file cannot be opened.
    pub fn try_acquire(common_dir: &Path) -> io::Result<Option<Self>> {
        let path = lock_path(common_dir);
        fs::create_dir_all(path.parent().unwrap_or(common_dir))?;
        let file = File::options().create(true).append(true).open(&path)?;
        match file.try_lock() {
            Ok(()) => Ok(Some(Self { _file: file })),
            Err(TryLockError::WouldBlock) => {
                info!(path = %Shown::of(&path), "refresh already running");
                Ok(None)
            }
            Err(TryLockError::Error(e)) => Err(e),
        }
    }
}

/// Probe the configured remote when due and record the answer.
///
/// `ledger_branch` is the orphan ticket branch to include, if any. Never fetches: that is the
/// integrate step's job.
///
/// # Errors
/// [`GitError`] when git cannot be spawned or the state cannot be written.
pub fn probe(
    repo: &Repo,
    cfg: &SyncTable,
    base: &str,
    ledger_branch: Option<&str>,
    now: i64,
    mode: ProbeMode,
) -> Result<ProbeReport, GitError> {
    let common = repo.common_dir().to_path_buf();
    let mut state = RefreshState::load(&common);
    if repo.remote_url(&cfg.remote).is_none() {
        info!(remote = %cfg.remote, "no such remote; local-only");
        return Ok(ProbeReport {
            outcome: ProbeOutcome::LocalOnly,
            state,
        });
    }
    let backing_off = state.failures > 0 && now < state.next_attempt_at;
    let skip = match mode {
        ProbeMode::Force => false,
        ProbeMode::Explicit => backing_off,
        ProbeMode::Auto => now < state.next_attempt_at,
    };
    if skip {
        debug!(
            ?mode,
            next = state.next_attempt_at,
            "probe not due; using cache"
        );
        return Ok(ProbeReport {
            outcome: ProbeOutcome::Cached,
            state,
        });
    }
    let Some(_lock) = RefreshLock::try_acquire(&common).map_err(|e| io_err("refresh lock", e))?
    else {
        return Ok(ProbeReport {
            outcome: ProbeOutcome::Busy,
            state,
        });
    };
    let patterns = probe_patterns(base, ledger_branch);
    let timeout = Duration::from_millis(u64::from(cfg.probe_timeout_ms));
    let answer = repo.ls_remote(&cfg.remote, &patterns, timeout)?;
    let previous = std::mem::take(&mut state.oids);
    state.probed_at = now;
    state.remote.clone_from(&cfg.remote);
    base.clone_into(&mut state.base);
    let mut changed = false;
    match answer {
        RemoteProbe::Refs { refs, head_branch } => {
            let oids: BTreeMap<String, String> = refs
                .into_iter()
                .filter(|r| r.name != "HEAD")
                .map(|r| (r.name, r.oid))
                .collect();
            changed = oids != previous;
            state.last_ok_at = now;
            state.failures = 0;
            state.next_attempt_at = now + i64::from(cfg.ttl_secs);
            if oids.contains_key(&format!("refs/heads/{base}")) {
                state.class = ProbeClass::Ok;
                state.detail.clear();
            } else {
                state.class = ProbeClass::NoBase;
                state.detail = format!(
                    "{} has no {base}; {} HEAD is {}",
                    cfg.remote,
                    cfg.remote,
                    head_branch.as_deref().unwrap_or("unknown")
                );
            }
            state.oids = oids;
        }
        RemoteProbe::TimedOut => {
            state.oids = previous;
            fail(
                &mut state,
                ProbeClass::Timeout,
                "probe timed out".to_owned(),
                cfg,
                now,
            );
        }
        RemoteProbe::Failed { text, .. } => {
            state.oids = previous;
            let class = classify_failure(&text);
            let detail = text.lines().next().unwrap_or("").trim().to_owned();
            fail(&mut state, class, detail, cfg, now);
        }
    }
    state
        .save(&common)
        .map_err(|e| io_err("refresh state", e))?;
    info!(class = ?state.class, changed, failures = state.failures, "remote probed");
    Ok(ProbeReport {
        outcome: ProbeOutcome::Probed { changed },
        state,
    })
}

fn io_err(context: &str, source: io::Error) -> GitError {
    GitError::Io {
        context: context.to_owned(),
        source,
    }
}

fn fail(state: &mut RefreshState, class: ProbeClass, detail: String, cfg: &SyncTable, now: i64) {
    state.class = class;
    state.detail = detail;
    state.failures = state.failures.saturating_add(1);
    state.next_attempt_at = now
        + i64::from(backoff_secs(
            state.failures,
            cfg.ttl_secs,
            cfg.backoff_max_secs,
        ));
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
    #[test]
    fn backoff_doubles_and_caps() {
        assert_eq!(backoff_secs(1, 300, 3600), 300);
        assert_eq!(backoff_secs(2, 300, 3600), 600);
        assert_eq!(backoff_secs(3, 300, 3600), 1200);
        assert_eq!(backoff_secs(5, 300, 3600), 3600);
        assert_eq!(backoff_secs(u32::MAX, 300, 3600), 3600);
    }

    #[test]
    fn only_transient_classes_are_retryable_failures() {
        // frob:tests crates/frob-ledger/src/refresh.rs::ProbeClass.is_retryable_failure
        assert!(ProbeClass::Offline.is_retryable_failure());
        assert!(ProbeClass::Rate.is_retryable_failure());
        assert!(!ProbeClass::Ok.is_retryable_failure());
        assert!(!ProbeClass::NoBase.is_retryable_failure());
    }

    #[test]
    fn failure_text_is_classified() {
        assert_eq!(
            classify_failure("fatal: could not read Username for 'https://x'"),
            ProbeClass::Auth
        );
        assert_eq!(
            classify_failure("git@x: Permission denied (publickey)."),
            ProbeClass::Auth
        );
        assert_eq!(
            classify_failure("HTTP 429 Too Many Requests"),
            ProbeClass::Rate
        );
        assert_eq!(
            classify_failure("Could not resolve host: x"),
            ProbeClass::Offline
        );
    }

    #[test]
    fn status_lines_come_from_the_cache() {
        let mut s = RefreshState::default();
        assert_eq!(s.status_line(1000, 300), "frob:unknown");
        s.class = ProbeClass::Ok;
        s.probed_at = 1000;
        assert_eq!(s.status_line(1100, 300), "frob:ok");
        assert_eq!(s.status_line(1000 + 7200 + 5, 300), "frob:2h-stale");
        s.class = ProbeClass::Offline;
        assert_eq!(
            s.status_line(1000 + 120, 300),
            "frob:2m-stale W-SYNC-OFFLINE"
        );
    }

    #[test]
    fn state_round_trips_and_missing_is_unknown() {
        let dir = tempfile::tempdir().expect("tmp");
        assert_eq!(RefreshState::load(dir.path()).class, ProbeClass::Unknown);
        let mut s = RefreshState {
            probed_at: 5,
            class: ProbeClass::Rate,
            ..RefreshState::default()
        };
        s.oids.insert("refs/heads/main".into(), "abc".into());
        s.save(dir.path()).expect("save");
        assert_eq!(RefreshState::load(dir.path()), s);
    }

    #[test]
    fn status_from_cache_takes_under_ten_ms() {
        let dir = tempfile::tempdir().expect("tmp");
        let s = RefreshState {
            probed_at: 1,
            class: ProbeClass::Ok,
            ..RefreshState::default()
        };
        s.save(dir.path()).expect("save");
        let t = std::time::Instant::now();
        let line = RefreshState::load(dir.path()).status_line(100_000, 300);
        assert!(
            t.elapsed() < Duration::from_millis(10),
            "took {:?}",
            t.elapsed()
        );
        assert!(line.ends_with("-stale"));
    }

    #[test]
    fn second_lock_is_refused_until_release() {
        let dir = tempfile::tempdir().expect("tmp");
        let first = RefreshLock::try_acquire(dir.path())
            .expect("io")
            .expect("lock");
        assert!(RefreshLock::try_acquire(dir.path()).expect("io").is_none());
        drop(first);
        assert!(RefreshLock::try_acquire(dir.path()).expect("io").is_some());
    }

    #[test]
    fn patterns_name_base_ledger_and_prefixes() {
        let p = probe_patterns("experimental", Some("frob-tickets"));
        assert!(p.contains(&"refs/heads/experimental".to_owned()));
        assert!(p.contains(&"refs/heads/frob-tickets".to_owned()));
        assert!(p.contains(&"refs/heads/ticket/*".to_owned()));
        assert!(
            !probe_patterns("main", None)
                .iter()
                .any(|x| x.contains("frob-tickets"))
        );
    }

    fn git(dir: &Path, args: &[&str]) {
        let st = std::process::Command::new("git")
            .args(args)
            .current_dir(dir)
            .env("GIT_AUTHOR_NAME", "t")
            .env("GIT_AUTHOR_EMAIL", "t@t")
            .env("GIT_COMMITTER_NAME", "t")
            .env("GIT_COMMITTER_EMAIL", "t@t")
            .status()
            .expect("git");
        assert!(st.success(), "git {args:?}");
    }

    /// A clone whose `origin` is a local repo with branch `main`; returns (guard, clone path).
    fn clone_with_origin() -> (tempfile::TempDir, PathBuf) {
        let t = tempfile::tempdir().expect("tmp");
        let origin = t.path().join("origin");
        let clone = t.path().join("clone");
        fs::create_dir_all(&origin).expect("mk");
        git(&origin, &["init", "-q", "-b", "main"]);
        git(&origin, &["commit", "-q", "--allow-empty", "-m", "c1"]);
        fs::create_dir_all(&clone).expect("mk");
        git(&clone, &["init", "-q", "-b", "main"]);
        git(
            &clone,
            &["remote", "add", "origin", &Shown::of(&origin).to_string()],
        );
        (t, clone)
    }

    #[test]
    fn probe_records_ok_then_uses_cache_then_sees_change() {
        let (t, clone) = clone_with_origin();
        let repo = Repo::discover(&clone).expect("repo");
        let cfg = SyncTable::default();
        let r = probe(&repo, &cfg, "main", None, 1000, ProbeMode::Auto).expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::Probed { changed: true });
        assert_eq!(r.state.class, ProbeClass::Ok);
        assert!(r.state.oids.contains_key("refs/heads/main"));
        let r = probe(&repo, &cfg, "main", None, 1010, ProbeMode::Auto).expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::Cached);
        let r = probe(&repo, &cfg, "main", None, 1020, ProbeMode::Explicit).expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::Probed { changed: false });
        git(
            &t.path().join("origin"),
            &["commit", "-q", "--allow-empty", "-m", "c2"],
        );
        let r = probe(&repo, &cfg, "main", None, 1030, ProbeMode::Force).expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::Probed { changed: true });
    }

    #[test]
    fn probe_reports_missing_base_naming_remote_head() {
        let (_t, clone) = clone_with_origin();
        let repo = Repo::discover(&clone).expect("repo");
        let r = probe(
            &repo,
            &SyncTable::default(),
            "experimental",
            None,
            5,
            ProbeMode::Force,
        )
        .expect("probe");
        assert_eq!(r.state.class, ProbeClass::NoBase);
        assert_eq!(
            r.state.detail,
            "origin has no experimental; origin HEAD is main"
        );
    }

    #[test]
    fn unreachable_remote_backs_off_and_missing_remote_is_local_only() {
        let (t, clone) = clone_with_origin();
        let repo = Repo::discover(&clone).expect("repo");
        fs::remove_dir_all(t.path().join("origin")).expect("rm");
        let cfg = SyncTable::default();
        let r = probe(&repo, &cfg, "main", None, 100, ProbeMode::Auto).expect("probe");
        assert_eq!(r.state.class, ProbeClass::Offline);
        assert_eq!(r.state.failures, 1);
        assert_eq!(r.state.next_attempt_at, 100 + 300);
        let r = probe(&repo, &cfg, "main", None, 150, ProbeMode::Explicit).expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::Cached);
        let other = SyncTable {
            remote: "nope".into(),
            ..SyncTable::default()
        };
        let r = probe(&repo, &other, "main", None, 150, ProbeMode::Force).expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::LocalOnly);
    }

    #[test]
    fn busy_lock_returns_cache() {
        let (_t, clone) = clone_with_origin();
        let repo = Repo::discover(&clone).expect("repo");
        let _held = RefreshLock::try_acquire(repo.common_dir())
            .expect("io")
            .expect("lock");
        let r = probe(
            &repo,
            &SyncTable::default(),
            "main",
            None,
            1,
            ProbeMode::Force,
        )
        .expect("probe");
        assert_eq!(r.outcome, ProbeOutcome::Busy);
    }
}
