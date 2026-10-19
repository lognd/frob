//! Duplicate closing on every run (mirror.md 3.3 "Duplicates"; F6).
//!
//! When two bot issues carry valid markers for one ULID, the lowest issue number is canonical.
//! The others are closed as duplicates of it. A duplicate keeps its marker, so it is never
//! re-adopted, and its history is still read, so edits a human made on it are captured. The
//! check runs on every run, not only on first sync: a human reopening a duplicate, or a late
//! create landing after its retry, is closed again on the next listing.

// frob:ticket 01M4052SBZCJ3MRHGTPAFW4QP1

use std::collections::BTreeMap;

use tracing::{debug, info, warn};

use crate::adapter::{
    AdapterError, AdapterResult, EventId, HistoryEntry, IssueRef, TrackerAdapter,
};
use crate::marker::MarkerVerdict;
use crate::projection::Outcome;

/// One bot issue whose creation revision carries a valid marker for `ulid`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Claim {
    /// The issue holding the marker.
    pub issue: IssueRef,
    /// The ticket ULID the marker names.
    pub ulid: String,
}

/// An issue closed (or to be closed) as a duplicate of the canonical one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Duplicate {
    /// The ticket both issues claim.
    pub ulid: String,
    /// The duplicate issue.
    pub issue: IssueRef,
    /// The canonical issue (lowest number) for the ticket.
    pub canonical: IssueRef,
}

/// Which issue is canonical per ULID and which others are duplicates.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DupPlan {
    /// Canonical issue per ticket ULID.
    pub canonical: BTreeMap<String, IssueRef>,
    /// Every non-canonical claimant, ordered by ULID then issue number.
    pub duplicates: Vec<Duplicate>,
}

/// What closing the duplicates did.
#[derive(Debug, Default)]
pub struct DupReport {
    /// Duplicates this run closed (new, or reopened by a human).
    pub closed: Vec<IssueRef>,
    /// Duplicates already closed; nothing written.
    pub already_closed: Vec<IssueRef>,
    /// Duplicates whose read or close failed; the next run retries them.
    pub failed: Vec<(IssueRef, AdapterError)>,
}

/// Keep the adopted markers from per-issue verdicts; every other verdict claims nothing.
pub fn claims_from_verdicts(
    items: impl IntoIterator<Item = (IssueRef, MarkerVerdict)>,
) -> Vec<Claim> {
    items
        .into_iter()
        .filter_map(|(issue, verdict)| match verdict {
            MarkerVerdict::Adopted(m) => Some(Claim {
                issue,
                ulid: m.fields.ulid,
            }),
            _ => None,
        })
        .collect()
}

/// Order issue refs by number; a non-numeric ref sorts after every number, then lexically.
fn number_key(issue: &IssueRef) -> (u64, &str) {
    (issue.0.parse().unwrap_or(u64::MAX), issue.0.as_str())
}

/// Pick the lowest-numbered claimant per ULID as canonical; the rest are duplicates.
pub fn plan_duplicates(claims: &[Claim]) -> DupPlan {
    let mut by_ulid: BTreeMap<&str, Vec<&IssueRef>> = BTreeMap::new();
    for c in claims {
        by_ulid.entry(c.ulid.as_str()).or_default().push(&c.issue);
    }
    let mut plan = DupPlan::default();
    for (ulid, mut issues) in by_ulid {
        issues.sort_by_key(|i| number_key(i));
        issues.dedup();
        let canonical = issues[0].clone();
        for dup in &issues[1..] {
            debug!(ulid, canonical = %canonical.0, duplicate = %dup.0, "dups: duplicate found");
            plan.duplicates.push(Duplicate {
                ulid: ulid.to_string(),
                issue: (*dup).clone(),
                canonical: canonical.clone(),
            });
        }
        plan.canonical.insert(ulid.to_string(), canonical);
    }
    plan
}

/// Close every duplicate that is open; a reopened duplicate is closed again. Never edits the
/// body, so the marker stays and the issue is not re-adopted.
pub fn close_duplicates<A: TrackerAdapter + ?Sized>(adapter: &mut A, plan: &DupPlan) -> DupReport {
    let mut report = DupReport::default();
    for d in &plan.duplicates {
        let state = match adapter.read(&d.issue) {
            Ok(s) => s,
            Err(e) => {
                warn!(issue = %d.issue.0, error = %e, "dups: read failed; retry next run");
                report.failed.push((d.issue.clone(), e));
                continue;
            }
        };
        if state.closed {
            debug!(issue = %d.issue.0, "dups: already closed");
            report.already_closed.push(d.issue.clone());
            continue;
        }
        match adapter.close(&d.issue, Outcome::Duplicate) {
            Ok(()) => {
                info!(issue = %d.issue.0, canonical = %d.canonical.0, ulid = %d.ulid, "dups: closed duplicate");
                report.closed.push(d.issue.clone());
            }
            Err(e) => {
                warn!(issue = %d.issue.0, error = %e, "dups: close failed; retry next run");
                report.failed.push((d.issue.clone(), e));
            }
        }
    }
    report
}

/// Read each duplicate's history after its cursor (all when absent), so edits made on a closed
/// duplicate are captured like any other issue's.
pub fn read_duplicate_history<A: TrackerAdapter + ?Sized>(
    adapter: &A,
    plan: &DupPlan,
    cursors: &BTreeMap<IssueRef, EventId>,
) -> Vec<(IssueRef, AdapterResult<Vec<HistoryEntry>>)> {
    plan.duplicates
        .iter()
        .map(|d| {
            let h = adapter.history_after(&d.issue, cursors.get(&d.issue));
            debug!(issue = %d.issue.0, ok = h.is_ok(), "dups: read duplicate history");
            (d.issue.clone(), h)
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn claim(n: &str, ulid: &str) -> Claim {
        Claim {
            issue: IssueRef(n.into()),
            ulid: ulid.into(),
        }
    }

    // frob:tests plan_duplicates
    #[test]
    fn lowest_number_is_canonical_numerically() {
        let plan = plan_duplicates(&[
            claim("10", "A"),
            claim("9", "A"),
            claim("30", "A"),
            claim("5", "B"),
        ]);
        assert_eq!(plan.canonical["A"], IssueRef("9".into()));
        let dups: Vec<_> = plan.duplicates.iter().map(|d| d.issue.0.as_str()).collect();
        assert_eq!(dups, ["10", "30"]);
        assert_eq!(plan.canonical["B"].0, "5");
    }

    // frob:tests plan_duplicates
    #[test]
    fn same_issue_listed_twice_is_not_a_duplicate() {
        let plan = plan_duplicates(&[claim("3", "A"), claim("3", "A")]);
        assert!(plan.duplicates.is_empty());
    }

    // frob:tests claims_from_verdicts
    #[test]
    fn only_adopted_verdicts_claim() {
        let got = claims_from_verdicts([
            (IssueRef("1".into()), MarkerVerdict::Spoofed),
            (IssueRef("2".into()), MarkerVerdict::None),
        ]);
        assert!(got.is_empty());
    }
}
