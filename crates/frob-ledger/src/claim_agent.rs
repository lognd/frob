//! Agent claims (`distributed-tickets.md` section 4.7): holder kind, the soft-activity cap and `rekind`.
//!
//! An agent claim uses the short `agent_idle_hours` window; the harness keeps it alive with
//! `frob claim touch`, a soft heartbeat. Soft activity alone may extend a claim at most
//! `soft_max_windows` windows past the last hard activity, so a polling daemon cannot hold a
//! ticket forever. A human taking over an agent worktree re-claims (`lease` op `rekind`),
//! which switches to the human window. Nothing here reads a clock or writes an event.

// frob:ticket 01M5CW058JVA3D7TKB6T62N4TW

use tracing::{debug, info};

use crate::claim_window::{ClaimObservation, ClaimWindows, HolderKind};

/// Environment variable whose presence at claim time marks the holder as an agent.
pub const AGENT_ENV: &str = "FROB_AGENT";

/// The holder kind for a claim made while `FROB_AGENT` held `agent_label` (an empty label is a human).
#[must_use]
pub fn holder_kind(agent_label: Option<&str>) -> HolderKind {
    match agent_label.map(str::trim) {
        Some(l) if !l.is_empty() => HolderKind::Agent,
        _ => HolderKind::Human,
    }
}

/// When a claim started and when this clone first saw its latest hard and soft activity (local epoch seconds).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ActivityTimes {
    /// When the claim was taken; the base before any hard activity.
    pub claim_start: i64,
    /// First sight of the latest hard activity, if any.
    pub hard: Option<i64>,
    /// First sight of the latest soft activity, if any.
    pub soft: Option<i64>,
}

/// The first-seen time the idle clock should read, with soft activity capped.
///
/// The base is the later of the claim start and the last hard activity. Soft activity
/// moves the clock past the base but never beyond `base + (soft_max_windows - 1) * window`,
/// so the claim is evictable at the latest `soft_max_windows` windows after the base.
/// `soft_max_windows = 0` ignores soft activity; a `None` window (never evict) is uncapped.
#[must_use]
pub fn capped_observed_at(
    times: &ActivityTimes,
    window_secs: Option<i64>,
    soft_max_windows: u32,
) -> i64 {
    let base = times
        .hard
        .map_or(times.claim_start, |h| h.max(times.claim_start));
    let Some(soft) = times.soft.filter(|s| *s > base) else {
        return base;
    };
    let Some(window) = window_secs else {
        return soft;
    };
    if soft_max_windows == 0 {
        debug!(base, "soft activity ignored: soft_max_windows is 0");
        return base;
    }
    let cap = base + i64::from(soft_max_windows - 1) * window;
    let at = soft.min(cap).max(base);
    if at < soft {
        debug!(soft, cap, "soft activity capped by soft_max_windows");
    }
    at
}

/// Build the [`ClaimObservation`] for a claim, applying the soft cap with the claim's own window.
#[must_use]
pub fn observation_for(
    windows: &ClaimWindows,
    times: &ActivityTimes,
    holder: HolderKind,
    class: crate::model::Class,
    ticket_idle_days: Option<u32>,
) -> ClaimObservation {
    let window = windows.window_secs(holder, class, ticket_idle_days);
    ClaimObservation {
        observed_at: capped_observed_at(times, window, windows.soft_max_windows()),
        holder,
        class,
        ticket_idle_days,
    }
}

/// Re-claim as `to` (`lease` op `rekind`): the window kind switches and the idle clock restarts at `now`.
///
/// A rekind to the kind already held changes nothing.
#[must_use]
pub fn rekind(obs: &ClaimObservation, to: HolderKind, now: i64) -> ClaimObservation {
    if obs.holder == to {
        debug!(?to, "rekind is a no-op");
        return obs.clone();
    }
    info!(from = ?obs.holder, ?to, "claim rekinded");
    ClaimObservation {
        observed_at: now,
        holder: to,
        ..obs.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::claim_window::IdleLevel;
    use crate::model::Class;

    const HOUR: i64 = 3600;

    fn times(hard: Option<i64>, soft: Option<i64>) -> ActivityTimes {
        ActivityTimes {
            claim_start: 0,
            hard,
            soft,
        }
    }

    // frob:tests holder_kind
    #[test]
    fn agent_label_selects_agent_window() {
        assert_eq!(holder_kind(Some("claude")), HolderKind::Agent);
        assert_eq!(holder_kind(Some("  ")), HolderKind::Human);
        assert_eq!(holder_kind(None), HolderKind::Human);
    }

    // frob:tests capped_observed_at
    #[test]
    fn soft_activity_is_capped_by_windows() {
        let w = Some(4 * HOUR);
        assert_eq!(capped_observed_at(&times(None, None), w, 2), 0);
        // Within the cap soft activity counts in full.
        assert_eq!(
            capped_observed_at(&times(None, Some(3 * HOUR)), w, 2),
            3 * HOUR
        );
        // Past the cap it stops at base + (2 - 1) windows.
        assert_eq!(
            capped_observed_at(&times(None, Some(50 * HOUR)), w, 2),
            4 * HOUR
        );
        // Hard activity moves the base and resets the cap.
        assert_eq!(
            capped_observed_at(&times(Some(10 * HOUR), Some(50 * HOUR)), w, 2),
            14 * HOUR
        );
        // Older soft activity than the hard base is irrelevant.
        assert_eq!(
            capped_observed_at(&times(Some(10 * HOUR), Some(5 * HOUR)), w, 2),
            10 * HOUR
        );
        assert_eq!(capped_observed_at(&times(None, Some(HOUR)), w, 0), 0);
        assert_eq!(
            capped_observed_at(&times(None, Some(99 * HOUR)), None, 2),
            99 * HOUR
        );
    }

    // frob:tests observation_for
    #[test]
    fn touching_agent_is_evictable_after_soft_cap() {
        let w = ClaimWindows::default();
        let t = times(None, Some(100 * HOUR));
        let o = observation_for(&w, &t, HolderKind::Agent, Class::Standard, None);
        assert_eq!(o.observed_at, 4 * HOUR);
        // Evictable once soft_max_windows (2) windows of 4h have passed since the claim.
        assert_ne!(w.status(&o, 7 * HOUR, 0).level, IdleLevel::Evictable);
        assert_eq!(w.status(&o, 8 * HOUR, 0).level, IdleLevel::Evictable);
    }

    // frob:tests rekind
    #[test]
    fn rekind_switches_to_human_window() {
        let w = ClaimWindows::default();
        let agent = ClaimObservation {
            observed_at: 0,
            holder: HolderKind::Agent,
            class: Class::Standard,
            ticket_idle_days: None,
        };
        assert_eq!(w.status(&agent, 5 * HOUR, 0).level, IdleLevel::Evictable);
        let human = rekind(&agent, HolderKind::Human, 5 * HOUR);
        assert_eq!(human.holder, HolderKind::Human);
        assert_ne!(w.status(&human, 6 * HOUR, 0).level, IdleLevel::Evictable);
        assert_eq!(rekind(&human, HolderKind::Human, 9 * HOUR), human);
    }
}
