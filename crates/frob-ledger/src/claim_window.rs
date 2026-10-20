//! Claim idle windows and warnings (`distributed-tickets.md` sections 4.1 and 4.4): the `[claims]` tables and the pure arithmetic that turns "first observed here at T" into a window, a fraction and a warning.
//!
//! Nothing here reads a clock, a clone's observation file or the network: callers hand in a [`ClaimObservation`]
//! and a local `now`, so the activity-observation code can feed it later without this module knowing about it.

// frob:ticket 01M5CW04YABDJW6ZXSWFGTCB9E

use gob_config::ConfigTable;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use tracing::{debug, warn};

use crate::model::Class;

/// Seconds in an hour.
const HOUR: i64 = 3600;

/// Seconds in a day.
const DAY: i64 = 86_400;

/// How idle time is counted (`[claims] count`, decision D-3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum CountKnob {
    /// Every calendar day counts.
    All,
    /// Saturdays and Sundays (in the observer's timezone) do not count.
    Weekdays,
}

/// How long a claim may sit idle before it is evictable (`[claims]`).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "claims", materialize)]
pub struct ClaimsTable {
    /// Calendar days a human claim may sit idle before it is evictable; 0 means never evict.
    #[config(default = 3)]
    pub idle_days: u32,
    /// `all` counts every calendar day as idle time; `weekdays` skips Saturday and Sunday.
    #[config(default = CountKnob::All)]
    pub count: CountKnob,
    /// Hours a claim held by an agent (`FROB_AGENT` set at claim time) may sit idle; 0 means never evict.
    #[config(default = 4)]
    pub agent_idle_hours: u32,
    /// Fractions of the window (each above 0 and below 1) at which the holder is warned.
    #[config(default = vec![0.5, 0.8])]
    pub warn_at: Vec<f64>,
    /// Longest hold, in days, `frob claim hold` accepts.
    #[config(default = 30)]
    pub max_hold_days: u32,
    /// Longest stretch, in days, a blocked, review, train or CI pause stops the idle clock.
    #[config(default = 14)]
    pub paused_max_days: u32,
}

/// Per-class idle windows in days (`[claims.class]`); they override `idle_days`, and 0 means never evict.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "claims.class", materialize)]
pub struct ClaimsClassTable {
    /// Days an expedite claim may sit idle: a critical fix must not be parked on someone's absence.
    #[config(default = 1)]
    pub expedite: u32,
    /// Days an intangible claim (chores, debt) may sit idle: slow upkeep gets a longer leash.
    #[config(default = 7)]
    pub intangible: u32,
}

/// Who holds a claim, which fixes the window kind at claim time.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HolderKind {
    /// A person: the `idle_days` window.
    Human,
    /// An agent harness: the `agent_idle_hours` window.
    Agent,
}

/// The validated `[claims]` and `[claims.class]` settings the window arithmetic reads.
#[derive(Debug, Clone, PartialEq)]
pub struct ClaimWindows {
    human_days: u32,
    agent_hours: u32,
    count: CountKnob,
    expedite_days: u32,
    intangible_days: u32,
    warn_at: Vec<f64>,
    max_hold_days: u32,
    paused_max_days: u32,
}

impl Default for ClaimWindows {
    fn default() -> Self {
        Self {
            human_days: 3,
            agent_hours: 4,
            count: CountKnob::All,
            expedite_days: 1,
            intangible_days: 7,
            warn_at: vec![0.5, 0.8],
            max_hold_days: 30,
            paused_max_days: 14,
        }
    }
}

impl ClaimWindows {
    /// Validate the two tables: `warn_at` must be strictly ascending fractions in (0, 1).
    ///
    /// # Errors
    ///
    /// A message naming the bad `[claims] warn_at` entry.
    pub fn from_tables(claims: &ClaimsTable, class: &ClaimsClassTable) -> Result<Self, String> {
        let mut prev = 0.0_f64;
        for &f in &claims.warn_at {
            if !(f > prev && f < 1.0) {
                warn!(value = f, "claims warn_at rejected");
                return Err(format!(
                    "[claims] warn_at entry {f} must be above 0, below 1 and larger than the one before it"
                ));
            }
            prev = f;
        }
        debug!(idle_days = claims.idle_days, agent_hours = claims.agent_idle_hours, count = ?claims.count, "claim windows read");
        Ok(Self {
            human_days: claims.idle_days,
            agent_hours: claims.agent_idle_hours,
            count: claims.count,
            expedite_days: class.expedite,
            intangible_days: class.intangible,
            warn_at: claims.warn_at.clone(),
            max_hold_days: claims.max_hold_days,
            paused_max_days: claims.paused_max_days,
        })
    }

    /// The longest hold in seconds (`[claims] max_hold_days`).
    #[must_use]
    pub fn max_hold_secs(&self) -> i64 {
        i64::from(self.max_hold_days) * DAY
    }

    /// The longest a pause stops the idle clock, in seconds (`[claims] paused_max_days`).
    #[must_use]
    pub fn paused_max_secs(&self) -> i64 {
        i64::from(self.paused_max_days) * DAY
    }

    /// The idle window in seconds, `None` when it is "never evict".
    ///
    /// Resolution order: the ticket's `claim_idle_days` field, then the class table, then the agent or human default; 0 at any level wins as never.
    #[must_use]
    pub fn window_secs(
        &self,
        holder: HolderKind,
        class: Class,
        ticket_days: Option<u32>,
    ) -> Option<i64> {
        let days = ticket_days.or(match class {
            Class::Expedite => Some(self.expedite_days),
            Class::Intangible => Some(self.intangible_days),
            Class::FixedDate | Class::Standard => None,
        });
        let secs = match (days, holder) {
            (Some(d), _) => i64::from(d) * DAY,
            (None, HolderKind::Human) => i64::from(self.human_days) * DAY,
            (None, HolderKind::Agent) => i64::from(self.agent_hours) * HOUR,
        };
        (secs > 0).then_some(secs)
    }

    /// Idle seconds between the local first observation and `now`, skipping weekends under `count = weekdays`.
    ///
    /// `utc_offset_secs` is the observer's zone; a clock that went backwards clamps to zero.
    #[must_use]
    pub fn idle_secs(&self, observed_at: i64, now: i64, utc_offset_secs: i64) -> i64 {
        if now <= observed_at {
            return 0;
        }
        match self.count {
            CountKnob::All => now - observed_at,
            CountKnob::Weekdays => weekday_secs(observed_at, now, utc_offset_secs),
        }
    }

    /// The status of one claim: how far into its window it is and which warning level that reaches.
    #[must_use]
    pub fn status(&self, obs: &ClaimObservation, now: i64, utc_offset_secs: i64) -> IdleStatus {
        let idle = self.idle_secs(obs.observed_at, now, utc_offset_secs);
        let window = self.window_secs(obs.holder, obs.class, obs.ticket_idle_days);
        let (level, remaining) = match window {
            None => (IdleLevel::Quiet, None),
            Some(w) if idle >= w => (IdleLevel::Evictable, Some(0)),
            Some(w) => {
                let reached = self
                    .warn_at
                    .iter()
                    .rposition(|f| fraction_reached(idle, w, *f));
                let level = reached.map_or(IdleLevel::Quiet, |index| IdleLevel::Warn {
                    index,
                    urgent: index + 1 == self.warn_at.len(),
                });
                (level, Some(w - idle))
            }
        };
        debug!(idle, ?window, ?level, "claim idle status computed");
        IdleStatus {
            idle_secs: idle,
            window_secs: window,
            remaining_secs: remaining,
            level,
        }
    }
}

/// True when `idle` has reached fraction `f` of `window`.
fn fraction_reached(idle: i64, window: i64, f: f64) -> bool {
    #[allow(clippy::cast_precision_loss)]
    let (i, w) = (idle as f64, window as f64);
    i >= w * f
}

/// Seconds in `[from, to)` that fall on a Monday to Friday in the zone `offset` seconds east of UTC.
fn weekday_secs(from: i64, to: i64, offset: i64) -> i64 {
    let mut total = 0;
    let mut t = from;
    while t < to {
        let local = t + offset;
        let day_end = local.div_euclid(DAY) * DAY + DAY - offset;
        let end = day_end.min(to);
        // 1970-01-01 was a Thursday: day 0 is index 3 of Monday = 0.
        let weekday = (local.div_euclid(DAY) + 3).rem_euclid(7);
        if weekday < 5 {
            total += end - t;
        }
        t = end;
    }
    total
}

/// What one claim looks like to this clone: the inputs of [`ClaimWindows::status`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimObservation {
    /// Local epoch seconds at which this clone first saw the claim's latest activity.
    pub observed_at: i64,
    /// Whether an agent or a person holds the claim.
    pub holder: HolderKind,
    /// The ticket's class of service.
    pub class: Class,
    /// The ticket's `claim_idle_days` field, when set.
    pub ticket_idle_days: Option<u32>,
}

/// How far a claim has run into its window.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdleLevel {
    /// Below the first warning fraction, or a window of "never".
    Quiet,
    /// At or past `warn_at[index]`; `urgent` when that is the last configured fraction.
    Warn {
        /// Position in `[claims] warn_at`; also the threshold an acknowledgement silences.
        index: usize,
        /// The final warning before the claim is evictable.
        urgent: bool,
    },
    /// The window has passed.
    Evictable,
}

/// The computed state of one claim's idle clock.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct IdleStatus {
    /// Idle seconds counted under `count`.
    pub idle_secs: i64,
    /// The window, `None` for never.
    pub window_secs: Option<i64>,
    /// Seconds until evictable (0 once it is), `None` for never.
    pub remaining_secs: Option<i64>,
    /// The warning level reached.
    pub level: IdleLevel,
}

impl IdleStatus {
    /// The threshold rank: `warn_at` index plus one for a warning, `usize::MAX` once evictable, 0 when quiet; acknowledgements compare against it.
    #[must_use]
    pub fn rank(&self) -> usize {
        match self.level {
            IdleLevel::Quiet => 0,
            IdleLevel::Warn { index, .. } => index + 1,
            IdleLevel::Evictable => usize::MAX,
        }
    }

    /// True when this status deserves a notice given the rank the holder last acknowledged (`None` for never).
    #[must_use]
    pub fn needs_notice(&self, acked_rank: Option<usize>) -> bool {
        self.rank() > acked_rank.unwrap_or(0)
    }

    /// `1.5 of 3 days` or `2 of 4 hours`: idle against the window, in the unit the window is naturally given in.
    #[must_use]
    pub fn idle_of_window(&self) -> String {
        let Some(w) = self.window_secs else {
            return "never".to_owned();
        };
        let (unit, per) = if w % DAY == 0 {
            ("days", DAY)
        } else {
            ("hours", HOUR)
        };
        #[allow(clippy::cast_precision_loss)]
        let (i, w) = (self.idle_secs as f64 / per as f64, w / per);
        format!("{} of {w} {unit}", trim_decimal(i))
    }
}

/// One decimal place with a trailing `.0` dropped.
fn trim_decimal(v: f64) -> String {
    let s = format!("{v:.1}");
    s.strip_suffix(".0").map_or(s.clone(), str::to_owned)
}

/// A short duration: `14h`, `3d`, or `40m`.
fn short_duration(secs: i64) -> String {
    if secs >= DAY {
        format!("{}d", secs / DAY)
    } else if secs >= HOUR {
        format!("{}h", secs / HOUR)
    } else {
        format!("{}m", secs.max(0) / 60)
    }
}

/// The holder's line for one claim (`W-CLAIM-IDLE` at a warning level, an evictable line at 100%), `None` when quiet.
#[must_use]
pub fn holder_notice(handle: &str, status: &IdleStatus) -> Option<String> {
    match status.level {
        IdleLevel::Quiet => None,
        IdleLevel::Warn { urgent, .. } => Some(format!(
            "W-CLAIM-IDLE{}: {handle} idle {}; push, comment, or frob claim touch {handle} --note ...; going away? frob claim hold {handle} --until DATE --reason ...",
            if urgent { " (urgent)" } else { "" },
            status.idle_of_window(),
        )),
        IdleLevel::Evictable => Some(format!("{handle} evictable now")),
    }
}

/// What other people see on the board and in `doable`: nothing before the last warning fraction, then `evictable in 14h`, then `evictable now`.
#[must_use]
pub fn others_notice(handle: &str, status: &IdleStatus) -> Option<String> {
    match status.level {
        IdleLevel::Warn { urgent: true, .. } => status
            .remaining_secs
            .map(|r| format!("{handle} evictable in {}", short_duration(r))),
        IdleLevel::Evictable => Some(format!("{handle} evictable now")),
        IdleLevel::Quiet | IdleLevel::Warn { .. } => None,
    }
}

/// One claim with its handle and computed status, ready for aggregation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimNotice {
    /// The ticket handle, `~X`.
    pub handle: String,
    /// The computed idle status.
    pub status: IdleStatus,
    /// The rank the holder last acknowledged (`frob claim notices`), `None` for never.
    pub acked_rank: Option<usize>,
}

/// One aggregated line per verb for a holder with several idle claims, `None` when nothing needs saying.
///
/// A single claim gets its full [`holder_notice`]; several are summed into `W-CLAIM-IDLE: N claims idle: ~A (1.5 of 3 days), ...`.
/// Acknowledged claims stay silent until they reach a higher threshold.
#[must_use]
pub fn aggregate_holder_notice(claims: &[ClaimNotice]) -> Option<String> {
    let mut due: Vec<&ClaimNotice> = claims
        .iter()
        .filter(|c| c.status.needs_notice(c.acked_rank))
        .collect();
    due.sort_by_key(|c| std::cmp::Reverse(c.status.rank()));
    match due.as_slice() {
        [] => None,
        [one] => holder_notice(&one.handle, &one.status),
        many => {
            let urgent = many.iter().any(|c| {
                matches!(
                    c.status.level,
                    IdleLevel::Warn { urgent: true, .. } | IdleLevel::Evictable
                )
            });
            let list = many
                .iter()
                .map(|c| format!("{} ({})", c.handle, c.status.idle_of_window()))
                .collect::<Vec<_>>()
                .join(", ");
            Some(format!(
                "W-CLAIM-IDLE{}: {} claims idle: {list}; frob claim notices lists them",
                if urgent { " (urgent)" } else { "" },
                many.len(),
            ))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOON_MON: i64 = 4 * DAY + 12 * HOUR; // 1970-01-05 12:00 UTC, a Monday

    fn human(observed_at: i64) -> ClaimObservation {
        ClaimObservation {
            observed_at,
            holder: HolderKind::Human,
            class: Class::Standard,
            ticket_idle_days: None,
        }
    }

    // frob:tests crates/frob-ledger/src/claim_window.rs::ClaimWindows.window_secs
    #[test]
    fn window_resolution_order_and_never() {
        let w = ClaimWindows::default();
        let s = |h, c, t| w.window_secs(h, c, t);
        assert_eq!(s(HolderKind::Human, Class::Standard, None), Some(3 * DAY));
        assert_eq!(s(HolderKind::Agent, Class::Standard, None), Some(4 * HOUR));
        assert_eq!(s(HolderKind::Human, Class::Expedite, None), Some(DAY));
        assert_eq!(s(HolderKind::Human, Class::Intangible, None), Some(7 * DAY));
        assert_eq!(s(HolderKind::Agent, Class::Expedite, None), Some(DAY));
        assert_eq!(
            s(HolderKind::Human, Class::Expedite, Some(9)),
            Some(9 * DAY)
        );
        assert_eq!(s(HolderKind::Human, Class::Expedite, Some(0)), None);
    }

    // frob:tests crates/frob-ledger/src/claim_window.rs::ClaimWindows.from_tables
    #[test]
    fn tables_default_and_validate_warn_at() {
        let dir = tempfile::tempdir().unwrap();
        let c = gob_config::load::<ClaimsTable>(dir.path(), "frob")
            .unwrap()
            .value;
        let k = gob_config::load::<ClaimsClassTable>(dir.path(), "frob")
            .unwrap()
            .value;
        assert_eq!(
            ClaimWindows::from_tables(&c, &k).unwrap(),
            ClaimWindows::default()
        );
        std::fs::write(
            dir.path().join("frob.toml"),
            "[claims]\nidle_days = 5\ncount = \"weekdays\"\nwarn_at = [0.25]\n[claims.class]\nexpedite = 0\n",
        )
        .unwrap();
        let c = gob_config::load::<ClaimsTable>(dir.path(), "frob")
            .unwrap()
            .value;
        let k = gob_config::load::<ClaimsClassTable>(dir.path(), "frob")
            .unwrap()
            .value;
        let w = ClaimWindows::from_tables(&c, &k).unwrap();
        assert_eq!(
            w.window_secs(HolderKind::Human, Class::Standard, None),
            Some(5 * DAY)
        );
        assert_eq!(
            w.window_secs(HolderKind::Human, Class::Expedite, None),
            None
        );
        let bad = ClaimsTable {
            warn_at: vec![0.8, 0.5],
            ..c.clone()
        };
        assert!(ClaimWindows::from_tables(&bad, &k).is_err());
        let bad = ClaimsTable {
            warn_at: vec![1.0],
            ..c
        };
        assert!(ClaimWindows::from_tables(&bad, &k).is_err());
    }

    // frob:tests crates/frob-ledger/src/claim_window.rs::ClaimWindows.idle_secs
    #[test]
    fn weekdays_skip_the_weekend_and_clock_jumps_clamp() {
        let all = ClaimWindows::default();
        let wk = ClaimWindows {
            count: CountKnob::Weekdays,
            ..ClaimWindows::default()
        };
        let fri_noon = NOON_MON + 4 * DAY;
        let mon_noon = NOON_MON + 7 * DAY;
        assert_eq!(all.idle_secs(fri_noon, mon_noon, 0), 3 * DAY);
        // Friday noon to Monday noon: 12h Friday + 12h Monday.
        assert_eq!(wk.idle_secs(fri_noon, mon_noon, 0), DAY);
        assert_eq!(wk.idle_secs(NOON_MON, NOON_MON + 2 * HOUR, 0), 2 * HOUR);
        assert_eq!(all.idle_secs(mon_noon, fri_noon, 0), 0);
        // A zone far east shifts which instants are weekend: Fri 20:00 UTC is Sat 06:00 at +10h.
        let fri_20 = NOON_MON + 4 * DAY + 8 * HOUR;
        assert_eq!(wk.idle_secs(fri_20, fri_20 + 42 * HOUR, 10 * HOUR), 0);
    }

    // frob:tests crates/frob-ledger/src/claim_window.rs::ClaimWindows.status
    #[test]
    fn status_levels_follow_warn_at() {
        let w = ClaimWindows::default();
        let at = |idle: i64| w.status(&human(0), idle, 0);
        assert_eq!(at(DAY).level, IdleLevel::Quiet);
        assert_eq!(
            at(3 * DAY / 2).level,
            IdleLevel::Warn {
                index: 0,
                urgent: false
            }
        );
        assert_eq!(at(3 * DAY / 2).remaining_secs, Some(3 * DAY / 2));
        assert_eq!(
            at(3 * DAY * 8 / 10).level,
            IdleLevel::Warn {
                index: 1,
                urgent: true
            }
        );
        assert_eq!(at(3 * DAY).level, IdleLevel::Evictable);
        let never = ClaimObservation {
            ticket_idle_days: Some(0),
            ..human(0)
        };
        let s = w.status(&never, 100 * DAY, 0);
        assert_eq!(
            (s.level, s.window_secs, s.remaining_secs),
            (IdleLevel::Quiet, None, None)
        );
        assert!(!s.needs_notice(None));
    }

    // frob:tests crates/frob-ledger/src/claim_window.rs::holder_notice
    // frob:tests crates/frob-ledger/src/claim_window.rs::others_notice
    // frob:tests crates/frob-ledger/src/claim_window.rs::IdleStatus.idle_of_window
    #[test]
    fn notice_texts_by_audience() {
        let w = ClaimWindows::default();
        let half = w.status(&human(0), 3 * DAY / 2, 0);
        let text = holder_notice("~X", &half).unwrap();
        assert!(
            text.starts_with(
                "W-CLAIM-IDLE: ~X idle 1.5 of 3 days; push, comment, or frob claim touch ~X --note"
            ),
            "{text}"
        );
        assert!(text.contains("frob claim hold ~X --until DATE --reason"));
        assert_eq!(others_notice("~X", &half), None);

        let late = w.status(&human(0), 3 * DAY - 14 * HOUR, 0);
        assert!(
            holder_notice("~X", &late)
                .unwrap()
                .starts_with("W-CLAIM-IDLE (urgent): ")
        );
        assert_eq!(
            others_notice("~X", &late).as_deref(),
            Some("~X evictable in 14h")
        );

        let done = w.status(&human(0), 4 * DAY, 0);
        assert_eq!(
            holder_notice("~X", &done).as_deref(),
            Some("~X evictable now")
        );
        assert_eq!(
            others_notice("~X", &done).as_deref(),
            Some("~X evictable now")
        );

        let agent = ClaimObservation {
            holder: HolderKind::Agent,
            ..human(0)
        };
        let a = w.status(&agent, 2 * HOUR, 0);
        assert!(
            holder_notice("~A", &a)
                .unwrap()
                .contains("idle 2 of 4 hours")
        );
        assert_eq!(holder_notice("~X", &w.status(&human(0), HOUR, 0)), None);
    }

    // frob:tests crates/frob-ledger/src/claim_window.rs::aggregate_holder_notice
    // frob:tests crates/frob-ledger/src/claim_window.rs::IdleStatus.needs_notice
    #[test]
    fn notices_aggregate_and_acknowledgement_silences_until_next_threshold() {
        let w = ClaimWindows::default();
        let mk = |h: &str, idle, acked| ClaimNotice {
            handle: h.to_owned(),
            status: w.status(&human(0), idle, 0),
            acked_rank: acked,
        };
        assert_eq!(aggregate_holder_notice(&[]), None);
        assert_eq!(aggregate_holder_notice(&[mk("~A", DAY, None)]), None);

        let a = mk("~A", 3 * DAY / 2, None);
        let b = mk("~B", 3 * DAY * 8 / 10, None);
        let line = aggregate_holder_notice(&[a.clone(), b.clone()]).unwrap();
        assert_eq!(
            line,
            "W-CLAIM-IDLE (urgent): 2 claims idle: ~B (2.4 of 3 days), ~A (1.5 of 3 days); frob claim notices lists them"
        );

        // Acknowledging the 50% warning silences ~A but not the later 80% one on ~B.
        let a_acked = ClaimNotice {
            acked_rank: Some(a.status.rank()),
            ..a
        };
        let only_b = aggregate_holder_notice(&[a_acked.clone(), b]).unwrap();
        assert!(
            only_b.starts_with("W-CLAIM-IDLE (urgent): ~B idle 2.4 of 3 days;"),
            "{only_b}"
        );
        assert_eq!(aggregate_holder_notice(&[a_acked]), None);
    }
}
