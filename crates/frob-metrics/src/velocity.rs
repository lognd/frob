//! Velocity and capacity as a [`Figure`], over the same `frob-pm` functions `cycle assign` and `cycle velocity` use.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use std::collections::BTreeMap;

use frob_pm::cycle::velocity::{history_capacity, velocity};
use frob_pm::model::{Cycle, ObjectId, State};
use schemars::JsonSchema;
use serde::Serialize;

use crate::figure::Figure;

/// Points one closed cycle delivered.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct CycleDone {
    /// The `START..END` alias.
    pub alias: String,
    /// Points done among the tickets committed to the cycle.
    pub done: u32,
}

/// Velocity over the recent closed cycles and the capacity derived from it.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct VelocityStats {
    /// Closed cycles used, oldest first.
    pub cycles: Vec<CycleDone>,
    /// Mean points per cycle.
    pub mean: f64,
    /// Population standard deviation.
    pub stddev: f64,
    /// Enforced commitment limit in points (`mean - k * stddev`, floored).
    pub capacity: Option<u32>,
    /// One-line statement of the capacity.
    pub capacity_note: String,
}

/// Velocity and capacity over the last `last` closed cycles; Unresolved below `min_history` closed cycles.
pub fn velocity_stats(
    cycles: &[Cycle],
    done: &BTreeMap<ObjectId, u32>,
    last: usize,
    min_history: u32,
    k: f64,
) -> Figure<VelocityStats> {
    let closed = cycles.iter().filter(|c| c.state == State::Closed).count();
    Figure::gate(closed, min_history, || {
        let v = velocity(cycles, done, last);
        let cap = history_capacity(cycles, done, min_history, k);
        VelocityStats {
            cycles: v
                .per_cycle
                .iter()
                .map(|(alias, done)| CycleDone {
                    alias: alias.clone(),
                    done: *done,
                })
                .collect(),
            mean: v.mean,
            stddev: v.stddev,
            capacity: cap.limit(),
            capacity_note: cap.describe(),
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_ledger::model::Stamp;

    /// A closed cycle on the given days.
    fn cycle(start: &str, end: &str, state: State) -> Cycle {
        Cycle {
            id: ObjectId::mint(),
            start: start.parse().expect("day"),
            end: end.parse().expect("day"),
            ended: None,
            goal: "g".to_owned(),
            capacity_points: None,
            state,
            tickets: Vec::new(),
            created: Stamp::from_unix(1_800_000_000),
            updated: Stamp::from_unix(1_800_000_000),
            ordinal: 1,
        }
    }

    #[test]
    fn fixture_history_reproduces_known_velocity_and_capacity() {
        // frob:tests crates/frob-metrics/src/velocity.rs::velocity_stats
        let cycles = [
            cycle("2026-10-05", "2026-10-11", State::Closed),
            cycle("2026-10-12", "2026-10-18", State::Closed),
            cycle("2026-10-19", "2026-10-25", State::Closed),
            cycle("2026-10-26", "2026-11-01", State::Planned),
        ];
        let done: BTreeMap<ObjectId, u32> =
            cycles.iter().map(|c| c.id).zip([8, 12, 10, 0]).collect();
        let fig = velocity_stats(&cycles, &done, 6, 3, 0.5);
        let v = fig.value().expect("three cycles resolve");
        assert!((v.mean - 10.0).abs() < 1e-9);
        assert!((v.stddev - (8.0_f64 / 3.0).sqrt()).abs() < 1e-9);
        // 10 - 0.5 * 1.633 = 9.18 -> 9.
        assert_eq!(v.capacity, Some(9));
        assert_eq!(
            v.cycles.iter().map(|c| c.done).collect::<Vec<_>>(),
            [8, 12, 10]
        );
    }

    #[test]
    fn velocity_below_min_history_is_unresolved_with_the_count() {
        // frob:tests crates/frob-metrics/src/velocity.rs::velocity_stats
        let cycles = [
            cycle("2026-10-05", "2026-10-11", State::Closed),
            cycle("2026-10-12", "2026-10-18", State::Closed),
        ];
        let done = BTreeMap::new();
        assert_eq!(
            velocity_stats(&cycles, &done, 6, 3, 0.5),
            Figure::Unresolved {
                samples: 2,
                need: 3
            }
        );
    }
}
