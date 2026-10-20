//! Freshness of the cached ticket view: data age plus ranked `W-SYNC-*` / `E-SYNC-*` notices (`distributed-tickets.md` section 5.3).
//!
//! Pure functions over the cached [`RefreshState`]; nothing here touches the network or the disk.
// frob:ticket 01M5CW04D5QJCJ5S72V8PE22M6

use std::fmt::Write as _;

use serde::Serialize;
use tracing::debug;

use frob_ledger::refresh::{ProbeClass, RefreshState, human_age};

/// Default age in seconds past which a view earns `W-SYNC-STALE` (`[sync] warn_after`, 1 h).
pub const DEFAULT_WARN_AFTER_SECS: u32 = 3600;

/// Default age in seconds past which claiming verbs refuse (`[sync] stale_error`, 24 h).
pub const DEFAULT_STALE_ERROR_SECS: u32 = 86_400;

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
    /// The design defaults around the configured `ttl_secs`.
    #[must_use]
    pub fn with_ttl(ttl_secs: u32) -> Self {
        Self {
            ttl_secs,
            warn_after_secs: DEFAULT_WARN_AFTER_SECS,
            stale_error_secs: DEFAULT_STALE_ERROR_SECS,
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
        let _ = write!(message, " Silence with {silence}.");
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

#[cfg(test)]
mod tests {
    use super::*;

    fn st(class: ProbeClass, probed_at: i64) -> RefreshState {
        RefreshState {
            class,
            probed_at,
            ..RefreshState::default()
        }
    }

    fn t() -> Thresholds {
        Thresholds::with_ttl(300)
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
}
