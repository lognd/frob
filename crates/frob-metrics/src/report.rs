//! The stats report: one value computed from the fold and git, rendered as text and JSON alike.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::str::FromStr;

use frob_pm::model::{Cycle, ObjectId};
use schemars::JsonSchema;
use serde::Serialize;

use crate::cost::{CostReport, CostUnit, cost_reports};
use crate::figure::Figure;
use crate::remaining::{Remaining, RemainingRow, remaining};
use crate::times::{Throughput, TimeStats, throughput, time_stats};
use crate::velocity::{VelocityStats, velocity_stats};

/// Lifecycle state of a ticket as the metrics see it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum TicketState {
    /// Not finished and not dropped.
    Open,
    /// Done.
    Finished,
    /// Cut; excluded from every figure.
    Dropped,
}

/// The per-ticket facts the metrics need, gathered by the caller from the fold.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TicketFact {
    /// Ticket handle.
    pub handle: String,
    /// Story points, when estimated.
    pub points: Option<u32>,
    /// Lifecycle state.
    pub state: TicketState,
    /// Parent epic handle, if any.
    pub parent: Option<String>,
    /// Creation time, unix seconds.
    pub created: i64,
    /// First move to in-progress, unix seconds.
    pub started: Option<i64>,
    /// Time it finished, unix seconds.
    pub done_at: Option<i64>,
    /// Model tokens spent, when recorded.
    pub tokens: Option<u64>,
}

/// A section of the report, selectable with `--section`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Section {
    /// Velocity and capacity.
    Velocity,
    /// Points remaining.
    Remaining,
    /// Throughput.
    Throughput,
    /// Cycle and lead time percentiles.
    Times,
    /// Cost per point.
    Cost,
}

impl Section {
    /// Every section, in report order.
    pub const ALL: [Self; 5] = [
        Self::Velocity,
        Self::Remaining,
        Self::Throughput,
        Self::Times,
        Self::Cost,
    ];

    /// The name accepted by `--section`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Velocity => "velocity",
            Self::Remaining => "remaining",
            Self::Throughput => "throughput",
            Self::Times => "times",
            Self::Cost => "cost",
        }
    }
}

impl FromStr for Section {
    type Err = String;

    /// Parse a `--section` name.
    fn from_str(s: &str) -> Result<Self, String> {
        Self::ALL
            .into_iter()
            .find(|x| x.as_str() == s)
            .ok_or_else(|| {
                let names: Vec<&str> = Self::ALL.iter().map(|x| x.as_str()).collect();
                format!(
                    "unknown section `{s}`; expected one of {}",
                    names.join(", ")
                )
            })
    }
}

/// Everything [`compute`] needs.
#[derive(Debug, Clone)]
pub struct StatsInput<'a> {
    /// Sections to compute; empty means all.
    pub sections: Vec<Section>,
    /// Every cycle.
    pub cycles: &'a [Cycle],
    /// Points done per cycle commitment, from the delivery ledger.
    pub done: &'a BTreeMap<ObjectId, u32>,
    /// Per-ticket facts.
    pub tickets: &'a [TicketFact],
    /// Each milestone version with its epic handles.
    pub milestones: &'a [(String, Vec<String>)],
    /// Velocity window in cycles.
    pub last: usize,
    /// `[pm] min_history`.
    pub min_history: u32,
    /// Capacity safety factor `k`.
    pub k: f64,
    /// Now, unix seconds.
    pub now: i64,
    /// Throughput window in days.
    pub window_days: u32,
}

/// The stats report; sections not requested are omitted.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct StatsReport {
    /// Velocity and capacity.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub velocity: Option<Figure<VelocityStats>>,
    /// Points remaining.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub remaining: Option<Remaining>,
    /// Throughput.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub throughput: Option<Figure<Throughput>>,
    /// Cycle and lead times.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub times: Option<TimeStats>,
    /// Cost per point, per unit.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cost: Option<Vec<CostReport>>,
}

/// Compute the requested sections from `input`.
pub fn compute(input: &StatsInput<'_>) -> StatsReport {
    let want = |s: Section| input.sections.is_empty() || input.sections.contains(&s);
    tracing::info!(sections = ?input.sections, tickets = input.tickets.len(), "computing stats");
    StatsReport {
        velocity: want(Section::Velocity).then(|| {
            velocity_stats(
                input.cycles,
                input.done,
                input.last,
                input.min_history,
                input.k,
            )
        }),
        remaining: want(Section::Remaining).then(|| remaining(input.tickets, input.milestones)),
        throughput: want(Section::Throughput).then(|| {
            throughput(
                input.tickets,
                input.now,
                input.window_days,
                input.min_history,
            )
        }),
        times: want(Section::Times).then(|| time_stats(input.tickets, input.min_history)),
        cost: want(Section::Cost).then(|| cost_reports(input.tickets, input.min_history)),
    }
}

/// One line for an Unresolved figure.
fn unresolved(label: &str, samples: u32, need: u32) -> String {
    format!("{label}: unresolved ({samples} of {need} samples)")
}

/// Text lines for one remaining row.
fn row_line(r: &RemainingRow) -> String {
    format!(
        "  {}: {} points, {} tickets ({} unestimated)",
        r.name, r.points, r.tickets, r.unestimated
    )
}

/// Render the report as text lines; the JSON form is the report itself.
pub fn render_text(r: &StatsReport) -> Vec<String> {
    let mut out = Vec::new();
    if let Some(v) = &r.velocity {
        match v {
            Figure::Value { value } => {
                out.push("velocity (points per closed cycle):".to_owned());
                for c in &value.cycles {
                    out.push(format!("  {}: {}", c.alias, c.done));
                }
                out.push(format!(
                    "  mean {:.2}, stddev {:.2}",
                    value.mean, value.stddev
                ));
                out.push(format!("  {}", value.capacity_note));
            }
            Figure::Unresolved { samples, need } => {
                out.push(unresolved("velocity", *samples, *need));
            }
        }
    }
    if let Some(rem) = &r.remaining {
        out.push("remaining:".to_owned());
        out.push(row_line(&rem.total));
        out.push(" by milestone:".to_owned());
        out.extend(rem.by_milestone.iter().map(row_line));
        out.push(" by epic:".to_owned());
        out.extend(rem.by_epic.iter().map(row_line));
    }
    if let Some(t) = &r.throughput {
        match t {
            Figure::Value { value } => out.push(format!(
                "throughput: {} finished in {} days ({:.2} per week)",
                value.finished, value.window_days, value.per_week
            )),
            Figure::Unresolved { samples, need } => {
                out.push(unresolved("throughput", *samples, *need));
            }
        }
    }
    if let Some(t) = &r.times {
        for (label, f) in [("cycle time", &t.cycle_days), ("lead time", &t.lead_days)] {
            match f {
                Figure::Value { value } => out.push(format!(
                    "{label} (days): p50 {:.1}, p85 {:.1}, p95 {:.1}",
                    value.p50, value.p85, value.p95
                )),
                Figure::Unresolved { samples, need } => {
                    out.push(unresolved(label, *samples, *need));
                }
            }
        }
    }
    for c in r.cost.iter().flatten() {
        let unit = match c.unit {
            CostUnit::WallClockHours => "hours",
            CostUnit::Tokens => "tokens",
        };
        match &c.fit {
            Figure::Value { value } => {
                let f = &value.fit;
                let mut line = format!(
                    "cost per point ({unit}): b {:.2}, spread x{:.2}, {} samples",
                    f.b, f.spread, f.samples
                );
                if let Some((lo, hi)) = f.b_interval {
                    let _ = write!(line, ", b 95% [{lo:.2}, {hi:.2}]");
                }
                out.push(line);
                for s in &value.sizes {
                    out.push(format!(
                        "  {} points: median {:.2}, p85 {:.2}",
                        s.points, s.median, s.p85
                    ));
                }
            }
            Figure::Unresolved { samples, need } => {
                out.push(unresolved(
                    &format!("cost per point ({unit})"),
                    *samples,
                    *need,
                ));
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sections_parse_and_unknown_is_an_error() {
        // frob:tests crates/frob-metrics/src/report.rs::Section
        assert_eq!("cost".parse::<Section>(), Ok(Section::Cost));
        assert!("nope".parse::<Section>().is_err());
        // frob:tests crates/frob-metrics/src/report.rs::Section.as_str
        assert!(
            Section::ALL
                .iter()
                .all(|s| s.as_str().parse::<Section>() == Ok(*s))
        );
    }

    #[test]
    fn empty_history_renders_every_figure_unresolved() {
        // frob:tests crates/frob-metrics/src/report.rs::compute
        let done = BTreeMap::new();
        let input = StatsInput {
            sections: Vec::new(),
            cycles: &[],
            done: &done,
            tickets: &[],
            milestones: &[],
            last: 3,
            min_history: 3,
            k: 1.0,
            now: 0,
            window_days: 28,
        };
        let r = compute(&input);
        assert_eq!(
            r.velocity,
            Some(Figure::Unresolved {
                samples: 0,
                need: 3
            })
        );
        let text = render_text(&r).join("\n");
        assert!(
            text.contains("velocity: unresolved (0 of 3 samples)"),
            "{text}"
        );
        assert!(text.contains("throughput: unresolved"), "{text}");
    }
}
