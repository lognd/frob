//! Throughput and the cycle and lead time percentiles of finished tickets.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use schemars::JsonSchema;
use serde::Serialize;

use crate::figure::Figure;
use crate::percentile::{Percentiles, percentiles};
use crate::report::{TicketFact, TicketState};

/// Seconds in a day, for converting stamps to days.
const DAY: f64 = 86_400.0;

/// Tickets finished per week over a trailing window.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, JsonSchema)]
pub struct Throughput {
    /// Window length in days.
    pub window_days: u32,
    /// Tickets finished inside the window.
    pub finished: u32,
    /// `finished` scaled to a week.
    pub per_week: f64,
}

/// Cycle time (started to done) and lead time (created to done) in days.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct TimeStats {
    /// Days from the first move to in-progress to done.
    pub cycle_days: Figure<Percentiles>,
    /// Days from creation to done.
    pub lead_days: Figure<Percentiles>,
}

/// The finished tickets among `facts` that have a done time.
fn finished(facts: &[TicketFact]) -> impl Iterator<Item = (&TicketFact, i64)> {
    facts
        .iter()
        .filter(|f| f.state == TicketState::Finished)
        .filter_map(|f| f.done_at.map(|d| (f, d)))
}

/// Days between two unix seconds, never negative.
#[allow(clippy::cast_precision_loss)]
fn days(from: i64, to: i64) -> f64 {
    (to - from).max(0) as f64 / DAY
}

/// Finished tickets per week over the `window_days` ending at `now`; Unresolved below `min_history` finished tickets in the window.
pub fn throughput(
    facts: &[TicketFact],
    now: i64,
    window_days: u32,
    min_history: u32,
) -> Figure<Throughput> {
    let since = now - i64::from(window_days) * 86_400;
    let n = finished(facts)
        .filter(|(_, d)| *d > since && *d <= now)
        .count();
    Figure::gate(n, min_history, || Throughput {
        window_days,
        finished: u32::try_from(n).unwrap_or(u32::MAX),
        per_week: f64::from(u32::try_from(n).unwrap_or(u32::MAX)) * 7.0
            / f64::from(window_days.max(1)),
    })
}

/// Percentiles of one duration sample, Unresolved below `min_history` samples.
fn gated(samples: &[f64], min_history: u32) -> Figure<Percentiles> {
    match percentiles(samples) {
        Some(p) if samples.len() >= min_history as usize => Figure::Value { value: p },
        _ => Figure::Unresolved {
            samples: u32::try_from(samples.len()).unwrap_or(u32::MAX),
            need: min_history,
        },
    }
}

/// Cycle and lead time percentiles over every finished ticket.
pub fn time_stats(facts: &[TicketFact], min_history: u32) -> TimeStats {
    let cycle: Vec<f64> = finished(facts)
        .filter_map(|(f, d)| f.started.map(|s| days(s, d)))
        .collect();
    let lead: Vec<f64> = finished(facts).map(|(f, d)| days(f.created, d)).collect();
    TimeStats {
        cycle_days: gated(&cycle, min_history),
        lead_days: gated(&lead, min_history),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A finished ticket created at day 0, started at day 1, done after `d` days.
    fn done(d: i64) -> TicketFact {
        TicketFact {
            handle: format!("~{d}"),
            points: Some(1),
            state: TicketState::Finished,
            parent: None,
            created: 0,
            started: Some(86_400),
            done_at: Some(d * 86_400),
            tokens: None,
        }
    }

    #[test]
    fn times_and_throughput_of_a_fixture_history() {
        // frob:tests crates/frob-metrics/src/times.rs::time_stats
        // Lead times 2..=11 days; cycle times 1..=10 days.
        let facts: Vec<TicketFact> = (2..=11).map(done).collect();
        let t = time_stats(&facts, 3);
        let cycle = t.cycle_days.value().expect("ten samples");
        assert!((cycle.p50 - 5.5).abs() < 1e-9);
        assert!((cycle.p85 - 8.65).abs() < 1e-9);
        let lead = t.lead_days.value().expect("ten samples");
        assert!((lead.p50 - 6.5).abs() < 1e-9);
        // Ten tickets finished within a 14-day window ending day 11: 5 per week.
        let tp = throughput(&facts, 11 * 86_400, 14, 3);
        assert!((tp.value().expect("resolved").per_week - 5.0).abs() < 1e-9);
    }

    #[test]
    fn too_few_finished_tickets_are_unresolved() {
        // frob:tests crates/frob-metrics/src/times.rs::time_stats
        let facts = [done(3), done(4)];
        assert_eq!(
            time_stats(&facts, 3).cycle_days,
            Figure::Unresolved {
                samples: 2,
                need: 3
            }
        );
        assert_eq!(
            throughput(&facts, 5 * 86_400, 14, 3),
            Figure::Unresolved {
                samples: 2,
                need: 3
            }
        );
    }
}
