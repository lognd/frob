//! Per-issue reconcile, never block (mirror.md 3.4; owner decision; MIR002 is Advisory).
//!
//! For one issue the mirror compares the tracker's current values with the projection. For each
//! repository-owned field that diverges, or that history after the cursor shows was changed by
//! someone other than the mirror (including unknown automation: a bot id with no matching
//! journaled write), it plans a revert to the projection and an [`Edit`] to record as a proposal.
//! A tracker-owned field is never reverted and never proposed. Values are compared after the
//! tracker's own normalization ([`ReadBack`]). Nothing here fails a check or a land: an edit whose
//! value cannot be recovered becomes a [`GapKind`] record, never an error.

// frob:ticket 01M4052TC4BVA3JFFCHZX82EWS

use std::collections::BTreeMap;

use gob_time::Stamp;
use tracing::{debug, info};

use crate::adapter::{EventId, IssueRef};
use crate::capture::{Gap, GapKind};
use crate::fields::{FieldOwnership, Owner};
use crate::github::read::HistoryRead;
use crate::journal::{Attribution, Journal, value_digest};
use crate::normalize::{Action, ReadBack};
use crate::proposals::Edit;

/// One planned revert of a repository-owned field to its projected value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Revert {
    /// The field to write back.
    pub field: String,
    /// The projected value to write.
    pub value: String,
}

/// What reconciling one issue decided; applying it is the caller's job.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Reconciled {
    /// Writes that restore the projection, in field order.
    pub reverts: Vec<Revert>,
    /// Outside edits to record as proposals, oldest first.
    pub edits: Vec<Edit>,
    /// Cases where an edit or change could not be fully captured.
    pub gaps: Vec<Gap>,
}

/// Everything reconcile reads for one issue.
pub struct IssueView<'a> {
    /// The tracker issue.
    pub issue: &'a IssueRef,
    /// Field ownership from `[mirror.fields]`.
    pub ownership: &'a FieldOwnership,
    /// The rendered projection, field to value.
    pub projection: &'a BTreeMap<String, String>,
    /// The tracker's current values, field to value.
    pub current: &'a BTreeMap<String, String>,
    /// History strictly after the stored cursor.
    pub history: &'a HistoryRead,
    /// Full values of history events when the tracker retained them (revision content).
    pub event_values: &'a BTreeMap<EventId, String>,
    /// The ticket's write journal, for own-write attribution.
    pub journal: &'a Journal,
    /// The mirror's tracker user ids.
    pub bot_ids: &'a [u64],
    /// The stored read-back record, for normalized comparison.
    pub read_back: &'a ReadBack,
    /// The run's time, stamped on recorded edits.
    pub now: Stamp,
}

/// Reconciles one issue: reverts and records outside changes to repository-owned fields.
pub fn reconcile_issue(view: &IssueView<'_>) -> Reconciled {
    let mut out = Reconciled::default();
    let repo_owned = |f: &str| view.ownership.owner(f) == Some(Owner::Repository);
    for entry in &view.history.entries {
        if !repo_owned(&entry.field) {
            debug!(field = %entry.field, "reconcile: tracker-owned or unprojected, left alone");
            continue;
        }
        if view.journal.classify(view.bot_ids, view.issue, entry) == Attribution::Own {
            continue;
        }
        let value = view.event_values.get(&entry.event).or_else(|| {
            view.current
                .get(&entry.field)
                .filter(|c| value_digest(c) == entry.value_digest)
        });
        match value {
            Some(v) => {
                info!(issue = %view.issue.0, field = %entry.field, "reconcile: outside edit proposed");
                out.edits.push(Edit {
                    tracker_event: entry.event.clone(),
                    item: view.issue.0.clone(),
                    field: entry.field.clone(),
                    actor_id: entry.actor_id.to_string(),
                    time: view.now,
                    value: v.clone(),
                });
            }
            None => out.gaps.push(Gap {
                issue: view.issue.clone(),
                field: Some(entry.field.clone()),
                kind: GapKind::BeyondRetention,
            }),
        }
    }
    for (field, want) in view.projection {
        let Some(now) = view.current.get(field).filter(|_| repo_owned(field)) else {
            continue;
        };
        if view.read_back.plan(field, want, now) == Action::Skip {
            continue;
        }
        info!(issue = %view.issue.0, field = %field, "reconcile: revert to projection");
        out.reverts.push(Revert {
            field: field.clone(),
            value: want.clone(),
        });
        if !view.history.entries.iter().any(|e| &e.field == field) {
            out.gaps.push(Gap {
                issue: view.issue.clone(),
                field: Some(field.clone()),
                kind: GapKind::Unexplained,
            });
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::HistoryEntry;
    use crate::fields::FieldsConfig;
    use crate::github::read::Fidelity;
    use crate::journal::{JournalEntry, WriteStatus};
    use crate::proposals::{ProposalSink, record};
    use frob_ledger::event::Event;

    fn ownership() -> FieldOwnership {
        let cfg = FieldsConfig {
            owners: BTreeMap::from([
                ("title".to_owned(), Owner::Repository),
                ("assignee".to_owned(), Owner::Tracker),
            ]),
            tracker_owned: vec![],
        };
        FieldOwnership::load(&cfg, &["title", "assignee"]).unwrap()
    }

    fn map(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect()
    }

    fn entry(ev: &str, actor: u64, field: &str, value: &str) -> HistoryEntry {
        HistoryEntry {
            event: EventId(ev.into()),
            actor_id: actor,
            field: field.into(),
            value_digest: value_digest(value),
        }
    }

    struct Vec2(Vec<Event>);
    impl ProposalSink for Vec2 {
        type Error = ();
        fn commit(&mut self, events: Vec<Event>) -> Result<(), ()> {
            self.0.extend(events);
            Ok(())
        }
    }

    fn run(
        projection: &[(&str, &str)],
        current: &[(&str, &str)],
        entries: Vec<HistoryEntry>,
        journal: &Journal,
        revisions: &[(&str, &str)],
    ) -> Reconciled {
        let issue = IssueRef("7".into());
        let own = ownership();
        let history = HistoryRead {
            entries,
            fidelity: Fidelity::Full,
        };
        let rb = ReadBack::new();
        let ev: BTreeMap<EventId, String> = revisions
            .iter()
            .map(|(k, v)| (EventId((*k).into()), (*v).to_owned()))
            .collect();
        reconcile_issue(&IssueView {
            issue: &issue,
            ownership: &own,
            projection: &map(projection),
            current: &map(current),
            history: &history,
            event_values: &ev,
            journal,
            bot_ids: &[99],
            read_back: &rb,
            now: Stamp::from_unix(1_000),
        })
    }

    // frob:tests reconcile_issue
    #[test]
    fn edited_title_is_reverted_once_proposed_once_and_second_run_is_quiet() {
        let first = run(
            &[("title", "Right")],
            &[("title", "Human")],
            vec![entry("e1", 5, "title", "Human")],
            &Journal::default(),
            &[],
        );
        assert_eq!(first.reverts.len(), 1);
        assert_eq!(first.reverts[0].value, "Right");
        assert_eq!(first.edits.len(), 1);
        let mut sink = Vec2(vec![]);
        let rec = record(
            &mut sink,
            &[],
            &first.edits,
            "mirror",
            Stamp::from_unix(1_000),
            5,
        )
        .unwrap();
        assert_eq!(rec.appended, 1);
        let second = run(
            &[("title", "Right")],
            &[("title", "Right")],
            vec![],
            &Journal::default(),
            &[],
        );
        assert_eq!(second, Reconciled::default());
        let existing = sink.0.clone();
        let again = record(
            &mut sink,
            &existing,
            &first.edits,
            "mirror",
            Stamp::from_unix(1_000),
            5,
        )
        .unwrap();
        assert_eq!(again.appended, 0);
    }

    // frob:tests reconcile_issue
    #[test]
    fn tracker_owned_field_is_left_unchanged() {
        let out = run(
            &[("title", "T"), ("assignee", "a")],
            &[("title", "T"), ("assignee", "b")],
            vec![entry("e1", 5, "assignee", "b")],
            &Journal::default(),
            &[],
        );
        assert_eq!(out, Reconciled::default());
    }

    // frob:tests reconcile_issue
    #[test]
    fn bot_entry_without_journaled_write_is_unknown_automation_and_reverted() {
        let out = run(
            &[("title", "Right")],
            &[("title", "Bot")],
            vec![entry("e1", 99, "title", "Bot")],
            &Journal::default(),
            &[],
        );
        assert_eq!(out.reverts.len(), 1);
        assert_eq!(out.edits.len(), 1);
        assert_eq!(out.edits[0].actor_id, "99");
        let journal = Journal {
            entries: vec![JournalEntry {
                issue: IssueRef("7".into()),
                field: "title".into(),
                value_digest: value_digest("Right"),
                run_id: "r".into(),
                time: "t".into(),
                status: WriteStatus::Confirmed,
            }],
        };
        let own = run(
            &[("title", "Right")],
            &[("title", "Right")],
            vec![entry("e2", 99, "title", "Right")],
            &journal,
            &[],
        );
        assert_eq!(own, Reconciled::default());
    }

    // frob:tests reconcile_issue
    #[test]
    fn edit_between_read_and_write_is_recorded_next_run() {
        // The mirror overwrote the human's edit, so the title already matches the projection.
        let out = run(
            &[("title", "Right")],
            &[("title", "Right")],
            vec![entry("e1", 5, "title", "Mid")],
            &Journal::default(),
            &[("e1", "Mid")],
        );
        assert!(out.reverts.is_empty());
        assert_eq!(out.edits.len(), 1);
        assert_eq!(out.edits[0].tracker_event, EventId("e1".into()));
        assert!(out.gaps.is_empty());
    }
}
