//! The one forecast (D104): a Monte Carlo over the measured throughput and cycle-time samples.
//!
//! [`forecast`] runs a fixed number of seeded trials. Each trial draws the open work (unsized
//! tickets get a size bootstrapped from finished work), burns it down with bootstrapped weekly
//! throughput, and races that against the dependency chain (a sum of bootstrapped cycle times);
//! the later of the two is the trial's finish. P50/P85/P95 of the trials are the answer, and the
//! side that bound most often (plus how much of the work was unsized) names the dominant risk.
//! Below `[pm] min_history` finished tickets the figure is Unresolved with the sample count.
//! [`forecast_line`] is the single renderer `release status` and `ticket show` both print.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use schemars::JsonSchema;
use serde::Serialize;

use crate::figure::Figure;
use crate::percentile::{Percentiles, percentiles};
use crate::report::{TicketFact, TicketState};

/// Trials per forecast.
pub const TRIALS: u32 = 10_000;

/// Weeks of finished work the throughput is bootstrapped from.
pub const HISTORY_WEEKS: usize = 8;

/// Upper bound on simulated weeks, so a degenerate sample cannot loop forever.
const MAX_WEEKS: f64 = 520.0;

/// Seconds in a day.
const DAY_SECS: i64 = 86_400;

/// Seed used by the CLI so the same history always yields the same dates.
pub const DEFAULT_SEED: u64 = 0x000F_0BF0_CA57_D104;

/// What most delays the finish.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Risk {
    /// A chain of blocked-by tickets takes longer than the work does.
    DependencyChain,
    /// The team's throughput is the limit.
    Capacity,
    /// Most of the remaining work has no estimate.
    UnsizedWork,
}

impl Risk {
    /// The words used in the forecast line.
    pub const fn describe(self) -> &'static str {
        match self {
            Self::DependencyChain => "dependency chain",
            Self::Capacity => "capacity",
            Self::UnsizedWork => "unsized work",
        }
    }
}

/// The open work a forecast is about.
#[derive(Debug, Clone, PartialEq)]
pub struct Workload {
    /// Estimated points not yet done.
    pub sized_points: u32,
    /// Open tickets without an estimate.
    pub unsized_tickets: u32,
    /// Longest chain of blocked-by tickets, counting each ticket in it.
    pub chain_len: u32,
}

/// Everything [`forecast`] needs.
#[derive(Debug, Clone)]
pub struct ForecastInput<'a> {
    /// The open work.
    pub work: Workload,
    /// Every ticket fact; finished ones inside the window are the samples.
    pub facts: &'a [TicketFact],
    /// Now, unix seconds.
    pub now: i64,
    /// `[pm] min_history`.
    pub min_history: u32,
    /// RNG seed; the same seed and history give the same answer.
    pub seed: u64,
    /// Trials to run.
    pub trials: u32,
}

/// A calendar date for each percentile.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Dates {
    /// Median finish, `YYYY-MM-DD`.
    pub p50: String,
    /// 85th percentile finish.
    pub p85: String,
    /// 95th percentile finish.
    pub p95: String,
}

/// The forecast outcome.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct Forecast {
    /// Trials run.
    pub trials: u32,
    /// Days from now to finish at each percentile.
    pub days: Percentiles,
    /// The same as calendar dates.
    pub dates: Dates,
    /// What most delays the finish.
    pub risk: Risk,
}

/// `SplitMix64`: a tiny seeded generator, so fixtures are stable without a dependency.
struct Rng(u64);

impl Rng {
    /// The next 64 random bits.
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// A uniformly chosen element of the non-empty `xs`.
    fn pick(&mut self, xs: &[f64]) -> f64 {
        // Truncation intended: the remainder is below `len`.
        #[allow(clippy::cast_possible_truncation)]
        let i = (self.next() % xs.len() as u64) as usize;
        xs[i]
    }
}

/// The finished, sized tickets inside the trailing history window as `(points, done_at)`.
fn window_finished(facts: &[TicketFact], now: i64) -> Vec<(f64, i64)> {
    let since = now - i64::try_from(HISTORY_WEEKS).unwrap_or(8) * 7 * DAY_SECS;
    facts
        .iter()
        .filter(|f| f.state == TicketState::Finished)
        .filter_map(|f| Some((f64::from(f.points?), f.done_at?)))
        .filter(|(_, d)| *d > since && *d <= now)
        .collect()
}

/// Points finished in each of the last [`HISTORY_WEEKS`] weeks, oldest first.
fn weekly_points(finished: &[(f64, i64)], now: i64) -> Vec<f64> {
    let mut weeks = vec![0.0; HISTORY_WEEKS];
    for (pts, done) in finished {
        let ago = usize::try_from((now - done) / (7 * DAY_SECS)).unwrap_or(0);
        if let Some(slot) = weeks.get_mut(HISTORY_WEEKS - 1 - ago.min(HISTORY_WEEKS - 1)) {
            *slot += pts;
        }
    }
    weeks
}

/// Cycle times, in days, of the finished tickets that have a start.
#[allow(clippy::cast_precision_loss)]
fn cycle_samples(facts: &[TicketFact]) -> Vec<f64> {
    facts
        .iter()
        .filter(|f| f.state == TicketState::Finished)
        .filter_map(|f| Some((f.started?, f.done_at?)))
        .map(|(s, d)| (d - s).max(0) as f64 / DAY_SECS as f64)
        .collect()
}

/// The length of the longest path through `blocked_by` edges `(ticket, blocker)`, counting tickets; cycles are cut.
pub fn longest_chain(blocked_by: &[(String, String)]) -> u32 {
    fn depth<'a>(
        t: &'a str,
        edges: &'a [(String, String)],
        stack: &mut Vec<&'a str>,
        memo: &mut std::collections::BTreeMap<&'a str, u32>,
    ) -> u32 {
        if let Some(d) = memo.get(t) {
            return *d;
        }
        if stack.contains(&t) {
            tracing::warn!(ticket = t, "blocked-by cycle ignored in chain length");
            return 0;
        }
        stack.push(t);
        let below = edges
            .iter()
            .filter(|(a, _)| a == t)
            .map(|(_, b)| depth(b, edges, stack, memo))
            .max()
            .unwrap_or(0);
        stack.pop();
        memo.insert(t, below + 1);
        below + 1
    }
    let mut memo = std::collections::BTreeMap::new();
    blocked_by
        .iter()
        .map(|(a, _)| depth(a, blocked_by, &mut Vec::new(), &mut memo))
        .max()
        .unwrap_or(0)
}

/// The open work among `facts` whose handle is in `open`, with the dependency chain length given.
pub fn workload(facts: &[TicketFact], open: &[String], chain_len: u32) -> Workload {
    let mine = facts
        .iter()
        .filter(|f| f.state == TicketState::Open && open.contains(&f.handle));
    let (mut sized, mut unsized_n) = (0, 0);
    for f in mine {
        match f.points {
            Some(p) => sized += p,
            None => unsized_n += 1,
        }
    }
    Workload {
        sized_points: sized,
        unsized_tickets: unsized_n,
        chain_len,
    }
}

/// One simulated finish: `(days, chain_bound, unsized_share)`.
fn trial(
    rng: &mut Rng,
    work: &Workload,
    sizes: &[f64],
    weekly: &[f64],
    cycles: &[f64],
) -> (f64, bool, f64) {
    let unsized_pts: f64 = (0..work.unsized_tickets).map(|_| rng.pick(sizes)).sum();
    let total = f64::from(work.sized_points) + unsized_pts;
    let mut left = total;
    let mut weeks = 0.0;
    while left > 0.0 && weeks < MAX_WEEKS {
        let done = rng.pick(weekly);
        if done >= left {
            weeks += if done > 0.0 { left / done } else { 0.0 };
            left = 0.0;
        } else {
            left -= done;
            weeks += 1.0;
        }
    }
    let capacity_days = weeks * 7.0;
    let chain_days: f64 = if cycles.is_empty() {
        0.0
    } else {
        (0..work.chain_len).map(|_| rng.pick(cycles)).sum()
    };
    let share = if total > 0.0 {
        unsized_pts / total
    } else {
        0.0
    };
    (
        capacity_days.max(chain_days),
        chain_days > capacity_days,
        share,
    )
}

/// Run the Monte Carlo; Unresolved below `min_history` finished sized tickets in the window.
pub fn forecast(input: &ForecastInput<'_>) -> Figure<Forecast> {
    let finished = window_finished(input.facts, input.now);
    Figure::gate(finished.len(), input.min_history.max(1), || {
        let sizes: Vec<f64> = finished.iter().map(|(p, _)| *p).collect();
        let weekly = weekly_points(&finished, input.now);
        let cycles = cycle_samples(input.facts);
        let mut rng = Rng(input.seed);
        let (mut days, mut chain_bound, mut share_sum) = (Vec::new(), 0_u32, 0.0);
        for _ in 0..input.trials {
            let (d, chain, share) = trial(&mut rng, &input.work, &sizes, &weekly, &cycles);
            days.push(d);
            chain_bound += u32::from(chain);
            share_sum += share;
        }
        let trials = f64::from(input.trials.max(1));
        let risk = if f64::from(chain_bound) / trials > 0.5 {
            Risk::DependencyChain
        } else if share_sum / trials >= 0.34 {
            Risk::UnsizedWork
        } else {
            Risk::Capacity
        };
        let p = percentiles(&days).unwrap_or(Percentiles {
            p50: 0.0,
            p85: 0.0,
            p95: 0.0,
        });
        #[allow(clippy::cast_possible_truncation)]
        let date = |d: f64| ymd(input.now + (d.ceil() as i64) * DAY_SECS);
        tracing::info!(trials = input.trials, p50 = p.p50, p85 = p.p85, p95 = p.p95, risk = ?risk, "forecast computed");
        Forecast {
            trials: input.trials,
            days: p,
            dates: Dates {
                p50: date(p.p50),
                p85: date(p.p85),
                p95: date(p.p95),
            },
            risk,
        }
    })
}

/// `YYYY-MM-DD` of a unix time (proleptic Gregorian, UTC).
fn ymd(unix: i64) -> String {
    let z = unix.div_euclid(DAY_SECS) + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + i64::from(m <= 2);
    format!("{y:04}-{m:02}-{d:02}")
}

/// The one printed line for a forecast; `release status` and `ticket show` both call this.
pub fn forecast_line(f: &Figure<Forecast>) -> String {
    match f {
        Figure::Value { value } => format!(
            "forecast: P50 {}, P85 {}, P95 {} ({} trials; main risk: {})",
            value.dates.p50,
            value.dates.p85,
            value.dates.p95,
            value.trials,
            value.risk.describe()
        ),
        Figure::Unresolved { samples, need } => {
            format!("forecast: unresolved ({samples} of {need} samples)")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: i64 = 1_800_000_000;

    /// A finished 2-point ticket done `ago` days before NOW after a 3-day cycle.
    fn done(ago: i64) -> TicketFact {
        TicketFact {
            handle: format!("~D{ago}"),
            points: Some(2),
            state: TicketState::Finished,
            parent: None,
            created: 0,
            started: Some(NOW - (ago + 3) * DAY_SECS),
            done_at: Some(NOW - ago * DAY_SECS),
            tokens: None,
        }
    }

    fn open(handle: &str, points: Option<u32>) -> TicketFact {
        TicketFact {
            handle: handle.to_owned(),
            points,
            state: TicketState::Open,
            parent: None,
            created: 0,
            started: None,
            done_at: None,
            tokens: None,
        }
    }

    fn history() -> Vec<TicketFact> {
        (1..=20).map(|i| done(i * 2)).collect()
    }

    fn run(facts: &[TicketFact], work: Workload, min_history: u32) -> Figure<Forecast> {
        forecast(&ForecastInput {
            work,
            facts,
            now: NOW,
            min_history,
            seed: 42,
            trials: 2_000,
        })
    }

    #[test]
    fn seeded_fixture_gives_stable_percentiles() {
        // frob:tests crates/frob-metrics/src/forecast.rs::forecast
        let facts = history();
        let work = Workload {
            sized_points: 30,
            unsized_tickets: 0,
            chain_len: 1,
        };
        let a = run(&facts, work.clone(), 3);
        let b = run(&facts, work, 3);
        assert_eq!(a, b);
        let f = a.value().expect("resolved");
        assert!(f.days.p50 <= f.days.p85 && f.days.p85 <= f.days.p95);
        assert!(f.days.p50 > 0.0);
        assert_eq!(f.risk, Risk::Capacity);
        // Pinned so an accidental change to the model or the RNG is noticed.
        assert_eq!(
            (
                f.dates.p50.as_str(),
                f.dates.p85.as_str(),
                f.dates.p95.as_str()
            ),
            ("2027-02-25", "2027-03-10", "2027-03-19")
        );
    }

    #[test]
    fn below_min_history_is_unresolved_with_the_count() {
        // frob:tests crates/frob-metrics/src/forecast.rs::forecast
        // frob:tests crates/frob-metrics/src/forecast.rs::forecast_line
        let facts: Vec<TicketFact> = (1..=2).map(done).collect();
        let work = Workload {
            sized_points: 5,
            unsized_tickets: 0,
            chain_len: 1,
        };
        let fig = run(&facts, work, 3);
        assert_eq!(
            fig,
            Figure::Unresolved {
                samples: 2,
                need: 3
            }
        );
        assert_eq!(forecast_line(&fig), "forecast: unresolved (2 of 3 samples)");
    }

    #[test]
    fn a_long_chain_or_unsized_work_names_the_risk() {
        // frob:tests crates/frob-metrics/src/forecast.rs::forecast
        let facts = history();
        let chain = Workload {
            sized_points: 2,
            unsized_tickets: 0,
            chain_len: 30,
        };
        assert_eq!(
            run(&facts, chain, 3).value().expect("resolved").risk,
            Risk::DependencyChain
        );
        let unsized_work = Workload {
            sized_points: 2,
            unsized_tickets: 20,
            chain_len: 1,
        };
        assert_eq!(
            run(&facts, unsized_work, 3).value().expect("resolved").risk,
            Risk::UnsizedWork
        );
    }

    #[test]
    fn chain_length_counts_the_longest_blocked_by_path() {
        // frob:tests crates/frob-metrics/src/forecast.rs::longest_chain
        let e = |a: &str, b: &str| (a.to_owned(), b.to_owned());
        assert_eq!(longest_chain(&[]), 0);
        assert_eq!(
            longest_chain(&[e("~A", "~B"), e("~B", "~C"), e("~A", "~D")]),
            3
        );
        assert_eq!(longest_chain(&[e("~A", "~B"), e("~B", "~A")]), 2);
    }

    #[test]
    fn workload_sums_the_listed_open_tickets() {
        // frob:tests crates/frob-metrics/src/forecast.rs::workload
        let facts = [open("~A", Some(3)), open("~B", None), open("~C", Some(8))];
        let w = workload(&facts, &["~A".to_owned(), "~B".to_owned()], 2);
        assert_eq!((w.sized_points, w.unsized_tickets, w.chain_len), (3, 1, 2));
    }

    #[test]
    fn dates_render_as_iso_days() {
        // frob:tests crates/frob-metrics/src/forecast.rs::forecast_line
        assert_eq!(ymd(0), "1970-01-01");
        assert_eq!(ymd(951_782_400), "2000-02-29");
    }

    #[test]
    fn risk_words_are_stable() {
        // frob:tests crates/frob-metrics/src/forecast.rs::Risk.describe
        assert_eq!(Risk::DependencyChain.describe(), "dependency chain");
        assert_eq!(Risk::Capacity.describe(), "capacity");
        assert_eq!(Risk::UnsizedWork.describe(), "unsized work");
    }
}
