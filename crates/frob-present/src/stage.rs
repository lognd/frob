//! Stage identity, outcome and the end-of-run profile report.

use std::fmt;
use std::time::Duration;

/// Stable dotted stage name such as `land.merge`; unknown names display verbatim.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct StageId(String);

impl StageId {
    /// Wrap a dotted stage name.
    pub fn new(name: impl Into<String>) -> Self {
        Self(name.into())
    }

    /// The name as text.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for StageId {
    /// The dotted name, verbatim.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// How a stage finished.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    /// The stage passed.
    Ok,
    /// The stage passed with warnings.
    Warn,
    /// The stage failed.
    Failed,
    /// The stage was skipped.
    Skipped,
}

impl Outcome {
    /// Lowercase label used in plain lines.
    pub fn label(self) -> &'static str {
        match self {
            Self::Ok => "ok",
            Self::Warn => "warn",
            Self::Failed => "failed",
            Self::Skipped => "skipped",
        }
    }
}

/// One finished stage in a [`ProfileReport`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StageTiming {
    /// The stage.
    pub stage: StageId,
    /// Measured duration (from the injected clock, never read here).
    pub elapsed: Duration,
    /// How it ended.
    pub outcome: Outcome,
}

/// Per-stage elapsed time, built from the stage end events.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ProfileReport {
    /// Finished stages in completion order.
    pub stages: Vec<StageTiming>,
}

impl ProfileReport {
    /// Append a finished stage.
    pub fn push(&mut self, stage: StageId, elapsed: Duration, outcome: Outcome) {
        self.stages.push(StageTiming {
            stage,
            elapsed,
            outcome,
        });
    }

    /// Sum of all stage durations.
    pub fn total(&self) -> Duration {
        self.stages.iter().map(|s| s.elapsed).sum()
    }

    /// The slowest stage whose share of the total exceeds `threshold` (0.0 to 1.0).
    pub fn slowest_above(&self, threshold: f64) -> Option<&StageTiming> {
        let total = self.total().as_secs_f64();
        if total <= 0.0 {
            return None;
        }
        self.stages
            .iter()
            .max_by_key(|s| s.elapsed)
            .filter(|s| s.elapsed.as_secs_f64() / total > threshold)
    }
}

/// One row of a [`ProfileView`].
#[derive(Debug, Clone, PartialEq, serde::Serialize, schemars::JsonSchema)]
pub struct ProfileRow {
    /// Dotted stage name.
    pub stage: String,
    /// Elapsed milliseconds.
    pub ms: u64,
    /// Share of the total, 0.0 to 1.0.
    pub share: f64,
    /// Outcome label.
    pub outcome: String,
    /// True for the slowest stage when it exceeds the warn share.
    pub slow: bool,
}

/// Serializable [`ProfileReport`] for the envelope's `profile` field (only with `--profile`).
#[derive(Debug, Clone, PartialEq, serde::Serialize, schemars::JsonSchema)]
pub struct ProfileView {
    /// Sum of the stage durations in milliseconds.
    pub total_ms: u64,
    /// Stages in completion order.
    pub stages: Vec<ProfileRow>,
}

/// Share of the total above which the slowest stage is flagged `slow`.
pub const SLOW_SHARE: f64 = 0.5;

impl ProfileReport {
    /// The serializable view, flagging the slowest stage above `slow_share`.
    pub fn view(&self, slow_share: f64) -> ProfileView {
        let total = self.total();
        let denom = total.as_secs_f64();
        let slow = self.slowest_above(slow_share).map(|s| s.stage.clone());
        let stages = self
            .stages
            .iter()
            .map(|s| ProfileRow {
                stage: s.stage.as_str().to_owned(),
                ms: u64::try_from(s.elapsed.as_millis()).unwrap_or(u64::MAX),
                share: if denom > 0.0 {
                    s.elapsed.as_secs_f64() / denom
                } else {
                    0.0
                },
                outcome: s.outcome.label().to_owned(),
                slow: slow.as_ref() == Some(&s.stage),
            })
            .collect();
        ProfileView {
            total_ms: u64::try_from(total.as_millis()).unwrap_or(u64::MAX),
            stages,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-present/src/stage.rs::view
    #[test]
    fn profile_view_flags_the_slowest_stage_and_sums_shares() {
        let mut r = ProfileReport::default();
        r.push(
            StageId::new("land.merge"),
            Duration::from_millis(100),
            Outcome::Ok,
        );
        r.push(
            StageId::new("land.check"),
            Duration::from_millis(900),
            Outcome::Ok,
        );
        let v = r.view(SLOW_SHARE);
        assert_eq!(v.total_ms, 1000);
        assert!(!v.stages[0].slow);
        assert!(v.stages[1].slow);
        assert!((v.stages[1].share - 0.9).abs() < 1e-9);
    }
}
