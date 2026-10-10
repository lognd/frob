//! One JSON line per run in `<telemetry dir>/telemetry.jsonl` (no arguments, no paths).

use std::io::Write;
use std::path::Path;

use serde::Serialize;

use crate::report::{Counts, StageTime, Stats, Timing};

/// The line appended after a run.
#[derive(Serialize)]
struct Line<'a> {
    at: String,
    duration_ms: &'a [StageTime],
    budget_ms: u64,
    tools_ms: u64,
    files: usize,
    cached_hits: usize,
    findings: Counts,
}

/// Append the telemetry line; failures are logged, never raised.
pub(crate) fn append(
    at: gob_time::Stamp,
    dir: &Path,
    timing: &Timing,
    stats: &Stats,
    counts: Counts,
) {
    let line = Line {
        at: at.precise(),
        duration_ms: &timing.stages,
        budget_ms: timing.budget_ms(),
        tools_ms: timing.tools_ms(),
        files: stats.files,
        cached_hits: stats.cached_hits(),
        findings: counts,
    };
    let Ok(mut text) = serde_json::to_string(&line) else {
        return;
    };
    text.push('\n');
    let result = std::fs::create_dir_all(dir).and_then(|()| {
        std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(dir.join("telemetry.jsonl"))
            .and_then(|mut f| f.write_all(text.as_bytes()))
    });
    match result {
        Ok(()) => tracing::debug!("telemetry line appended"),
        Err(err) => tracing::warn!(%err, "telemetry not written"),
    }
}
