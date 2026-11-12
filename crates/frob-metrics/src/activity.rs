//! Activity inference: classify a ticket's in-progress time from observed signals, never from agent-set state.
// frob:ticket 01M48Q2BWRT117K8E163MWHDN2
//!
//! Frob already sees (or cheaply records) lease events, worktree commit times, file mtimes, test
//! and evidence runs, goway job reports, lease refusals and the land start and end. Each is a
//! [`Signal`]. [`classify`] turns a timeline of signals into ordered [`Segment`]s of
//! [`Activity`], sessionised by an idle gap threshold, and [`totals`] folds segments into
//! per-activity seconds. [`Journal`] is the local, uncommitted store (a JSON-lines file per
//! ticket under the git common dir), so nothing here is ever written to the code branch.

use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Default idle gap: a silence longer than this (15 minutes) ends a working session.
pub const DEFAULT_IDLE_GAP_SECS: i64 = 900;

/// What a ticket's time was spent on.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize, JsonSchema,
)]
#[serde(rename_all = "snake_case")]
pub enum Activity {
    /// Editing: commits, file changes and lease activity.
    Implementing,
    /// Running tests, evidence or a goway job.
    Testing,
    /// Blocked on someone else, such as a refused lease.
    Waiting,
    /// Between land start and land end.
    Landing,
    /// No signal inside the idle gap.
    Idle,
}

impl Activity {
    /// Every activity, in the order summaries list them.
    pub const ALL: [Activity; 5] = [
        Activity::Implementing,
        Activity::Testing,
        Activity::Waiting,
        Activity::Landing,
        Activity::Idle,
    ];

    /// The lowercase name used in summaries and JSON.
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Implementing => "implementing",
            Self::Testing => "testing",
            Self::Waiting => "waiting",
            Self::Landing => "landing",
            Self::Idle => "idle",
        }
    }
}

/// One observed fact about a ticket, at a unix-second instant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Signal {
    /// A lease was acquired or renewed.
    Lease {
        /// Unix seconds.
        at: i64,
    },
    /// A commit landed on the ticket's worktree branch.
    Commit {
        /// Unix seconds.
        at: i64,
    },
    /// A worktree file's mtime, seen when frob looked.
    FileEdit {
        /// Unix seconds.
        at: i64,
    },
    /// A test or evidence run (`from` to `to`).
    TestRun {
        /// Unix seconds the run began.
        from: i64,
        /// Unix seconds the run ended.
        to: i64,
    },
    /// A goway job report (`from` to `to`).
    GowayJob {
        /// Unix seconds the job began.
        from: i64,
        /// Unix seconds the job ended.
        to: i64,
    },
    /// A lease was refused (`E-LEASE-HELD`).
    LeaseRefused {
        /// Unix seconds.
        at: i64,
    },
    /// A land began and ended.
    Land {
        /// Unix seconds the land began.
        from: i64,
        /// Unix seconds the land ended.
        to: i64,
    },
}

/// How a signal contributes to the timeline.
enum Shape {
    /// An instant that opens a session of this activity.
    Point(i64, Activity),
    /// A measured interval of this activity.
    Span(i64, i64, Activity),
}

impl Signal {
    fn shape(self) -> Shape {
        match self {
            Self::Lease { at } | Self::Commit { at } | Self::FileEdit { at } => {
                Shape::Point(at, Activity::Implementing)
            }
            Self::LeaseRefused { at } => Shape::Point(at, Activity::Waiting),
            Self::TestRun { from, to } | Self::GowayJob { from, to } => {
                Shape::Span(from, to.max(from), Activity::Testing)
            }
            Self::Land { from, to } => Shape::Span(from, to.max(from), Activity::Landing),
        }
    }

    /// The instant the signal starts at, for ordering.
    #[must_use]
    pub fn start(self) -> i64 {
        match self.shape() {
            Shape::Point(at, _) | Shape::Span(at, _, _) => at,
        }
    }
}

/// A half-open stretch `[start, end)` of one activity, in unix seconds.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Segment {
    /// What the time was spent on.
    pub activity: Activity,
    /// Unix seconds the segment begins.
    pub start: i64,
    /// Unix seconds the segment ends.
    pub end: i64,
}

impl Segment {
    /// The segment's length in seconds.
    #[must_use]
    pub fn secs(&self) -> i64 {
        self.end - self.start
    }
}

/// Seconds spent in one activity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct ActivityTotal {
    /// The activity.
    pub activity: Activity,
    /// Total seconds.
    pub secs: i64,
}

/// Append `seg` to `out`, merging with a touching segment of the same activity and dropping empties.
fn push(out: &mut Vec<Segment>, seg: Segment) {
    if seg.end <= seg.start {
        return;
    }
    if let Some(last) = out.last_mut()
        && last.activity == seg.activity
        && last.end == seg.start
    {
        last.end = seg.end;
        return;
    }
    out.push(seg);
}

/// Classify a timeline into ordered, non-overlapping segments.
///
/// A point signal (commit, edit, lease, refusal) runs until the next signal starts, but at most
/// `idle_gap_secs`; any remainder up to the next signal is [`Activity::Idle`]. A measured span
/// (test run, goway job, land) is its own activity for its whole length. The final point signal
/// contributes nothing, since nothing is known about what followed it. Spans overlapping earlier
/// time are clipped to start where the earlier segment ended.
#[must_use]
pub fn classify(signals: &[Signal], idle_gap_secs: i64) -> Vec<Segment> {
    let mut sorted: Vec<Signal> = signals.to_vec();
    sorted.sort_by_key(|s| s.start());
    let mut out: Vec<Segment> = Vec::new();
    let mut cursor = i64::MIN;
    for (i, sig) in sorted.iter().enumerate() {
        let next = sorted.get(i + 1).map(|s| s.start());
        match sig.shape() {
            Shape::Span(from, to, activity) => {
                let start = from.max(cursor);
                push(
                    &mut out,
                    Segment {
                        activity,
                        start,
                        end: to,
                    },
                );
                cursor = cursor.max(to);
            }
            Shape::Point(at, activity) => {
                let Some(next) = next else { continue };
                let start = at.max(cursor);
                let active_end = next.min(at.saturating_add(idle_gap_secs));
                push(
                    &mut out,
                    Segment {
                        activity,
                        start,
                        end: active_end,
                    },
                );
                push(
                    &mut out,
                    Segment {
                        activity: Activity::Idle,
                        start: start.max(active_end),
                        end: next,
                    },
                );
                cursor = cursor.max(next);
            }
        }
    }
    tracing::debug!(
        signals = signals.len(),
        segments = out.len(),
        idle_gap_secs,
        "classified activity timeline"
    );
    out
}

/// Fold segments into one total per activity, in [`Activity::ALL`] order, zero entries kept.
#[must_use]
pub fn totals(segments: &[Segment]) -> Vec<ActivityTotal> {
    Activity::ALL
        .iter()
        .map(|&activity| ActivityTotal {
            activity,
            secs: segments
                .iter()
                .filter(|s| s.activity == activity)
                .map(Segment::secs)
                .sum(),
        })
        .collect()
}

/// A one-line summary such as `implementing 2h0m, testing 5m0s`, omitting zero totals.
#[must_use]
pub fn summary_line(totals: &[ActivityTotal]) -> String {
    let parts: Vec<String> = totals
        .iter()
        .filter(|t| t.secs > 0)
        .map(|t| format!("{} {}", t.activity.name(), human(t.secs)))
        .collect();
    if parts.is_empty() {
        "no activity recorded".to_owned()
    } else {
        parts.join(", ")
    }
}

/// Seconds as `XhYmZs`, dropping leading zero units.
fn human(secs: i64) -> String {
    let (h, m, s) = (secs / 3600, secs % 3600 / 60, secs % 60);
    if h > 0 {
        format!("{h}h{m}m{s}s")
    } else if m > 0 {
        format!("{m}m{s}s")
    } else {
        format!("{s}s")
    }
}

/// Why the journal could not be read or written.
#[derive(Debug, thiserror::Error)]
pub enum JournalError {
    /// The journal file could not be created, appended to or read.
    #[error("activity journal {path}: {source}")]
    Io {
        /// The journal path.
        path: PathBuf,
        /// The underlying error.
        source: std::io::Error,
    },
    /// A signal could not be encoded.
    #[error("activity journal encode: {0}")]
    Encode(#[from] serde_json::Error),
}

/// The local activity journal: one JSON-lines file per ticket in a directory outside any work tree.
#[derive(Debug, Clone)]
pub struct Journal {
    dir: PathBuf,
}

impl Journal {
    /// A journal under `<common_dir>/frob/activity`, the git common dir being shared and uncommitted.
    #[must_use]
    pub fn in_common_dir(common_dir: &Path) -> Self {
        Self {
            dir: common_dir.join("frob").join("activity"),
        }
    }

    /// A journal stored directly in `frob_dir/activity`, where `frob_dir` is `<common_dir>/frob`.
    #[must_use]
    pub fn in_frob_dir(frob_dir: &Path) -> Self {
        Self {
            dir: frob_dir.join("activity"),
        }
    }

    /// Record `signal`, logging instead of failing: activity is observation and must never block the verb observed.
    pub fn record_quietly(&self, ticket: &str, signal: &Signal) {
        if let Err(e) = self.record(ticket, signal) {
            tracing::warn!(ticket, error = %e, "could not record activity signal");
        }
    }

    fn path(&self, ticket: &str) -> PathBuf {
        self.dir.join(format!("{ticket}.jsonl"))
    }

    /// Append `signal` to `ticket`'s journal, creating it on first use.
    ///
    /// # Errors
    ///
    /// [`JournalError`] on encoding or I/O failure.
    pub fn record(&self, ticket: &str, signal: &Signal) -> Result<(), JournalError> {
        let path = self.path(ticket);
        let io = |source| JournalError::Io {
            path: path.clone(),
            source,
        };
        fs::create_dir_all(&self.dir).map_err(io)?;
        let mut line = serde_json::to_string(signal)?;
        line.push('\n');
        let mut f = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&path)
            .map_err(io)?;
        f.write_all(line.as_bytes()).map_err(io)?;
        tracing::debug!(ticket, path = %path.display(), "activity signal recorded");
        Ok(())
    }

    /// Every signal recorded for `ticket`, oldest first; unreadable lines are skipped with a warning.
    ///
    /// # Errors
    ///
    /// [`JournalError::Io`] when the file exists but cannot be read; a missing file is an empty timeline.
    pub fn read(&self, ticket: &str) -> Result<Vec<Signal>, JournalError> {
        let path = self.path(ticket);
        let text = match fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(source) => return Err(JournalError::Io { path, source }),
        };
        Ok(text
            .lines()
            .filter_map(|l| match serde_json::from_str::<Signal>(l) {
                Ok(s) => Some(s),
                Err(e) => {
                    tracing::warn!(ticket, error = %e, "skipping unreadable activity journal line");
                    None
                }
            })
            .collect())
    }

    /// Classify `ticket`'s recorded timeline and total it per activity.
    ///
    /// # Errors
    ///
    /// [`JournalError`] when the journal cannot be read.
    pub fn summarize(
        &self,
        ticket: &str,
        idle_gap_secs: i64,
    ) -> Result<Vec<ActivityTotal>, JournalError> {
        Ok(totals(&classify(&self.read(ticket)?, idle_gap_secs)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seg(activity: Activity, start: i64, end: i64) -> Segment {
        Segment {
            activity,
            start,
            end,
        }
    }

    fn fixture() -> Vec<Signal> {
        vec![
            Signal::Lease { at: 0 },
            Signal::Commit { at: 100 },
            Signal::TestRun { from: 150, to: 250 },
            Signal::LeaseRefused { at: 300 },
            Signal::FileEdit { at: 2000 },
            Signal::Land {
                from: 2100,
                to: 2200,
            },
        ]
    }

    // frob:tests classify
    #[test]
    fn fixture_timeline_classifies_into_expected_segments() {
        let got = classify(&fixture(), 600);
        assert_eq!(
            got,
            vec![
                seg(Activity::Implementing, 0, 150),
                seg(Activity::Testing, 150, 250),
                seg(Activity::Waiting, 300, 900),
                seg(Activity::Idle, 900, 2000),
                seg(Activity::Implementing, 2000, 2100),
                seg(Activity::Landing, 2100, 2200),
            ]
        );
    }

    // frob:tests totals
    #[test]
    fn totals_sum_each_activity() {
        let t = totals(&classify(&fixture(), 600));
        let get = |a| t.iter().find(|x| x.activity == a).map(|x| x.secs);
        assert_eq!(get(Activity::Implementing), Some(150 + 100));
        assert_eq!(get(Activity::Testing), Some(100));
        assert_eq!(get(Activity::Waiting), Some(600));
        assert_eq!(get(Activity::Landing), Some(100));
        assert_eq!(get(Activity::Idle), Some(1100));
    }

    // frob:tests summary_line
    #[test]
    fn summary_omits_zero_totals() {
        let t = totals(&[seg(Activity::Testing, 0, 90)]);
        assert_eq!(summary_line(&t), "testing 1m30s");
        assert_eq!(summary_line(&totals(&[])), "no activity recorded");
    }

    // frob:tests Journal::record
    #[test]
    fn journal_round_trips_and_summarizes() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let dir = tmp.path().to_path_buf();
        let j = Journal::in_common_dir(&dir);
        for s in fixture() {
            j.record("T1", &s).expect("record");
        }
        assert_eq!(j.read("T1").expect("read"), fixture());
        assert!(j.read("other").expect("read").is_empty());
        let t = j.summarize("T1", 600).expect("summarize");
        assert_eq!(t, totals(&classify(&fixture(), 600)));
    }
}
