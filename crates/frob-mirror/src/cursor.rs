//! History cursor (mirror.md 3.3 F3, 3.4 F2, MIR-AUD-25): the tracker event id actually read.
//!
//! The cursor is a [`HistoryCursor`], a newtype over a tracker [`EventId`] so a time cannot be
//! stored. A read yields a [`PendingCursor`] (the position read) taken before the ticket's issues
//! are listed; it is held outside the shard, so it survives a create, and only
//! [`PendingCursor::advance`] with a [`Committed`] proof writes it into a shard. A crash before
//! the proposals commit leaves the stored cursor untouched, so the next run re-reads from it.

// frob:ticket 01M4052SQS2X5XYN24DE9ENQF8

use tracing::{debug, info};

use crate::adapter::{AdapterResult, EventId, IssueRef};
use crate::github::read::{HistoryRead, HistorySource, history_after};
use crate::mapfile::Shard;

/// A history position: the id of the last tracker event read. Never a time.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoryCursor(EventId);

impl HistoryCursor {
    /// Wraps a tracker event id as a cursor.
    pub fn from_event(event: EventId) -> Self {
        Self(event)
    }

    /// The event id history is read strictly after.
    pub fn event(&self) -> &EventId {
        &self.0
    }

    /// The cursor stored in `shard`, if any.
    pub fn of_shard(shard: &Shard) -> Option<Self> {
        shard.history_cursor.clone().map(|id| Self(EventId(id)))
    }
}

/// Proof that the proposals a cursor covers are committed; only then may the cursor advance.
#[derive(Debug, Clone, Copy)]
pub struct Committed(());

impl Committed {
    /// Asserts the covered proposals were committed (call after the commit succeeded).
    pub fn confirm() -> Self {
        Self(())
    }
}

/// The position a read reached, not yet durable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PendingCursor(Option<HistoryCursor>);

impl PendingCursor {
    /// A position that saw nothing: for a ticket with no issue yet, so no stored cursor either.
    // frob:ticket 01M5EA0YFAACDY5BV70R2MH98S
    pub fn empty() -> Self {
        Self(None)
    }

    /// The position read, if any history was seen.
    pub fn position(&self) -> Option<&HistoryCursor> {
        self.0.as_ref()
    }

    /// Returns `shard` with the cursor advanced; a read that saw nothing keeps the stored cursor.
    /// All other shard fields (such as a created issue's identity) are preserved.
    pub fn advance(self, mut shard: Shard, _proof: Committed) -> Shard {
        if let Some(c) = self.0 {
            info!(ulid = %shard.ulid, cursor = %c.0.0, "cursor: advanced after commit");
            shard.history_cursor = Some(c.0.0);
        }
        shard
    }
}

/// One ticket's read: the history after the stored cursor and the position it reached.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CursorRead {
    /// History strictly after the stored cursor.
    pub history: HistoryRead,
    /// The position actually read, to advance only after commit.
    pub pending: PendingCursor,
}

/// Reads `issue` history after the shard's stored cursor, before the ticket's issues are listed.
///
/// The pending cursor is the last event actually read, else the stored one. Nothing is written.
///
/// # Errors
/// Returns the source's `AdapterError` when a read fails.
pub fn begin_read(
    source: &dyn HistorySource,
    issue: &IssueRef,
    shard: &Shard,
) -> AdapterResult<CursorRead> {
    let stored = HistoryCursor::of_shard(shard);
    let history = history_after(source, issue, stored.as_ref().map(HistoryCursor::event))?;
    let reached = history
        .entries
        .last()
        .map(|e| HistoryCursor::from_event(e.event.clone()))
        .or(stored);
    debug!(ulid = %shard.ulid, entries = history.entries.len(), "cursor: read");
    Ok(CursorRead {
        history,
        pending: PendingCursor(reached),
    })
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;

    use super::*;
    use crate::adapter::IssueState;
    use crate::github::read::{BodyRevisions, TimelineEvent};
    use crate::mapfile::{MapError, ShardStore, read_shard, write_shard};
    use std::collections::BTreeMap;

    struct Fake(RefCell<Vec<TimelineEvent>>);

    impl Fake {
        fn push(&self, id: &str, at: &str) {
            self.0.borrow_mut().push(TimelineEvent {
                id: id.into(),
                created_at: at.into(),
                actor_id: 1,
                field: "title".into(),
                value: id.into(),
            });
        }
    }

    impl HistorySource for Fake {
        fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
            Ok(IssueState {
                issue: issue.clone(),
                title: String::new(),
                body: String::new(),
                labels: vec![],
                assignees: vec![],
                closed: false,
            })
        }
        fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
            Ok(self.0.borrow().clone())
        }
        fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
            Ok(BodyRevisions::default())
        }
    }

    #[derive(Default)]
    struct Mem(BTreeMap<String, Vec<u8>>);

    impl ShardStore for Mem {
        fn get(&self, key: &str) -> Option<Vec<u8>> {
            self.0.get(key).cloned()
        }
        fn put_if(&mut self, key: &str, _: Option<&str>, bytes: Vec<u8>) -> Result<(), MapError> {
            self.0.insert(key.into(), bytes);
            Ok(())
        }
    }

    fn issue() -> IssueRef {
        IssueRef("7".into())
    }

    #[test]
    fn first_read_cursor_survives_a_create() {
        let src = Fake(RefCell::new(vec![]));
        src.push("e1", "2026-01-01T00:00:00Z");
        src.push("e2", "2026-01-02T00:00:00Z");
        let read = begin_read(&src, &issue(), &Shard::new("U1")).unwrap();
        assert_eq!(read.history.entries.len(), 2);
        // The create fills in identity after the cursor was taken.
        let mut created = Shard::new("U1");
        created.issue_number = Some(7);
        let out = read.pending.advance(created, Committed::confirm());
        assert_eq!(out.issue_number, Some(7));
        assert_eq!(out.history_cursor.as_deref(), Some("e2"));
    }

    #[test]
    fn crash_before_commit_leaves_cursor_and_repeat_reads_the_same() {
        let src = Fake(RefCell::new(vec![]));
        src.push("e1", "2026-01-01T00:00:00Z");
        let mut store = Mem::default();
        let mut shard = Shard::new("U1");
        shard.history_cursor = Some("e0".into());
        write_shard(&mut store, &shard).unwrap();
        // Run 1 reads, then crashes before the commit: pending is dropped, never advanced.
        let first = begin_read(&src, &issue(), &read_shard(&store, "U1").unwrap().unwrap());
        let first = first.unwrap();
        drop(first.pending.clone());
        let stored = read_shard(&store, "U1").unwrap().unwrap();
        assert_eq!(stored.history_cursor.as_deref(), Some("e0"));
        // Repeat sees identical history, so a keyed record cannot be duplicated.
        let again = begin_read(&src, &issue(), &stored).unwrap();
        assert_eq!(again, first);
    }

    #[test]
    fn edit_after_the_cursor_is_read_next_run() {
        let src = Fake(RefCell::new(vec![]));
        src.push("e1", "2026-01-01T00:00:00Z");
        let read = begin_read(&src, &issue(), &Shard::new("U1")).unwrap();
        let shard = read.pending.advance(Shard::new("U1"), Committed::confirm());
        // A human edit lands between the mirror's read and its next run.
        src.push("e2", "2026-01-03T00:00:00Z");
        let next = begin_read(&src, &issue(), &shard).unwrap();
        assert_eq!(next.history.entries.len(), 1);
        assert_eq!(next.history.entries[0].event, EventId("e2".into()));
    }

    #[test]
    fn empty_read_keeps_stored_cursor() {
        let src = Fake(RefCell::new(vec![]));
        let mut shard = Shard::new("U1");
        shard.history_cursor = Some("e9".into());
        let read = begin_read(&src, &issue(), &shard).unwrap();
        // The stored event is absent from history: a gap, everything (nothing) is returned.
        let out = read.pending.advance(shard, Committed::confirm());
        assert_eq!(out.history_cursor.as_deref(), Some("e9"));
    }
}
