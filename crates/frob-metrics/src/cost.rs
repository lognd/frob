//! Cost per point: a log-normal fit of cost against points, per cost unit.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use schemars::JsonSchema;
use serde::Serialize;

use crate::figure::Figure;
use crate::fit::{LogNormalFit, MIN_SAMPLES, SizePrediction, fit};
use crate::report::{TicketFact, TicketState};

/// Story sizes the fit is reported at (the Fibonacci scale `[pm] max_story_points` is drawn from).
pub const SIZES: [u32; 5] = [1, 2, 3, 5, 8];

/// What cost is measured in.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum CostUnit {
    /// Hours from first in-progress to done.
    WallClockHours,
    /// Model tokens spent, when the ticket records them.
    Tokens,
}

/// The fitted model and its per-size predictions.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct CostFit {
    /// Parameters, spread and the exponent interval.
    pub fit: LogNormalFit,
    /// Median and P85 at each of [`SIZES`].
    pub sizes: Vec<SizePrediction>,
}

/// Cost per point in one unit.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct CostReport {
    /// The unit costs are in.
    pub unit: CostUnit,
    /// The fit, or Unresolved with the sample count.
    pub fit: Figure<CostFit>,
}

/// `(points, cost)` samples of the finished, estimated tickets for which `cost` yields a positive value.
fn samples(facts: &[TicketFact], cost: impl Fn(&TicketFact) -> Option<f64>) -> Vec<(f64, f64)> {
    facts
        .iter()
        .filter(|f| f.state == TicketState::Finished)
        .filter_map(|f| {
            let points = f.points.filter(|p| *p > 0)?;
            let c = cost(f).filter(|c| *c > 0.0)?;
            Some((f64::from(points), c))
        })
        .collect()
}

/// Fit one unit; Unresolved below `max(min_history, MIN_SAMPLES)` samples.
fn report(unit: CostUnit, samples: &[(f64, f64)], min_history: u32) -> CostReport {
    let need = min_history.max(u32::try_from(MIN_SAMPLES).unwrap_or(3));
    let have = u32::try_from(samples.len()).unwrap_or(u32::MAX);
    let unresolved = || Figure::Unresolved {
        samples: have,
        need,
    };
    let fit = if have < need {
        unresolved()
    } else {
        match fit(samples) {
            Ok(f) => Figure::Value {
                value: CostFit {
                    sizes: f.predict(&SIZES),
                    fit: f,
                },
            },
            Err(e) => {
                tracing::warn!(?unit, error = %e, "cost fit failed");
                unresolved()
            }
        }
    };
    CostReport { unit, fit }
}

/// Cost per point per unit: wall-clock always, tokens only when some finished ticket records them.
pub fn cost_reports(facts: &[TicketFact], min_history: u32) -> Vec<CostReport> {
    #[allow(clippy::cast_precision_loss)]
    let wall = samples(facts, |f| {
        let (s, d) = (f.started?, f.done_at?);
        (d > s).then(|| (d - s) as f64 / 3600.0)
    });
    let mut out = vec![report(CostUnit::WallClockHours, &wall, min_history)];
    #[allow(clippy::cast_precision_loss)]
    let tokens = samples(facts, |f| f.tokens.map(|t| t as f64));
    if facts.iter().any(|f| f.tokens.is_some()) {
        out.push(report(CostUnit::Tokens, &tokens, min_history));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A finished ticket of `points` that took `hours`.
    fn done(points: u32, hours: i64) -> TicketFact {
        TicketFact {
            handle: format!("~{points}-{hours}"),
            points: Some(points),
            state: TicketState::Finished,
            parent: None,
            created: 0,
            started: Some(0),
            done_at: Some(hours * 3600),
            tokens: None,
        }
    }

    #[test]
    fn below_min_history_every_cost_figure_is_unresolved_with_the_count() {
        // frob:tests crates/frob-metrics/src/cost.rs::cost_reports
        let facts = [done(1, 2), done(2, 4)];
        let r = cost_reports(&facts, 3);
        assert_eq!(r.len(), 1, "no token samples, no token report");
        assert_eq!(
            r[0].fit,
            Figure::Unresolved {
                samples: 2,
                need: 3
            }
        );
    }

    #[test]
    fn exact_power_law_history_fits_with_zero_spread() {
        // frob:tests crates/frob-metrics/src/cost.rs::cost_reports
        // cost = 2 * points hours exactly: b = 1, median(3) = 6, sigma = 0.
        let facts = [done(1, 2), done(2, 4), done(3, 6), done(5, 10), done(8, 16)];
        let r = cost_reports(&facts, 3);
        let f = r[0].fit.value().expect("resolved");
        assert!((f.fit.b - 1.0).abs() < 1e-9);
        assert!(f.fit.sigma < 1e-9);
        let three = f.sizes.iter().find(|s| s.points == 3).expect("size 3");
        assert!((three.median - 6.0).abs() < 1e-9);
        assert!((three.median_per_point - 2.0).abs() < 1e-9);
    }
}
