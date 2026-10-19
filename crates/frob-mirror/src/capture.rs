//! Read-time capture, fidelity gap and the gap listing (mirror.md 3.4, "what nothing is lost means").
//!
//! The value present at read time is always captured by comparing its digest with the last
//! observed one. Intermediate values and their authors come from history while it retains them;
//! a change no history entry explains is captured with [`Fidelity::Gap`] and no author. Cases
//! with no per-issue history (repository-level renames, project fields other than status,
//! deletions, history beyond retention) are recorded as gaps via [`GapListing`] for
//! `frob mirror status`. A gap is a record, never an error.

// frob:ticket 01M4052SVV8ZVVX0AW4MN0Q367

use std::collections::{BTreeMap, BTreeSet};

use tracing::{debug, info};

use crate::adapter::{EventId, IssueRef};
use crate::github::read::{Fidelity, HistoryRead};

/// Why a value could not be captured with full fidelity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum GapKind {
    /// The value changed and no history entry explains it.
    Unexplained,
    /// History beyond the retained window (or deleted revisions) is missing.
    BeyondRetention,
    /// A repository-level label, milestone or issue-type rename (caught once by inventory).
    RepositoryRename,
    /// A project field other than status, which has no per-issue history.
    ProjectField,
    /// A deletion, which leaves no per-issue history.
    Deletion,
}

impl GapKind {
    /// Stable lowercase name used in the gap listing.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Unexplained => "unexplained",
            Self::BeyondRetention => "beyond-retention",
            Self::RepositoryRename => "repository-rename",
            Self::ProjectField => "project-field",
            Self::Deletion => "deletion",
        }
    }
}

/// One recorded gap: where history is missing and why.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Gap {
    /// The affected issue.
    pub issue: IssueRef,
    /// The affected field, when the gap is specific to one.
    pub field: Option<String>,
    /// Why it is a gap.
    pub kind: GapKind,
}

/// One captured value with its provenance and fidelity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capture {
    /// The field the value belongs to.
    pub field: String,
    /// Digest of the captured value.
    pub value_digest: String,
    /// Tracker user id of the author; `None` when no history explains the value.
    pub actor_id: Option<u64>,
    /// The history event the value came from; `None` for a read-time capture.
    pub event: Option<EventId>,
    /// `Full` when history explains it, `Gap` otherwise.
    pub fidelity: Fidelity,
}

/// What one issue's read captured and which gaps it found.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CaptureOutcome {
    /// Captured values, history entries first (oldest first) then read-time captures.
    pub captures: Vec<Capture>,
    /// Gaps found in this read.
    pub gaps: Vec<Gap>,
}

/// Captures one issue's changes: every retained history entry, then the current value of each
/// field that differs from `last` and is not explained by the latest history entry for it.
///
/// `last` and `current` map a field to the digest of its value. A field absent from `last` was
/// never observed and is a baseline, not a change.
pub fn capture_issue(
    issue: &IssueRef,
    last: &BTreeMap<String, String>,
    current: &BTreeMap<String, String>,
    history: &HistoryRead,
) -> CaptureOutcome {
    let mut out = CaptureOutcome::default();
    let mut latest: BTreeMap<&str, &str> = BTreeMap::new();
    for e in &history.entries {
        latest.insert(&e.field, &e.value_digest);
        out.captures.push(Capture {
            field: e.field.clone(),
            value_digest: e.value_digest.clone(),
            actor_id: Some(e.actor_id),
            event: Some(e.event.clone()),
            fidelity: Fidelity::Full,
        });
    }
    if history.fidelity == Fidelity::Gap {
        info!(issue = %issue.0, "capture: history beyond retention");
        out.gaps.push(Gap {
            issue: issue.clone(),
            field: None,
            kind: GapKind::BeyondRetention,
        });
    }
    for (field, digest) in current {
        let changed = last.get(field).is_some_and(|prev| prev != digest);
        if !changed || latest.get(field.as_str()) == Some(&digest.as_str()) {
            continue;
        }
        info!(issue = %issue.0, field = %field, "capture: unexplained change, fidelity gap");
        out.captures.push(Capture {
            field: field.clone(),
            value_digest: digest.clone(),
            actor_id: None,
            event: None,
            fidelity: Fidelity::Gap,
        });
        out.gaps.push(Gap {
            issue: issue.clone(),
            field: Some(field.clone()),
            kind: GapKind::Unexplained,
        });
    }
    debug!(issue = %issue.0, captures = out.captures.len(), gaps = out.gaps.len(), "capture: done");
    out
}

/// Gaps accumulated over a run, deduplicated and ordered, for `frob mirror status`.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct GapListing(BTreeSet<Gap>);

impl GapListing {
    /// An empty listing.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds `gaps` to the listing; a repeated gap is listed once.
    pub fn extend(&mut self, gaps: impl IntoIterator<Item = Gap>) {
        self.0.extend(gaps);
    }

    /// Records a case that has no per-issue history (rename, project field, deletion).
    pub fn record_no_history(&mut self, issue: &IssueRef, field: Option<&str>, kind: GapKind) {
        info!(issue = %issue.0, kind = kind.as_str(), "capture: no per-issue history, gap");
        self.0.insert(Gap {
            issue: issue.clone(),
            field: field.map(str::to_owned),
            kind,
        });
    }

    /// The gaps in stable order.
    pub fn list(&self) -> Vec<&Gap> {
        self.0.iter().collect()
    }

    /// Whether no gap is recorded.
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::HistoryEntry;

    fn map(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect()
    }

    fn entry(ev: &str, actor: u64, field: &str, digest: &str) -> HistoryEntry {
        HistoryEntry {
            event: EventId(ev.into()),
            actor_id: actor,
            field: field.into(),
            value_digest: digest.into(),
        }
    }

    fn read(entries: Vec<HistoryEntry>, fidelity: Fidelity) -> HistoryRead {
        HistoryRead { entries, fidelity }
    }

    #[test]
    fn unexplained_change_is_captured_with_gap() {
        let i = IssueRef("1".into());
        let out = capture_issue(
            &i,
            &map(&[("title", "a")]),
            &map(&[("title", "b")]),
            &read(vec![], Fidelity::Full),
        );
        assert_eq!(out.captures.len(), 1);
        assert_eq!(out.captures[0].fidelity, Fidelity::Gap);
        assert_eq!(out.captures[0].actor_id, None);
        assert_eq!(out.gaps[0].kind, GapKind::Unexplained);
    }

    #[test]
    fn beyond_retention_is_recorded_and_listed() {
        let i = IssueRef("2".into());
        let out = capture_issue(&i, &map(&[]), &map(&[]), &read(vec![], Fidelity::Gap));
        assert_eq!(out.gaps[0].kind, GapKind::BeyondRetention);
        let mut listing = GapListing::new();
        listing.extend(out.gaps.clone());
        listing.extend(out.gaps);
        assert_eq!(listing.list().len(), 1);
        assert_eq!(listing.list()[0].issue, i);
    }

    #[test]
    fn two_changes_keep_both_values_and_authors() {
        let i = IssueRef("3".into());
        let h = read(
            vec![entry("e1", 10, "title", "b"), entry("e2", 11, "title", "c")],
            Fidelity::Full,
        );
        let out = capture_issue(&i, &map(&[("title", "a")]), &map(&[("title", "c")]), &h);
        assert!(out.gaps.is_empty());
        let got: Vec<_> = out
            .captures
            .iter()
            .map(|c| (c.value_digest.as_str(), c.actor_id, c.fidelity))
            .collect();
        assert_eq!(
            got,
            vec![
                ("b", Some(10), Fidelity::Full),
                ("c", Some(11), Fidelity::Full)
            ]
        );
    }

    #[test]
    fn no_history_cases_are_listed() {
        let i = IssueRef("4".into());
        let mut l = GapListing::new();
        l.record_no_history(&i, Some("label:x"), GapKind::RepositoryRename);
        l.record_no_history(&i, None, GapKind::Deletion);
        assert_eq!(l.list().len(), 2);
        assert!(!l.is_empty());
    }
}
