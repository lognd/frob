//! The `baselined` section of the check envelope: findings `frob-baseline.toml` mutes.
//!
//! A baselined finding is an Error whose fingerprint the repository's baseline file lists. It no
//! longer counts toward the gate, but it is never dropped: the envelope keeps it (JSON mode) with
//! the per-rule count of keys the baseline still carries, so the debt stays visible.

// frob:ticket 01M66G70F82EC8EERE0077QKVV

use std::collections::BTreeMap;
use std::path::Path;

use gob_diagnostics::FindingRecord;
use gob_rules::{BASELINE_FILE, Baseline, Finding};
use schemars::JsonSchema;
use serde::Serialize;

/// Findings the baseline muted, with the per-rule number of keys it still lists.
#[derive(Debug, Clone, Default, Serialize, JsonSchema)]
pub struct BaselinedSection {
    /// How many findings the baseline muted in this run.
    pub count: usize,
    /// Keys the baseline still lists per rule (the debt left to burn down).
    pub remaining: BTreeMap<String, usize>,
    /// The muted findings as structured records (filled in JSON mode only).
    pub findings: Vec<FindingRecord>,
}

/// What [`split`] found: the findings left live, the muted ones, the remaining totals and any note.
#[derive(Debug, Default)]
pub struct Split {
    /// Findings still counting toward the gate.
    pub live: Vec<Finding>,
    /// Findings the baseline muted.
    pub baselined: Vec<Finding>,
    /// Keys the baseline still lists per rule.
    pub remaining: BTreeMap<String, usize>,
    /// A non-fatal note (an unreadable baseline file), shown with the other notes.
    pub note: Option<String>,
}

/// Partition `findings` by the baseline file at `root`; no file means everything stays live.
pub fn split(root: &Path, findings: Vec<Finding>) -> Split {
    // The baseline is repository config read once per run, not walked rule content.
    #[allow(clippy::disallowed_methods)]
    let read = std::fs::read_to_string(root.join(BASELINE_FILE));
    let text = match read {
        Ok(text) => text,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            tracing::debug!("no baseline file; nothing is baselined");
            return Split {
                live: findings,
                ..Split::default()
            };
        }
        Err(e) => {
            tracing::warn!(error = %e, "baseline file unreadable; nothing is baselined");
            return Split {
                live: findings,
                note: Some(format!("{BASELINE_FILE} could not be read: {e}")),
                ..Split::default()
            };
        }
    };
    match Baseline::parse(&text) {
        Ok(baseline) => {
            let remaining = baseline
                .remaining()
                .into_iter()
                .map(|(rule, n)| (rule.to_owned(), n))
                .collect();
            let (live, baselined) = baseline.partition(findings);
            tracing::info!(baselined = baselined.len(), "baseline muted findings");
            Split {
                live,
                baselined,
                remaining,
                note: None,
            }
        }
        Err(e) => {
            tracing::warn!(error = %e, "baseline file invalid; nothing is baselined");
            Split {
                live: findings,
                note: Some(format!("{BASELINE_FILE} is invalid and was ignored: {e}")),
                ..Split::default()
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::Severity;

    fn finding(rule: &str, anchor: &str) -> Finding {
        Finding::new(rule.parse().unwrap(), Severity::Error, None, "msg", anchor)
    }

    // frob:tests crates/frob-check/src/baselined.rs::split
    #[test]
    fn split_mutes_listed_findings_and_reports_remaining_totals() {
        let dir = tempfile::tempdir().unwrap();
        let a = finding("DOC001", "a");
        let b = finding("DOC001", "b");
        let mut base = Baseline::default();
        let rule: gob_rules::RuleId = "DOC001".parse().unwrap();
        base.adopt(&rule, "debt", "~ABC1234", std::slice::from_ref(&a))
            .unwrap();
        std::fs::write(dir.path().join(BASELINE_FILE), base.render()).unwrap();
        let s = split(dir.path(), vec![a, b.clone()]);
        assert_eq!(s.baselined.len(), 1);
        assert_eq!(s.live, vec![b]);
        assert_eq!(s.remaining.get("DOC001"), Some(&1));
        assert!(s.note.is_none());
    }

    // frob:tests crates/frob-check/src/baselined.rs::split
    #[test]
    fn split_without_a_file_or_with_a_bad_one_keeps_everything_live() {
        let dir = tempfile::tempdir().unwrap();
        let f = finding("DOC001", "a");
        let none = split(dir.path(), vec![f.clone()]);
        assert_eq!((none.live.len(), none.baselined.len()), (1, 0));
        assert!(none.note.is_none());
        std::fs::write(dir.path().join(BASELINE_FILE), "<<<<<<< x\n").unwrap();
        let bad = split(dir.path(), vec![f]);
        assert_eq!((bad.live.len(), bad.baselined.len()), (1, 0));
        assert!(bad.note.is_some());
    }
}
