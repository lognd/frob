//! Freshness of the cached ticket view: data age plus ranked `W-SYNC-*` / `E-SYNC-*` notices (`distributed-tickets.md` section 5.3).
//!
//! Pure functions over the cached [`RefreshState`]; nothing here touches the network or the disk.
// frob:ticket 01M5CW04D5QJCJ5S72V8PE22M6
// frob:ticket 01M5D9NM6D3DSGD980M52CRMYV
// frob:ticket 01M713HQC2TF14B5F316HMYVT3

use std::fmt::Write as _;

use serde::Serialize;
use tracing::debug;

use gob_diagnostics::{Refusal, RefusalClass, RemedyCommand};
use gob_git::Repo;
use tracing::{info, warn};

use crate::refresh::{ProbeClass, RefreshState, human_age};

/// The ages that turn a cached view into a warning and into an error.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(clippy::struct_field_names)]
pub struct Thresholds {
    /// Seconds a successful probe stays fresh (`[sync] ttl_secs`).
    pub ttl_secs: u32,
    /// Seconds after which a view warns.
    pub warn_after_secs: u32,
    /// Seconds after which a view is too old to claim from.
    pub stale_error_secs: u32,
}

impl Thresholds {
    /// The thresholds configured under `[sync]`.
    #[must_use]
    pub fn from_sync(sync: &crate::config::SyncTable) -> Self {
        Self {
            ttl_secs: sync.ttl_secs,
            warn_after_secs: sync.warn_after_secs,
            stale_error_secs: sync.stale_error_secs,
        }
    }
}

/// Facts beyond the probe cache that outrank staleness.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Signals {
    /// A branch (ledger, base or ticket) diverged from its remote copy.
    pub diverged: bool,
    /// Concurrent edits to one ledger field are unresolved.
    pub ledger_conflict: bool,
    /// The local base could not be fast-forwarded (dirty checkout).
    pub base_blocked: bool,
}

/// How the cached view relates to the remote.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, schemars::JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum FreshState {
    /// A healthy probe younger than the ttl.
    Fresh,
    /// A healthy probe older than the ttl.
    Stale,
    /// The last probe failed; the view is whatever was cached.
    Degraded,
    /// Never probed.
    Unknown,
    /// No remote to be fresh against.
    LocalOnly,
}

/// Whether a notice is advisory or blocks a claiming verb.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, schemars::JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum Severity {
    /// Advisory: proceed.
    Warning,
    /// Claiming verbs refuse.
    Error,
}

/// One ranked freshness message in the design's `CODE: what as of age (cause). fix. silence.` shape.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct Notice {
    /// Stable code such as `W-SYNC-OFFLINE`.
    pub code: String,
    /// Advisory or blocking.
    pub severity: Severity,
    /// The complete one-line text.
    pub message: String,
}

/// The age and ranked notices of one cached view.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct Freshness {
    /// How the view relates to the remote.
    pub state: FreshState,
    /// Seconds since the last probe; `None` when never probed or local-only.
    pub age_secs: Option<i64>,
    /// Notices, highest rank first.
    pub notices: Vec<Notice>,
}

impl Freshness {
    /// Notice texts, highest rank first, for an envelope `warnings` list.
    #[must_use]
    pub fn messages(&self) -> Vec<String> {
        self.notices.iter().map(|n| n.message.clone()).collect()
    }

    /// The envelope-wide `freshness` field for this view.
    #[must_use]
    pub fn to_envelope(&self) -> gob_diagnostics::EnvelopeFreshness {
        let state = serde_json::to_value(self.state)
            .ok()
            .and_then(|v| v.as_str().map(str::to_owned))
            .unwrap_or_default();
        gob_diagnostics::EnvelopeFreshness {
            state,
            age_secs: self.age_secs,
        }
    }

    /// The blocking `E-SYNC-STALE` notice, when the view is too old to claim from.
    #[must_use]
    pub fn stale_error(&self) -> Option<&Notice> {
        self.notices.iter().find(|n| n.code == "E-SYNC-STALE")
    }
}

/// Compose one notice; `silence` names the knob, or is empty when nothing can silence it.
fn notice(
    code: &str,
    severity: Severity,
    what: &str,
    age: Option<i64>,
    cause: &str,
    fix: &str,
    silence: &str,
) -> Notice {
    let age = age.map_or_else(
        || "never refreshed".to_owned(),
        |a| format!("as of {} ago", human_age(a)),
    );
    let mut message = format!("{code}: {what} {age} ({cause}). {fix}.");
    if !silence.is_empty() {
        write!(message, " Silence with {silence}.").ok();
    }
    Notice {
        code: code.to_owned(),
        severity,
        message,
    }
}

/// The age, state and ranked notices of the cached view at `now` (unix seconds).
#[must_use]
#[allow(clippy::too_many_lines)]
pub fn assess(
    state: &RefreshState,
    has_remote: bool,
    signals: Signals,
    now: i64,
    t: Thresholds,
) -> Freshness {
    if !has_remote {
        return Freshness {
            state: FreshState::LocalOnly,
            age_secs: None,
            notices: Vec::new(),
        };
    }
    let never = state.class == ProbeClass::Unknown;
    let age = (!never).then(|| (now - state.probed_at).max(0));
    let old = |limit: u32| age.is_some_and(|a| a > i64::from(limit));
    let mut notices: Vec<(u8, Notice)> = Vec::new();
    let view = "ticket view";
    let warn_knob = "[sync] warn_after_secs";
    if signals.diverged {
        notices.push((
            0,
            notice(
                "W-SYNC-DIVERGED",
                Severity::Warning,
                view,
                age,
                "a branch diverged from its remote copy",
                "Run frob refresh to unite the ledger and merge the base by hand",
                "",
            ),
        ));
    }
    if signals.ledger_conflict {
        notices.push((
            1,
            notice(
                "E-SYNC-CONFLICT",
                Severity::Error,
                view,
                age,
                "concurrent edits to one field",
                "Resolve it with frob ticket update",
                "",
            ),
        ));
    }
    match state.class {
        ProbeClass::Auth => notices.push((
            2,
            notice(
                "W-SYNC-AUTH",
                Severity::Warning,
                view,
                age,
                "credentials were refused",
                "Run git fetch origin to re-authenticate",
                warn_knob,
            ),
        )),
        ProbeClass::Rate => notices.push((
            3,
            notice(
                "W-SYNC-RATE",
                Severity::Warning,
                view,
                age,
                "the host rate-limited the probe",
                "Run frob refresh later",
                warn_knob,
            ),
        )),
        ProbeClass::Offline => notices.push((
            4,
            notice(
                "W-SYNC-OFFLINE",
                Severity::Warning,
                view,
                age,
                "the remote is unreachable",
                "Run frob refresh when online",
                warn_knob,
            ),
        )),
        ProbeClass::Timeout => notices.push((
            4,
            notice(
                "W-SYNC-TIMEOUT",
                Severity::Warning,
                view,
                age,
                "the probe timed out",
                "Run frob refresh when online",
                warn_knob,
            ),
        )),
        ProbeClass::NoBase => notices.push((
            2,
            notice(
                "E-SYNC-NO-BASE",
                Severity::Error,
                view,
                age,
                "the remote lacks the base branch",
                "Set [tickets] ref to a branch the remote has, or push it",
                "",
            ),
        )),
        ProbeClass::Unknown | ProbeClass::Ok => {}
    }
    if signals.base_blocked {
        notices.push((
            5,
            notice(
                "W-SYNC-BASE",
                Severity::Warning,
                "local base",
                age,
                "dirty checkout blocks the fast-forward",
                "Commit or stash, then run frob refresh",
                "",
            ),
        ));
    }
    if never || (state.class == ProbeClass::Ok && old(t.warn_after_secs)) {
        let (code, cause) = if never {
            ("W-SYNC-UNKNOWN", "no probe has run")
        } else {
            ("W-SYNC-STALE", "older than the warn threshold")
        };
        notices.push((
            6,
            notice(
                code,
                Severity::Warning,
                view,
                age,
                cause,
                "Run frob refresh",
                warn_knob,
            ),
        ));
    }
    if old(t.stale_error_secs) {
        notices.push((
            7,
            notice(
                "E-SYNC-STALE",
                Severity::Error,
                view,
                age,
                "too old to claim from",
                "Run frob refresh, or pass --offline --reason",
                "[sync] stale_error_secs",
            ),
        ));
    }
    notices.sort_by_key(|(rank, _)| *rank);
    let fresh_state = match state.class {
        _ if never => FreshState::Unknown,
        ProbeClass::Ok if !old(t.ttl_secs) => FreshState::Fresh,
        ProbeClass::Ok => FreshState::Stale,
        _ => FreshState::Degraded,
    };
    debug!(state = ?fresh_state, ?age, notices = notices.len(), "freshness assessed");
    Freshness {
        state: fresh_state,
        age_secs: age,
        notices: notices.into_iter().map(|(_, n)| n).collect(),
    }
}

/// The signals the last `frob refresh` recorded in `state`.
#[must_use]
pub fn signals_of(state: &RefreshState) -> Signals {
    Signals {
        diverged: state.diverged,
        ledger_conflict: state.ledger_conflict,
        base_blocked: state.base_blocked,
    }
}

/// Assess the cached view of `repo` against `sync` at `now`, feeding the recorded refresh signals.
// frob:ticket 01M713HQC2TF14B5F316HMYVT3
#[must_use]
pub fn assess_repo(repo: &Repo, sync: &crate::config::SyncTable, now: i64) -> Freshness {
    let has_remote = repo.remote_url(&sync.remote).is_some();
    let mut state = RefreshState::load(repo.common_dir());
    // A failed probe stamps `probed_at`; the view's age is the last successful answer.
    if state.last_ok_at > 0 {
        state.probed_at = state.last_ok_at;
    }
    let fresh = assess(
        &state,
        has_remote,
        signals_of(&state),
        now,
        Thresholds::from_sync(sync),
    );
    debug!(state = ?fresh.state, age = ?fresh.age_secs, "ticket view freshness");
    fresh
}

/// Refuse a claiming verb when `fresh` blocks it, unless automatic sync is disabled (`CI`).
///
/// # Errors
///
/// A [`Refusal`] (`E-SYNC-STALE`) naming the notice and the `frob refresh` remedy.
// frob:ticket 01M713HQC2TF14B5F316HMYVT3
pub fn refuse_if_blocked(fresh: &Freshness) -> Result<(), Refusal> {
    let Some(notice) = fresh.stale_error() else {
        return Ok(());
    };
    if crate::sync_policy::sync_disabled(|k| std::env::var(k).ok()) {
        debug!("stale view tolerated: automatic sync is disabled");
        return Ok(());
    }
    warn!(age = ?fresh.age_secs, "refusing: ticket view too old to claim from");
    Err(Refusal::new(
        "E-SYNC-STALE",
        RefusalClass::DomainNegative,
        notice.message.clone(),
    )
    .with_command(RemedyCommand::new("frob", "refresh")))
}

/// The `[sync]` table of the repository at `root`, or `None` (logged) when the config cannot be read, so the verb's own config load reports it.
fn load_sync(root: &std::path::Path) -> Option<crate::config::SyncTable> {
    let doc = match gob_config::ConfigDocument::read(root, crate::config::PRODUCT) {
        Ok(d) => d,
        Err(e) => {
            debug!(error = %e, "freshness gate skipped: config unreadable");
            return None;
        }
    };
    let table = doc
        .table::<crate::config::SyncTable>()
        .map(|t| t.value)
        .ok();
    if table.is_none() {
        debug!("freshness gate skipped: [sync] unreadable");
    }
    table
}

/// Gate a claiming verb in the repository at `root`: load `[sync]`, assess the cached view and refuse when it is too old.
///
/// Offline-safe: reads only the local cache. A config that cannot be read never blocks (the verb's own config load reports it).
///
/// # Errors
///
/// See [`refuse_if_blocked`].
// frob:ticket 01M713HQC2TF14B5F316HMYVT3
pub fn gate_claim(repo: &Repo, root: &std::path::Path, now: i64) -> Result<(), Refusal> {
    let Some(sync) = load_sync(root) else {
        return Ok(());
    };
    let fresh = assess_repo(repo, &sync, now);
    info!(state = ?fresh.state, "freshness gate");
    refuse_if_blocked(&fresh)
}

/// How a claiming verb treats the remote: sync first and gate, or skip both with a recorded reason.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyncStance<'a> {
    /// Probe the remote within the foreground budget, then refuse when the view is stale.
    Online,
    /// `--offline --reason`: no probe and no gate; the reason is logged and returned as a warning.
    Offline(&'a str),
}

/// Sync in the foreground, then gate: the front of every claiming verb (`distributed-tickets.md` section 5.3).
///
/// A probe that fails is not fatal: the cache is judged by [`gate_claim`]. `SyncStance::Offline` skips both and returns a `W-SYNC-OFFLINE` warning carrying the reason.
///
/// # Errors
///
/// See [`refuse_if_blocked`]; only `SyncStance::Online` can refuse.
// frob:ticket 01M5DBVTN06Y1MBT6EDFKR7TYT
pub fn sync_then_gate(
    repo: &Repo,
    root: &std::path::Path,
    ledger: &crate::LedgerConfig,
    stance: SyncStance<'_>,
    now: i64,
) -> Result<Vec<String>, Refusal> {
    if let SyncStance::Offline(reason) = stance {
        warn!(%reason, "claiming offline: foreground sync and the staleness gate are skipped");
        return Ok(vec![format!(
            "W-SYNC-OFFLINE: claiming without syncing (--offline): {reason}"
        )]);
    }
    if let Some(sync) = load_sync(root)
        && repo.remote_url(&sync.remote).is_some()
        && !crate::sync_policy::sync_disabled(|k| std::env::var(k).ok())
    {
        let branch = (ledger.mode == crate::RefMode::Orphan).then_some(ledger.branch.as_str());
        match crate::sync_policy::foreground_probe(repo, &sync, &ledger.ref_name, branch, now) {
            Ok(done) => {
                info!(outcome = ?done.outcome, class = ?done.state.class, "foreground sync before claim");
            }
            Err(e) => warn!(error = %e, "foreground sync failed; judging the cached view"),
        }
    }
    gate_claim(repo, root, now)?;
    Ok(Vec::new())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn st(class: ProbeClass, probed_at: i64) -> RefreshState {
        RefreshState {
            probed_at,
            class,
            ..RefreshState::default()
        }
    }

    fn t() -> Thresholds {
        Thresholds {
            ttl_secs: 300,
            warn_after_secs: 3600,
            stale_error_secs: 86_400,
        }
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::Freshness.messages
    #[test]
    fn messages_lists_the_notice_texts_in_order() {
        let n = |m: &str| Notice {
            code: "W-X".to_owned(),
            severity: Severity::Warning,
            message: m.to_owned(),
        };
        let f = Freshness {
            state: FreshState::Stale,
            age_secs: Some(9),
            notices: vec![n("first"), n("second")],
        };
        assert_eq!(f.messages(), vec!["first".to_owned(), "second".to_owned()]);
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::Thresholds.from_sync
    #[test]
    fn thresholds_follow_the_sync_table() {
        let sync = crate::config::SyncTable {
            ttl_secs: 7,
            warn_after_secs: 8,
            stale_error_secs: 9,
            ..crate::config::SyncTable::default()
        };
        let t = Thresholds::from_sync(&sync);
        assert_eq!(
            (t.ttl_secs, t.warn_after_secs, t.stale_error_secs),
            (7, 8, 9)
        );
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::Freshness.to_envelope
    #[test]
    fn envelope_form_of_an_old_view_is_stale_with_its_age() {
        let old = assess(
            &st(ProbeClass::Ok, 0),
            true,
            Signals::default(),
            90_000,
            t(),
        );
        let e = old.to_envelope();
        assert_eq!((e.state.as_str(), e.age_secs), ("stale", Some(90_000)));
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::Freshness.to_envelope
    #[test]
    fn envelope_form_of_a_young_view_is_fresh() {
        let young = assess(
            &st(ProbeClass::Ok, 1000),
            true,
            Signals::default(),
            1100,
            t(),
        );
        assert_eq!(young.to_envelope().state, "fresh");
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::Freshness.stale_error
    #[test]
    fn stale_error_is_present_for_a_view_past_the_error_age() {
        let old = assess(
            &st(ProbeClass::Ok, 0),
            true,
            Signals::default(),
            90_000,
            t(),
        );
        assert!(old.stale_error().is_some());
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::Freshness.stale_error
    #[test]
    fn stale_error_is_absent_for_a_young_view() {
        let young = assess(
            &st(ProbeClass::Ok, 1000),
            true,
            Signals::default(),
            1100,
            t(),
        );
        assert!(young.stale_error().is_none());
    }

    #[test]
    fn no_remote_is_local_only_and_silent() {
        let f = assess(
            &st(ProbeClass::Unknown, 0),
            false,
            Signals::default(),
            10,
            t(),
        );
        assert_eq!(f.state, FreshState::LocalOnly);
        assert!(f.notices.is_empty() && f.age_secs.is_none());
    }

    #[test]
    fn young_healthy_view_is_fresh_without_notices() {
        let f = assess(
            &st(ProbeClass::Ok, 1000),
            true,
            Signals::default(),
            1100,
            t(),
        );
        assert_eq!(f.state, FreshState::Fresh);
        assert_eq!(f.age_secs, Some(100));
        assert!(f.notices.is_empty());
    }

    #[test]
    fn healthy_view_between_ttl_and_warn_is_stale_but_quiet() {
        let f = assess(&st(ProbeClass::Ok, 0), true, Signals::default(), 1000, t());
        assert_eq!(f.state, FreshState::Stale);
        assert!(f.notices.is_empty());
    }

    #[test]
    fn old_view_warns_then_errors_with_remedy_and_silence() {
        let f = assess(&st(ProbeClass::Ok, 0), true, Signals::default(), 7200, t());
        assert_eq!(f.notices[0].code, "W-SYNC-STALE");
        assert!(f.notices[0].message.contains("as of 2h ago"));
        assert!(f.notices[0].message.contains("Run frob refresh"));
        assert!(
            f.notices[0]
                .message
                .contains("Silence with [sync] warn_after_secs.")
        );
        assert!(f.notices.iter().all(|n| n.severity != Severity::Error));
    }

    #[test]
    fn old_view_warns_then_errors_with_remedy_and_silence_part_2() {
        let f = assess(
            &st(ProbeClass::Ok, 0),
            true,
            Signals::default(),
            90_000,
            t(),
        );
        assert_eq!(
            f.notices
                .iter()
                .find(|n| n.severity == Severity::Error)
                .map(|n| n.code.as_str()),
            Some("E-SYNC-STALE")
        );
    }

    #[test]
    fn never_probed_is_unknown_with_a_notice() {
        let f = assess(
            &st(ProbeClass::Unknown, 0),
            true,
            Signals::default(),
            10,
            t(),
        );
        assert_eq!(f.state, FreshState::Unknown);
        assert_eq!(f.notices[0].code, "W-SYNC-UNKNOWN");
        assert!(f.notices[0].message.contains("never refreshed"));
    }

    #[test]
    fn notices_are_ranked_diverged_first_stale_last() {
        let sig = Signals {
            diverged: true,
            ledger_conflict: true,
            base_blocked: true,
        };
        let f = assess(&st(ProbeClass::Offline, 0), true, sig, 90_000, t());
        let codes: Vec<&str> = f.notices.iter().map(|n| n.code.as_str()).collect();
        assert_eq!(
            codes,
            [
                "W-SYNC-DIVERGED",
                "E-SYNC-CONFLICT",
                "W-SYNC-OFFLINE",
                "W-SYNC-BASE",
                "E-SYNC-STALE"
            ]
        );
        assert_eq!(f.state, FreshState::Degraded);
    }

    #[test]
    fn failure_classes_rank_auth_rate_offline() {
        let rank = |c| {
            assess(&st(c, 0), true, Signals::default(), 10, t()).notices[0]
                .code
                .clone()
        };
        assert_eq!(rank(ProbeClass::Auth), "W-SYNC-AUTH");
        assert_eq!(rank(ProbeClass::Rate), "W-SYNC-RATE");
        assert_eq!(rank(ProbeClass::Offline), "W-SYNC-OFFLINE");
        assert_eq!(rank(ProbeClass::NoBase), "E-SYNC-NO-BASE");
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::signals_of
    #[test]
    fn recorded_refresh_signals_feed_the_assessment() {
        let state = RefreshState {
            class: ProbeClass::Ok,
            probed_at: 1000,
            diverged: true,
            ledger_conflict: true,
            ..RefreshState::default()
        };
        let sig = signals_of(&state);
        assert!(sig.diverged && sig.ledger_conflict && !sig.base_blocked);
        let f = assess(&state, true, sig, 1100, t());
        let codes: Vec<_> = f.notices.iter().map(|n| n.code.as_str()).collect();
        assert_eq!(codes, ["W-SYNC-DIVERGED", "E-SYNC-CONFLICT"]);
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::refuse_if_blocked
    #[test]
    fn a_stale_error_refuses_unless_sync_is_disabled() {
        let old = assess(
            &st(ProbeClass::Ok, 0),
            true,
            Signals::default(),
            90_000,
            t(),
        );
        let disabled = crate::sync_policy::sync_disabled(|k| std::env::var(k).ok());
        assert_eq!(refuse_if_blocked(&old).is_err(), !disabled);
        let young = assess(
            &st(ProbeClass::Ok, 1000),
            true,
            Signals::default(),
            1100,
            t(),
        );
        assert!(refuse_if_blocked(&young).is_ok());
    }

    // frob:tests crates/frob-ledger/src/freshness.rs::assess_repo
    // frob:tests crates/frob-ledger/src/freshness.rs::gate_claim
    #[test]
    fn a_repo_without_a_remote_or_config_is_assessed_and_not_gated() {
        let dir = tempfile::tempdir().expect("tempdir");
        let repo = Repo::init(dir.path()).expect("init");
        let sync = crate::config::SyncTable::default();
        let fresh = assess_repo(&repo, &sync, 1_800_000_000);
        assert_eq!(fresh.state, FreshState::LocalOnly, "{fresh:?}");
        // No frob config in the root: the gate does not apply.
        assert!(gate_claim(&repo, dir.path(), 1_800_000_000).is_ok());
    }
}
