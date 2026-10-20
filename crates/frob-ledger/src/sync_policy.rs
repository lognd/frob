//! Per-verb auto-refresh policy (`distributed-tickets.md` section 5.3): when a verb kicks a background refresh, probes in the foreground, or refuses on a stale view.
//!
//! The decisions are pure functions of the cached [`RefreshState`], the clock and `[sync]`;
//! only [`background_kick`] and [`foreground_probe`] touch the system.

// frob:ticket 01M5CW04GHM970H5KR4EV5KK0X

use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{EnvPolicy, ExecError, Limits, Program, Runner, Spec};
use gob_git::{GitError, Repo};
use gob_path::Shown;
use tracing::{debug, info, warn};

use crate::config::SyncTable;
use crate::refresh::{ProbeMode, ProbeReport, RefreshState, human_age, probe};

/// Environment variable that disables background sync and every network claim verb (CI).
pub const CI_VAR: &str = "CI";

/// Environment variable set on frob's own nested pushes so they never kick another refresh.
pub const INNER_VAR: &str = "FROB_SYNC_INNER";

/// How old the cached view is relative to `[sync]`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Staleness {
    /// Younger than `warn_after`: say nothing.
    Fresh,
    /// Older than `warn_after`: footnote it.
    Warn,
    /// Older than `stale_error`: mutating verbs refuse and `doable` rows may be taken.
    Error,
    /// The remote was never probed successfully on this clone.
    Unknown,
}

/// A mutating verb refused because the view is too old to claim from (`E-SYNC-STALE`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StaleRefusal {
    /// Human text naming the age and the remedy.
    pub message: String,
}

/// Whether the environment turns automatic sync off: `CI` or a nested frob push is set and non-empty.
#[must_use]
pub fn sync_disabled(env: impl Fn(&str) -> Option<String>) -> bool {
    [CI_VAR, INNER_VAR]
        .iter()
        .any(|k| env(k).is_some_and(|v| !v.is_empty() && v != "0" && v != "false"))
}

/// Seconds since the last successful probe, `None` when there never was one.
///
/// A failed probe does not refresh the view, so only the last `Ok` answer counts; the cache keeps that time in `last_ok_at`.
#[must_use]
pub fn view_age(state: &RefreshState, now: i64) -> Option<i64> {
    (state.last_ok_at > 0).then(|| (now - state.last_ok_at).max(0))
}

/// Classify the cache age against `warn_after` and `stale_error`.
#[must_use]
pub fn staleness(state: &RefreshState, now: i64, cfg: &SyncTable) -> Staleness {
    match view_age(state, now) {
        None => Staleness::Unknown,
        Some(age) if age > i64::from(cfg.stale_error_secs) => Staleness::Error,
        Some(age) if age > i64::from(cfg.warn_after_secs) => Staleness::Warn,
        Some(_) => Staleness::Fresh,
    }
}

/// The ranked-message-class text for a stale view, or `None` when nothing needs saying.
///
/// Shape: `<CODE>: ticket view is <age> old (<cause>). <fix>. Silence with [sync] warn_after_secs.`
#[must_use]
pub fn notice(state: &RefreshState, now: i64, cfg: &SyncTable) -> Option<String> {
    let level = staleness(state, now, cfg);
    if level == Staleness::Fresh {
        return None;
    }
    let code = state.class.code().unwrap_or("W-SYNC-STALE");
    let cause = if state.detail.is_empty() {
        "no recent probe"
    } else {
        state.detail.as_str()
    };
    let text = match view_age(state, now) {
        Some(age) => format!(
            "{code}: ticket view is {} old ({cause}). Run frob refresh when online. Silence with [sync] warn_after_secs.",
            human_age(age)
        ),
        None => format!(
            "{code}: ticket view was never refreshed from {} ({cause}). Run frob refresh when online.",
            state.remote
        ),
    };
    Some(text)
}

/// Gate for mutating verbs after the foreground probe: refuse when the view is past `stale_error` or unknown and the probe did not succeed.
///
/// A repository without a remote never refuses (`has_remote` false).
///
/// # Errors
/// [`StaleRefusal`] (`E-SYNC-STALE`) when the view is too old to trust.
pub fn stale_gate(
    state: &RefreshState,
    now: i64,
    cfg: &SyncTable,
    has_remote: bool,
) -> Result<(), StaleRefusal> {
    if !has_remote {
        return Ok(());
    }
    match staleness(state, now, cfg) {
        Staleness::Fresh | Staleness::Warn => Ok(()),
        level => {
            let age = view_age(state, now).map_or_else(|| "never".to_owned(), human_age);
            warn!(?level, %age, "refusing: ticket view too old");
            Err(StaleRefusal {
                message: format!(
                    "E-SYNC-STALE: ticket view last refreshed {age} ago (limit {}). Run frob refresh, or pass --offline --reason.",
                    human_age(i64::from(cfg.stale_error_secs))
                ),
            })
        }
    }
}

/// Whether a read verb should start a background refresh: the cache is past `ttl`, no backoff is pending and none was started within `ttl`.
#[must_use]
pub fn kick_due(state: &RefreshState, last_kick: Option<i64>, now: i64, cfg: &SyncTable) -> bool {
    let ttl = i64::from(cfg.ttl_secs);
    let probe_stale = state.probed_at == 0 || now - state.probed_at >= ttl;
    let backing_off = now < state.next_attempt_at;
    let kicked_recently = last_kick.is_some_and(|k| now - k < ttl);
    probe_stale && !backing_off && !kicked_recently
}

/// A copy of `cfg` whose probe timeout is clamped to `foreground_budget_ms`.
#[must_use]
pub fn foreground_cfg(cfg: &SyncTable) -> SyncTable {
    SyncTable {
        probe_timeout_ms: cfg.probe_timeout_ms.min(cfg.foreground_budget_ms),
        ..cfg.clone()
    }
}

fn kick_path(common_dir: &Path) -> PathBuf {
    common_dir.join("frob").join("kick")
}

fn read_kick(common_dir: &Path) -> Option<i64> {
    fs::read_to_string(kick_path(common_dir))
        .ok()?
        .trim()
        .parse()
        .ok()
}

fn write_kick(common_dir: &Path, now: i64) -> io::Result<()> {
    let path = kick_path(common_dir);
    fs::create_dir_all(path.parent().unwrap_or(common_dir))?;
    fs::write(path, now.to_string())
}

/// What [`background_kick`] did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KickOutcome {
    /// A detached `refresh` was started.
    Spawned,
    /// Nothing was due (fresh cache, backoff, a recent kick or no remote).
    NotDue,
    /// Sync is off here (CI or a nested frob push).
    Disabled,
    /// Spawning failed; the verb carries on with the cache.
    Failed,
}

/// Start a detached `<exe> refresh` in `cwd` and return its pid; the child never kicks another refresh.
///
/// # Errors
/// [`ExecError`] when the executable cannot be started.
pub fn spawn_refresh(exe: &Path, cwd: &Path) -> Result<u32, ExecError> {
    let spec = Spec {
        program: Program::Hook {
            path: exe.to_path_buf(),
        },
        args: vec!["refresh".to_owned()],
        cwd: Some(cwd.to_path_buf()),
        env: vec![(INNER_VAR.to_owned(), "1".to_owned())],
        timeout: Duration::ZERO,
        capture: false,
    };
    Runner::new(Limits { jobs: 1 }).spawn_detached(&spec, &EnvPolicy::Inherit)
}

/// Start a detached `<exe> refresh` when one is due; never waits and never touches the network inline.
///
/// At most one spawn per `ttl` per clone: the spawn time is kept in `<common_dir>/frob/kick`.
pub fn background_kick(
    repo: &Repo,
    cfg: &SyncTable,
    exe: &Path,
    now: i64,
    env: impl Fn(&str) -> Option<String>,
) -> KickOutcome {
    if sync_disabled(env) {
        debug!("background refresh disabled by environment");
        return KickOutcome::Disabled;
    }
    if repo.remote_url(&cfg.remote).is_none() {
        return KickOutcome::NotDue;
    }
    let common = repo.common_dir();
    let state = RefreshState::load(common);
    if !kick_due(&state, read_kick(common), now, cfg) {
        return KickOutcome::NotDue;
    }
    if let Err(e) = write_kick(common, now) {
        warn!(error = %e, "cannot record the refresh kick; skipping it");
        return KickOutcome::Failed;
    }
    match spawn_refresh(exe, repo.work_dir().unwrap_or(common)) {
        Ok(pid) => {
            info!(exe = %Shown::of(exe), pid, "background refresh started");
            KickOutcome::Spawned
        }
        Err(e) => {
            warn!(error = %e, "cannot start the background refresh");
            KickOutcome::Failed
        }
    }
}

/// Probe within the foreground budget, falling back to the cache on any failure.
///
/// # Errors
/// [`GitError`] when git cannot be spawned or the state cannot be written.
pub fn foreground_probe(
    repo: &Repo,
    cfg: &SyncTable,
    base: &str,
    ledger_branch: Option<&str>,
    now: i64,
) -> Result<ProbeReport, GitError> {
    probe(
        repo,
        &foreground_cfg(cfg),
        base,
        ledger_branch,
        now,
        ProbeMode::Auto,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::refresh::ProbeClass;

    fn state(class: ProbeClass, probed_at: i64, last_ok_at: i64) -> RefreshState {
        RefreshState {
            class,
            probed_at,
            last_ok_at,
            remote: "origin".into(),
            ..RefreshState::default()
        }
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::sync_disabled
    #[test]
    fn ci_and_inner_disable_sync() {
        assert!(sync_disabled(|k| (k == "CI").then(|| "true".to_owned())));
        assert!(sync_disabled(|k| (k == INNER_VAR).then(|| "1".to_owned())));
        assert!(!sync_disabled(|_| None));
        assert!(!sync_disabled(|_| Some(String::new())));
        assert!(!sync_disabled(|k| (k == "CI").then(|| "false".to_owned())));
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::staleness
    #[test]
    fn staleness_follows_warn_and_error_ages() {
        let cfg = SyncTable::default();
        let s = state(ProbeClass::Ok, 1000, 1000);
        assert_eq!(staleness(&s, 1000 + 3600, &cfg), Staleness::Fresh);
        assert_eq!(staleness(&s, 1000 + 3601, &cfg), Staleness::Warn);
        assert_eq!(staleness(&s, 1000 + 86401, &cfg), Staleness::Error);
        assert_eq!(
            staleness(&RefreshState::default(), 5, &cfg),
            Staleness::Unknown
        );
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::stale_gate
    #[test]
    fn gate_refuses_only_past_stale_error_or_unknown() {
        let cfg = SyncTable::default();
        let old = state(ProbeClass::Offline, 90_000, 100);
        let e = stale_gate(&old, 100_000, &cfg, true).expect_err("refuses");
        assert!(e.message.starts_with("E-SYNC-STALE"), "{}", e.message);
        let young = state(ProbeClass::Offline, 90_000, 80_000);
        assert!(stale_gate(&young, 100_000, &cfg, true).is_ok());
        assert!(stale_gate(&RefreshState::default(), 5, &cfg, true).is_err());
        assert!(stale_gate(&RefreshState::default(), 5, &cfg, false).is_ok());
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::notice
    #[test]
    fn notice_uses_the_failure_code_and_age() {
        let cfg = SyncTable::default();
        let mut s = state(ProbeClass::Offline, 20_000, 100);
        s.detail = "probe timed out".into();
        let n = notice(&s, 100 + 3 * 3600 + 700, &cfg).expect("notice");
        assert!(
            n.starts_with("W-SYNC-OFFLINE: ticket view is 3h old"),
            "{n}"
        );
        assert!(n.contains("probe timed out"));
        let fresh = state(ProbeClass::Ok, 100, 100);
        assert!(notice(&fresh, 200, &cfg).is_none());
        let n = notice(&state(ProbeClass::Ok, 100, 100), 100 + 7200, &cfg).expect("stale");
        assert!(n.starts_with("W-SYNC-STALE"), "{n}");
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::kick_due
    #[test]
    fn kick_waits_for_ttl_backoff_and_prior_kick() {
        let cfg = SyncTable::default();
        let s = state(ProbeClass::Ok, 1000, 1000);
        assert!(!kick_due(&s, None, 1100, &cfg));
        assert!(kick_due(&s, None, 1300, &cfg));
        assert!(!kick_due(&s, Some(1250), 1300, &cfg));
        assert!(kick_due(&s, Some(900), 1300, &cfg));
        let mut b = s.clone();
        b.next_attempt_at = 2000;
        assert!(!kick_due(&b, None, 1300, &cfg));
        assert!(kick_due(&RefreshState::default(), None, 5, &cfg));
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::foreground_cfg
    #[test]
    fn foreground_budget_clamps_the_probe_timeout() {
        let cfg = SyncTable {
            probe_timeout_ms: 10_000,
            ..SyncTable::default()
        };
        assert_eq!(foreground_cfg(&cfg).probe_timeout_ms, 3000);
        assert_eq!(foreground_cfg(&SyncTable::default()).probe_timeout_ms, 2500);
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::background_kick
    #[test]
    fn kick_is_disabled_in_ci_and_idle_without_a_remote() {
        let dir = tempfile::tempdir().expect("tmp");
        let repo = Repo::init(dir.path()).expect("init");
        let exe = Path::new("frob");
        let cfg = SyncTable::default();
        let ci = |k: &str| (k == CI_VAR).then(|| "1".to_string());
        assert_eq!(
            background_kick(&repo, &cfg, exe, 1000, ci),
            KickOutcome::Disabled
        );
        assert_eq!(
            background_kick(&repo, &cfg, exe, 1000, |_| None),
            KickOutcome::NotDue
        );
    }

    // frob:tests crates/frob-ledger/src/sync_policy.rs::foreground_probe
    #[test]
    fn foreground_probe_without_a_remote_is_not_an_error() {
        let dir = tempfile::tempdir().expect("tmp");
        let repo = Repo::init(dir.path()).expect("init");
        let report = foreground_probe(&repo, &SyncTable::default(), "main", None, 1000);
        assert!(report.is_ok());
    }
}
