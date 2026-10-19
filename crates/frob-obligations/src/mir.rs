//! `MIR001`: the mirror is behind (design: `mirror.md` sections 3.1 and 3.2).
//!
//! Time-based: no successful mirror run for N hours (scheduled runs are delayed, dropped and
//! disabled after inactivity), plus the per-scope reasons a run records when it stops. Every
//! finding is Advisory: the mirror never fails a check or a land.

// frob:ticket 01M4052VTX4T6W688PQXVTQV56

use gob_rules::{Finding, RuleId, Severity};
use gob_time::Stamp;

/// The rule id of the mirror-behind finding.
const MIR001: &str = "MIR001";

/// Seconds in an hour, for the staleness window.
const HOUR_SECS: i64 = 3600;

/// Why a scope of the mirror could not be brought up to date (mirror.md 3.2).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Mir001Reason {
    /// The run stopped at the rate limit; `reset` is the unix time the next window opens.
    RateLimited {
        /// Unix time the window resets, when the headers gave it.
        reset: Option<i64>,
    },
    /// The allowance cannot cover one ticket's reads plus one write.
    BudgetTooSmall,
    /// The token cannot see the repository or its own recent issues.
    TokenBlind,
    /// A bot issue carries a marker under a kid the keyring does not know.
    MarkerKeyUnknown,
    /// A per-ticket render limit was exceeded.
    RenderLimit,
    /// A write was accepted but the next read did not show it.
    WriteNotSticking,
}

impl Mir001Reason {
    /// The short reason slug shown in the message.
    pub fn slug(&self) -> &'static str {
        match self {
            Self::RateLimited { .. } => "rate-limited",
            Self::BudgetTooSmall => "budget-too-small",
            Self::TokenBlind => "token-blind",
            Self::MarkerKeyUnknown => "marker-key-unknown",
            Self::RenderLimit => "render-limit",
            Self::WriteNotSticking => "write-not-sticking",
        }
    }

    /// The one-line message for this reason, naming the next window when rate limited.
    pub fn describe(&self) -> String {
        match self {
            Self::RateLimited { reset: Some(r) } => {
                format!("{}: next window at unix time {r}", self.slug())
            }
            Self::RateLimited { reset: None } => {
                format!("{}: next window unknown", self.slug())
            }
            _ => self.slug().to_owned(),
        }
    }
}

/// A reason tied to the scope it applies to (a ticket ULID, or `run` for the whole run).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeReason {
    /// What the reason is about.
    pub scope: String,
    /// Why that scope is behind.
    pub reason: Mir001Reason,
}

/// What the last mirror runs left behind, as read from the mirror's recorded state.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct MirrorRunState {
    /// When the last run that completed successfully finished; `None` when none ever did.
    pub last_success: Option<Stamp>,
    /// The reasons the latest runs stopped short, per scope.
    pub reasons: Vec<ScopeReason>,
}

/// The validated `MIR001` id.
fn mir001_id() -> RuleId {
    MIR001
        .parse()
        .unwrap_or_else(|e| unreachable!("MIR001 is a valid rule id: {e}"))
}

/// An Advisory `MIR001` finding anchored on `anchor`.
fn advisory(anchor: &str, message: String) -> Finding {
    Finding::new(mir001_id(), Severity::Advisory, None, message, anchor)
}

/// `MIR001` findings for `state` at `now`: one when the last success is older than `max_hours`
/// (or there never was one), plus one per recorded scope reason. Empty when the mirror is fresh
/// and no reason is recorded. Never an Error: the mirror cannot fail a check.
pub fn mir001(state: &MirrorRunState, now: Stamp, max_hours: u64) -> Vec<Finding> {
    let mut out = Vec::new();
    let limit = i64::try_from(max_hours)
        .unwrap_or(i64::MAX / HOUR_SECS)
        .saturating_mul(HOUR_SECS);
    match state.last_success {
        None => {
            tracing::info!("MIR001: no successful mirror run recorded");
            out.push(advisory(
                "mirror/behind",
                "MIR001 mirror behind: no successful mirror run recorded".to_owned(),
            ));
        }
        Some(at) => {
            let age = now.unix().saturating_sub(at.unix());
            if age > limit {
                let hours = age / HOUR_SECS;
                tracing::info!(hours, max_hours, "MIR001: last successful run is stale");
                out.push(advisory(
                    "mirror/behind",
                    format!(
                        "MIR001 mirror behind: last successful run {hours} h ago (limit {max_hours} h)"
                    ),
                ));
            }
        }
    }
    for r in &state.reasons {
        tracing::info!(scope = %r.scope, reason = r.reason.slug(), "MIR001 scope reason");
        out.push(advisory(
            &format!("mirror/{}/{}", r.scope, r.reason.slug()),
            format!("MIR001 {} ({})", r.reason.describe(), r.scope),
        ));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: i64 = 1_000_000;

    fn at(hours_ago: i64) -> Stamp {
        Stamp::from_unix(NOW - hours_ago * HOUR_SECS)
    }

    #[test]
    fn stale_success_reports_age_and_never_errors() {
        // frob:tests crates/frob-obligations/src/mir.rs::mir001
        let state = MirrorRunState {
            last_success: Some(at(30)),
            reasons: vec![],
        };
        let found = mir001(&state, Stamp::from_unix(NOW), 24);
        assert_eq!(found.len(), 1);
        assert!(found[0].message.contains("30 h ago"));
        assert!(found.iter().all(|f| f.severity == Severity::Advisory));
    }

    #[test]
    fn rate_limited_run_reports_reason_with_next_window() {
        // frob:tests crates/frob-obligations/src/mir.rs::mir001
        let state = MirrorRunState {
            last_success: Some(at(1)),
            reasons: vec![ScopeReason {
                scope: "run".to_owned(),
                reason: Mir001Reason::RateLimited { reset: Some(1234) },
            }],
        };
        let found = mir001(&state, Stamp::from_unix(NOW), 24);
        assert_eq!(found.len(), 1);
        assert!(found[0].message.contains("rate-limited"));
        assert!(found[0].message.contains("unix time 1234"));
    }

    #[test]
    fn fresh_success_without_reasons_emits_nothing() {
        // frob:tests crates/frob-obligations/src/mir.rs::mir001
        let state = MirrorRunState {
            last_success: Some(at(2)),
            reasons: vec![],
        };
        assert!(mir001(&state, Stamp::from_unix(NOW), 24).is_empty());
    }

    #[test]
    fn never_succeeded_is_behind() {
        // frob:tests crates/frob-obligations/src/mir.rs::mir001
        let found = mir001(&MirrorRunState::default(), Stamp::from_unix(NOW), 24);
        assert_eq!(found.len(), 1);
        assert!(found[0].message.contains("no successful"));
    }
}
