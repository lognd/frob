//! GitHub history reads (mirror.md 3.3, 3.4): issue state, history after an event id, and the
//! creation revision of the body.
//!
//! The HTTP client is not part of this module: a `HistorySource` supplies raw timeline events and
//! body revisions (live from GraphQL, or recorded fixtures offline). This module merges them into
//! ordered `HistoryEntry` values, finds the creation revision, and reports a fidelity gap
//! (original body plus latest 99 edits only, deleted revision content, cursor event pruned)
//! instead of failing.

// frob:ticket 01M4052R0DZK01W7K8EE77637T

use tracing::{debug, trace, warn};

use crate::adapter::{AdapterResult, EventId, HistoryEntry, IssueRef, IssueState};
use crate::journal::value_digest;

/// GitHub keeps the original body plus this many latest edits.
pub const RETAINED_BODY_EDITS: usize = 99;

/// One timeline event that changed a field (label, assignee, title, state, ...).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TimelineEvent {
    /// Event id (stable, comparable by position in the timeline).
    pub id: String,
    /// Creation time, RFC 3339 UTC.
    pub created_at: String,
    /// Actor user id.
    pub actor_id: u64,
    /// Field changed.
    pub field: String,
    /// New value of the field.
    pub value: String,
}

/// One revision of the issue body.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BodyRevision {
    /// Revision id.
    pub id: String,
    /// Time of the revision, RFC 3339 UTC.
    pub created_at: String,
    /// Editor (author for the first revision) user id; `None` when the account is gone.
    pub editor_id: Option<u64>,
    /// Body text at this revision; `None` when a writer deleted the revision content.
    pub body: Option<String>,
}

/// Raw body revisions, oldest first, plus whether older ones were dropped by GitHub.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BodyRevisions {
    /// Revisions oldest first.
    pub revisions: Vec<BodyRevision>,
    /// True when the tracker holds more revisions than it returned (past the 99-edit window).
    pub truncated: bool,
}

/// Raw reads one GitHub issue needs; implemented by the live client and by fixtures.
pub trait HistorySource {
    /// Current values of the issue.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the tracker call fails.
    fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState>;
    /// The issue's field-changing timeline events, oldest first.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the tracker call fails.
    fn timeline(&self, issue: &IssueRef) -> AdapterResult<Vec<TimelineEvent>>;
    /// The issue's body revisions, oldest first.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the tracker call fails.
    fn body_revisions(&self, issue: &IssueRef) -> AdapterResult<BodyRevisions>;
}

/// Whether recorded history is complete or has a known hole.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Fidelity {
    /// Everything the protocol needs was readable.
    Full,
    /// Something was not retained or was deleted (mirror.md 3.4 `fidelity = gap`).
    Gap,
}

/// History after a cursor, with its fidelity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoryRead {
    /// Entries strictly after the cursor, in order.
    pub entries: Vec<HistoryEntry>,
    /// Whether anything is missing.
    pub fidelity: Fidelity,
}

/// The first revision of the body and its author.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CreationRevision {
    /// Author user id of the first revision.
    pub author_id: u64,
    /// Body text of the first revision; `None` when deleted or no longer retained.
    pub body: Option<String>,
    /// `Gap` when the first revision is not the true original or its content is gone.
    pub fidelity: Fidelity,
}

/// Read one issue's current values.
///
/// # Errors
/// Returns the source's `AdapterError` when the read fails.
pub fn read_issue(source: &dyn HistorySource, issue: &IssueRef) -> AdapterResult<IssueState> {
    trace!(issue = %issue.0, "github read: issue state");
    source.issue(issue)
}

/// Read timeline and body-edit entries strictly after `after` (all when `None`), oldest first.
///
/// The result carries `Fidelity::Gap` when body revisions were truncated or had deleted content,
/// or when `after` is no longer present (then every entry is returned); it never fails for those.
///
/// # Errors
/// Returns the source's `AdapterError` when a read fails.
pub fn history_after(
    source: &dyn HistorySource,
    issue: &IssueRef,
    after: Option<&EventId>,
) -> AdapterResult<HistoryRead> {
    let timeline = source.timeline(issue)?;
    let bodies = source.body_revisions(issue)?;
    let mut fidelity = Fidelity::Full;
    if bodies.truncated {
        warn!(issue = %issue.0, "github read: body edits past the retained window");
        fidelity = Fidelity::Gap;
    }

    // (created_at, id, entry); the first body revision is the original, not an edit.
    let mut merged: Vec<(String, HistoryEntry)> = Vec::new();
    for e in timeline {
        merged.push((
            e.created_at,
            HistoryEntry {
                event: EventId(e.id),
                actor_id: e.actor_id,
                field: e.field,
                value_digest: value_digest(&e.value),
            },
        ));
    }
    let skip_original = usize::from(!bodies.truncated);
    for r in bodies.revisions.into_iter().skip(skip_original) {
        let Some(body) = r.body else {
            warn!(issue = %issue.0, revision = %r.id, "github read: revision content deleted");
            fidelity = Fidelity::Gap;
            continue;
        };
        merged.push((
            r.created_at,
            HistoryEntry {
                event: EventId(r.id),
                actor_id: r.editor_id.unwrap_or(0),
                field: "body".into(),
                value_digest: value_digest(&body),
            },
        ));
    }
    merged.sort_by(|a, b| (&a.0, &a.1.event).cmp(&(&b.0, &b.1.event)));
    let all: Vec<HistoryEntry> = merged.into_iter().map(|(_, e)| e).collect();

    let entries = match after {
        None => all,
        Some(cursor) => {
            if let Some(i) = all.iter().position(|e| &e.event == cursor) {
                all.into_iter().skip(i + 1).collect()
            } else {
                warn!(issue = %issue.0, cursor = %cursor.0, "github read: cursor event not found");
                fidelity = Fidelity::Gap;
                all
            }
        }
    };
    debug!(issue = %issue.0, count = entries.len(), ?fidelity, "github read: history read");
    Ok(HistoryRead { entries, fidelity })
}

/// Read the creation revision of the body: the first revision and its author, regardless of
/// later edits. With no edit history the current body is the creation revision, by `creator_id`.
///
/// # Errors
/// Returns the source's `AdapterError` when a read fails.
pub fn creation_revision(
    source: &dyn HistorySource,
    issue: &IssueRef,
    creator_id: u64,
) -> AdapterResult<CreationRevision> {
    let bodies = source.body_revisions(issue)?;
    let Some(first) = bodies.revisions.first() else {
        let state = source.issue(issue)?;
        debug!(issue = %issue.0, "github read: unedited body is the creation revision");
        return Ok(CreationRevision {
            author_id: creator_id,
            body: Some(state.body),
            fidelity: Fidelity::Full,
        });
    };
    let mut fidelity = Fidelity::Full;
    if bodies.truncated {
        warn!(issue = %issue.0, "github read: original body no longer retained");
        fidelity = Fidelity::Gap;
    }
    if first.body.is_none() {
        warn!(issue = %issue.0, "github read: creation revision content deleted");
        fidelity = Fidelity::Gap;
    }
    Ok(CreationRevision {
        author_id: first.editor_id.unwrap_or(creator_id),
        body: first.body.clone(),
        fidelity,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::AdapterError;

    struct Fake {
        timeline: Vec<TimelineEvent>,
        bodies: BodyRevisions,
    }

    impl HistorySource for Fake {
        fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
            Ok(IssueState {
                issue: issue.clone(),
                title: "t".into(),
                body: "current".into(),
                labels: vec![],
                assignees: vec![],
                closed: false,
            })
        }
        fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
            Ok(self.timeline.clone())
        }
        fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
            Ok(self.bodies.clone())
        }
    }

    struct Bad;
    impl HistorySource for Bad {
        fn issue(&self, _: &IssueRef) -> AdapterResult<IssueState> {
            Err(AdapterError::Gone)
        }
        fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
            Ok(vec![])
        }
        fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
            Ok(BodyRevisions::default())
        }
    }

    fn ev(id: &str, at: &str, actor: u64, field: &str, v: &str) -> TimelineEvent {
        TimelineEvent {
            id: id.into(),
            created_at: at.into(),
            actor_id: actor,
            field: field.into(),
            value: v.into(),
        }
    }

    fn rev(id: &str, at: &str, who: u64, body: Option<&str>) -> BodyRevision {
        BodyRevision {
            id: id.into(),
            created_at: at.into(),
            editor_id: Some(who),
            body: body.map(Into::into),
        }
    }

    fn fake() -> Fake {
        Fake {
            timeline: vec![
                ev("E1", "2026-01-01T00:00:01Z", 5, "labels", "a"),
                ev("E3", "2026-01-01T00:00:03Z", 6, "title", "new"),
            ],
            bodies: BodyRevisions {
                revisions: vec![
                    rev("R0", "2026-01-01T00:00:00Z", 1, Some("orig")),
                    rev("R2", "2026-01-01T00:00:02Z", 7, Some("edited")),
                ],
                truncated: false,
            },
        }
    }

    // frob:tests history_after
    #[test]
    fn history_after_event_is_ordered_with_actor_field_and_digest() {
        let r = history_after(&fake(), &IssueRef("1".into()), Some(&EventId("E1".into()))).unwrap();
        let ids: Vec<_> = r.entries.iter().map(|e| e.event.0.as_str()).collect();
        assert_eq!(ids, ["R2", "E3"]);
        assert_eq!(r.entries[0].actor_id, 7);
        assert_eq!(r.entries[0].field, "body");
        assert_eq!(r.entries[0].value_digest, value_digest("edited"));
        assert_eq!(r.entries[1].field, "title");
        assert_eq!(r.fidelity, Fidelity::Full);
        let all = history_after(&fake(), &IssueRef("1".into()), None).unwrap();
        assert_eq!(all.entries.len(), 3);
    }

    // frob:tests creation_revision
    #[test]
    fn creation_revision_is_first_regardless_of_later_edits() {
        let c = creation_revision(&fake(), &IssueRef("1".into()), 99).unwrap();
        assert_eq!(c.author_id, 1);
        assert_eq!(c.body.as_deref(), Some("orig"));
        assert_eq!(c.fidelity, Fidelity::Full);
        let unedited = Fake {
            timeline: vec![],
            bodies: BodyRevisions::default(),
        };
        let c = creation_revision(&unedited, &IssueRef("1".into()), 99).unwrap();
        assert_eq!((c.author_id, c.body.as_deref()), (99, Some("current")));
    }

    // frob:tests history_after
    // frob:tests creation_revision
    #[test]
    fn truncation_or_deleted_content_is_a_gap_not_a_failure() {
        let mut f = fake();
        f.bodies.truncated = true;
        let h = history_after(&f, &IssueRef("1".into()), None).unwrap();
        assert_eq!(h.fidelity, Fidelity::Gap);
        assert_eq!(h.entries.len(), 4);
        let c = creation_revision(&f, &IssueRef("1".into()), 99).unwrap();
        assert_eq!(c.fidelity, Fidelity::Gap);

        let mut f = fake();
        f.bodies.revisions[1].body = None;
        let h = history_after(&f, &IssueRef("1".into()), None).unwrap();
        assert_eq!(h.fidelity, Fidelity::Gap);
        f.bodies.revisions[0].body = None;
        let c = creation_revision(&f, &IssueRef("1".into()), 99).unwrap();
        assert_eq!((c.body, c.fidelity), (None, Fidelity::Gap));

        let h = history_after(
            &fake(),
            &IssueRef("1".into()),
            Some(&EventId("gone".into())),
        )
        .unwrap();
        assert_eq!(h.fidelity, Fidelity::Gap);
    }

    // frob:tests read_issue
    #[test]
    fn read_issue_passes_errors_through() {
        let s = read_issue(&fake(), &IssueRef("1".into())).unwrap();
        assert_eq!(s.body, "current");
        assert_eq!(
            read_issue(&Bad, &IssueRef("1".into())),
            Err(AdapterError::Gone)
        );
    }
}
