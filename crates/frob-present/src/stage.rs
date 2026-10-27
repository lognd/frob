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
