//! Claim holds and pauses (`distributed-tickets.md` sections 4.2 and 4.7): the pure rules that stop a claim's idle clock.
//!
//! A hold is a person's promise ("on leave until 2026-11-03") capped by `[claims] max_hold_days`; a pause is a
//! condition ("blocked by ~Y", queued, in review, refused by CI) capped by `[claims] paused_max_days`. Both feed
//! [`effective_observation`], which moves the observation the idle arithmetic of [`crate::claim_window`] reads.
//! Nothing here reads a clock or writes a `lease` event: callers hand in `now` and persist the result.

// frob:ticket 01M5CW0557C2HYG7KZBV3Y6VBJ

use gob_time::Day;
use tracing::{debug, info, warn};

use crate::claim_window::{ClaimObservation, ClaimWindows};

/// Seconds in a day.
const DAY: i64 = 86_400;

/// Why a hold request was refused.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum HoldError {
    /// A hold needs a stated reason.
    #[error("a hold needs a reason (--reason TEXT)")]
    EmptyReason,
    /// The end date is not after now.
    #[error("hold end date {0} is not in the future")]
    NotFuture(Day),
    /// The hold would outlast `[claims] max_hold_days`.
    #[error("hold until {until} is {asked_days} days away; [claims] max_hold_days is {max_days}")]
    TooLong {
        /// The requested end date.
        until: Day,
        /// Whole days from now to the end date.
        asked_days: i64,
        /// The configured cap.
        max_days: i64,
    },
}

/// A claim hold: the idle clock is stopped from `started_at` until `until` or an early resume.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Hold {
    /// Local epoch seconds at which the hold began.
    pub started_at: i64,
    /// Epoch seconds at which the hold ends (the end of the given day in the writer's zone).
    pub until: i64,
    /// Why the holder is away.
    pub reason: String,
    /// Epoch seconds of an early `frob claim resume`, when one happened.
    pub resumed_at: Option<i64>,
}

impl Hold {
    /// Validate and build a hold ending at the end of `day` in the zone `utc_offset_secs` east of UTC.
    ///
    /// # Errors
    ///
    /// [`HoldError`] for an empty reason, a day that is already over, or a hold past `max_hold_days`.
    pub fn new(
        now: i64,
        day: Day,
        reason: &str,
        utc_offset_secs: i64,
        windows: &ClaimWindows,
    ) -> Result<Self, HoldError> {
        if reason.trim().is_empty() {
            warn!("claim hold refused: empty reason");
            return Err(HoldError::EmptyReason);
        }
        let until = (day.days_since(Day::from_unix(0)) + 1) * DAY - utc_offset_secs;
        if until <= now {
            warn!(%day, "claim hold refused: end date not in the future");
            return Err(HoldError::NotFuture(day));
        }
        let max = windows.max_hold_secs();
        if until - now > max {
            warn!(%day, max, "claim hold refused: past max_hold_days");
            return Err(HoldError::TooLong {
                until: day,
                asked_days: (until - now + DAY - 1) / DAY,
                max_days: max / DAY,
            });
        }
        info!(%day, "claim hold accepted");
        Ok(Self {
            started_at: now,
            until,
            reason: reason.trim().to_owned(),
            resumed_at: None,
        })
    }

    /// When the clock stopped counting: the early resume or the end date, whichever came first.
    #[must_use]
    pub fn ends_at(&self) -> i64 {
        self.resumed_at.map_or(self.until, |r| r.min(self.until))
    }

    /// True while the hold still stops the clock at `now`.
    #[must_use]
    pub fn is_active(&self, now: i64) -> bool {
        now < self.ends_at()
    }

    /// End the hold early at `now` (`frob claim resume`); a hold already over is left as it was.
    pub fn resume(&mut self, now: i64) {
        if self.is_active(now) {
            info!(now, "claim hold resumed early");
            self.resumed_at = Some(now);
        }
    }

    /// `held until 2026-11-03 (on leave)`, the line every clone shows while the hold is active.
    #[must_use]
    pub fn notice(&self, handle: &str, utc_offset_secs: i64) -> String {
        format!(
            "{handle} held until {} ({})",
            Day::from_unix(self.until - 1 + utc_offset_secs),
            self.reason
        )
    }
}

/// What a pause is waiting on.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PauseKind {
    /// An open `blocked-by` link to a ticket not done.
    Blocked,
    /// A review requested and not answered.
    Review,
    /// Queued on the land train.
    Train,
    /// A recorded land attempt refused by base CI.
    Ci,
}

impl PauseKind {
    /// The word the notice uses.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Blocked => "blocked",
            Self::Review => "in review",
            Self::Train => "queued",
            Self::Ci => "CI refused",
        }
    }
}

/// One pause: the clock stops from `since` for at most `[claims] paused_max_days`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pause {
    /// What the claim waits on.
    pub kind: PauseKind,
    /// Local epoch seconds at which the pause began.
    pub since: i64,
    /// The blocker named in the notice, such as `~Y`; empty when there is none.
    pub by: String,
}

impl Pause {
    /// Seconds of idle time this pause forgives at `now`, never more than the cap and never negative.
    #[must_use]
    pub fn credit_secs(&self, now: i64, windows: &ClaimWindows) -> i64 {
        (now - self.since).clamp(0, windows.paused_max_secs())
    }

    /// True once the cap is used up and warnings resume although the pause still stands.
    #[must_use]
    pub fn is_capped(&self, now: i64, windows: &ClaimWindows) -> bool {
        now - self.since >= windows.paused_max_secs()
    }

    /// `paused: blocked by ~Y (day 4 of 14)`, or `paused: blocked, cap reached; claim hold if longer` past the cap.
    #[must_use]
    pub fn notice(&self, now: i64, windows: &ClaimWindows) -> String {
        let by = if self.by.is_empty() {
            String::new()
        } else {
            format!(" by {}", self.by)
        };
        if self.is_capped(now, windows) {
            format!(
                "paused: {}{by}, cap of {} days reached; frob claim hold if it will be longer",
                self.kind.label(),
                windows.paused_max_secs() / DAY
            )
        } else {
            format!(
                "paused: {}{by} (day {} of {})",
                self.kind.label(),
                (now - self.since).max(0) / DAY + 1,
                windows.paused_max_secs() / DAY
            )
        }
    }
}

/// The observation the idle arithmetic should see once a hold and the pauses are taken into account.
///
/// An active hold pins the clock at zero; a hold that ended (expiry or early resume) restarts it from the end
/// moment; each pause then shifts the first-seen time forward by its capped credit, counted only from the later
/// of the pause start and the observation, and never past `now`.
#[must_use]
pub fn effective_observation(
    obs: &ClaimObservation,
    hold: Option<&Hold>,
    pauses: &[Pause],
    now: i64,
    windows: &ClaimWindows,
) -> ClaimObservation {
    let mut observed_at = obs.observed_at;
    if let Some(h) = hold.filter(|h| h.ends_at() > observed_at) {
        if h.is_active(now) {
            debug!("claim idle clock held");
            return ClaimObservation {
                observed_at: now,
                ..obs.clone()
            };
        }
        observed_at = observed_at.max(h.ends_at());
    }
    let credit: i64 = pauses
        .iter()
        .map(|p| {
            let since = p.since.max(observed_at);
            Pause { since, ..p.clone() }.credit_secs(now, windows)
        })
        .sum();
    debug!(credit, "claim idle clock paused");
    ClaimObservation {
        observed_at: (observed_at + credit).min(now),
        ..obs.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::claim_window::{HolderKind, IdleLevel};
    use crate::model::Class;

    const NOW: i64 = 20_000 * DAY + 3600;

    fn obs(observed_at: i64) -> ClaimObservation {
        ClaimObservation {
            observed_at,
            holder: HolderKind::Human,
            class: Class::Standard,
            ticket_idle_days: None,
        }
    }

    fn day(offset: i64) -> Day {
        Day::from_unix(NOW + offset * DAY)
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::Hold.new
    #[test]
    fn hold_validation() {
        let w = ClaimWindows::default();
        let h = Hold::new(NOW, day(2), " on leave ", 0, &w).unwrap();
        assert_eq!(h.reason, "on leave");
        assert_eq!(h.until, 20_003 * DAY);
        assert_eq!(
            Hold::new(NOW, day(2), "  ", 0, &w),
            Err(HoldError::EmptyReason)
        );
        assert_eq!(
            Hold::new(NOW, day(-1), "x", 0, &w),
            Err(HoldError::NotFuture(day(-1)))
        );
        assert!(Hold::new(NOW, day(29), "x", 0, &w).is_ok());
        assert!(matches!(
            Hold::new(NOW, day(31), "x", 0, &w),
            Err(HoldError::TooLong { max_days: 30, .. })
        ));
        // A zone east of UTC ends the day earlier in UTC terms.
        let east = Hold::new(NOW, day(2), "x", 3600, &w).unwrap();
        assert_eq!(east.until, 20_003 * DAY - 3600);
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::Hold.resume
    #[test]
    fn resume_ends_early_once() {
        let w = ClaimWindows::default();
        let mut h = Hold::new(NOW, day(5), "x", 0, &w).unwrap();
        assert!(h.is_active(NOW + DAY));
        h.resume(NOW + DAY);
        assert!(!h.is_active(NOW + DAY));
        assert_eq!(h.ends_at(), NOW + DAY);
        h.resume(NOW + 2 * DAY);
        assert_eq!(h.resumed_at, Some(NOW + DAY));
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::Hold.notice
    #[test]
    fn hold_notice_names_end_date() {
        let w = ClaimWindows::default();
        let h = Hold::new(NOW, day(2), "on leave", 0, &w).unwrap();
        let n = h.notice("~X", 0);
        assert_eq!(n, format!("~X held until {} (on leave)", day(2)));
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::effective_observation
    #[test]
    fn hold_stops_then_restarts_the_clock() {
        let w = ClaimWindows::default();
        let start = NOW - 2 * DAY;
        let h = Hold::new(NOW, day(5), "x", 0, &w).unwrap();
        let during = effective_observation(&obs(start), Some(&h), &[], NOW + DAY, &w);
        assert_eq!(w.status(&during, NOW + DAY, 0).idle_secs, 0);
        // After expiry the clock restarts from zero at the end date.
        let after = effective_observation(&obs(start), Some(&h), &[], h.until + DAY, &w);
        assert_eq!(w.status(&after, h.until + DAY, 0).idle_secs, DAY);
        // Activity after the hold ended wins over the hold.
        let later = obs(h.until + 100);
        let kept = effective_observation(&later, Some(&h), &[], h.until + DAY, &w);
        assert_eq!(kept.observed_at, h.until + 100);
        // An early resume restarts from the resume moment.
        let mut r = h.clone();
        r.resume(NOW + DAY);
        let early = effective_observation(&obs(start), Some(&r), &[], NOW + 2 * DAY, &w);
        assert_eq!(w.status(&early, NOW + 2 * DAY, 0).idle_secs, DAY);
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::Pause.credit_secs
    #[test]
    fn pause_credit_is_capped() {
        let w = ClaimWindows::default();
        let p = Pause {
            kind: PauseKind::Blocked,
            since: NOW,
            by: "~Y".to_owned(),
        };
        assert_eq!(p.credit_secs(NOW - 5, &w), 0);
        assert_eq!(p.credit_secs(NOW + 4 * DAY, &w), 4 * DAY);
        assert_eq!(p.credit_secs(NOW + 40 * DAY, &w), 14 * DAY);
        assert!(!p.is_capped(NOW + 13 * DAY, &w));
        assert!(p.is_capped(NOW + 14 * DAY, &w));
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::Pause.notice
    #[test]
    fn pause_notices() {
        let w = ClaimWindows::default();
        let p = Pause {
            kind: PauseKind::Blocked,
            since: NOW,
            by: "~Y".to_owned(),
        };
        assert_eq!(
            p.notice(NOW + 3 * DAY, &w),
            "paused: blocked by ~Y (day 4 of 14)"
        );
        assert!(p.notice(NOW + 15 * DAY, &w).contains("cap of 14 days"));
        let q = Pause {
            kind: PauseKind::Train,
            since: NOW,
            by: String::new(),
        };
        assert_eq!(q.notice(NOW, &w), "paused: queued (day 1 of 14)");
        assert_eq!(PauseKind::Review.label(), "in review");
        assert_eq!(PauseKind::Ci.label(), "CI refused");
    }

    // frob:tests crates/frob-ledger/src/claim_hold.rs::effective_observation
    #[test]
    fn pauses_stop_the_clock_until_the_cap() {
        let w = ClaimWindows::default();
        let start = NOW - DAY;
        let p = Pause {
            kind: PauseKind::Blocked,
            since: NOW,
            by: String::new(),
        };
        // Blocked for 10 days: idle stays at the 1 day seen before the pause.
        let e = effective_observation(
            &obs(start),
            None,
            std::slice::from_ref(&p),
            NOW + 10 * DAY,
            &w,
        );
        assert_eq!(w.status(&e, NOW + 10 * DAY, 0).idle_secs, DAY);
        // 20 days: 14 forgiven, 6 + 1 count, so the window of 3 days has passed.
        let e = effective_observation(
            &obs(start),
            None,
            std::slice::from_ref(&p),
            NOW + 20 * DAY,
            &w,
        );
        let s = w.status(&e, NOW + 20 * DAY, 0);
        assert_eq!(s.idle_secs, 7 * DAY);
        assert_eq!(s.level, IdleLevel::Evictable);
        // A pause that began before the last activity forgives only time since the activity.
        let old = Pause {
            since: start - 5 * DAY,
            ..p
        };
        let e = effective_observation(&obs(start), None, &[old], NOW, &w);
        assert_eq!(e.observed_at, NOW);
    }
}
