//! Write journal and own-write attribution (mirror.md 3.3 "Own writes", 3.5 journal).
//!
//! Before each mutation the run journals (issue, field, value digest, run id). A history
//! entry is own only when its actor is a bot id and its digest matches a journaled write;
//! any other bot entry is an edit by unknown automation. Unconfirmed entries are re-read
//! at the start of the next run and confirmed or marked lost.

// frob:ticket 01M4052RMBKXD6T8ANNFWJ751M

use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

use crate::adapter::{AdapterError, HistoryEntry, IssueRef};
use crate::mapfile::{MapError, ShardStore, content_hash, decode, encode};

/// Where a journaled write stands.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum WriteStatus {
    /// Journaled; the tracker has not been read back yet.
    Unconfirmed,
    /// A read-back showed the written value.
    Confirmed,
    /// A read-back showed a different value: the write did not land.
    Lost,
}

/// One journaled mutation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct JournalEntry {
    /// The issue written.
    pub issue: IssueRef,
    /// The field written.
    pub field: String,
    /// Digest of the value written.
    pub value_digest: String,
    /// The run that wrote it.
    pub run_id: String,
    /// When it was journaled (RFC 3339).
    pub time: String,
    /// Confirmation state.
    pub status: WriteStatus,
}

/// Who a history entry is attributed to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Attribution {
    /// A bot id whose digest matches a journaled write.
    Own,
    /// A bot id with no matching journaled write.
    UnknownAutomation,
    /// Not a bot id.
    Other,
}

/// What start-of-run recovery decided.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct RecoveryReport {
    /// Entries a read-back confirmed.
    pub confirmed: usize,
    /// Entries a read-back showed did not land.
    pub lost: usize,
    /// Entries whose read-back failed; still unconfirmed.
    pub unread: usize,
}

/// A ticket's write journal.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Journal {
    /// Entries in journaling order.
    pub entries: Vec<JournalEntry>,
}

/// Digest of a field value as journaled and as compared against history entries.
pub fn value_digest(value: &str) -> String {
    blake3::hash(value.as_bytes()).to_hex().to_string()
}

/// Store key of the journal for ticket `ulid`.
pub fn journal_key(ulid: &str) -> String {
    format!("journal-{ulid}")
}

/// Reads the journal for `ulid`; a missing journal is empty.
///
/// # Errors
/// `MapError::Corrupt` when the stored journal does not decode.
pub fn read_journal<S: ShardStore>(store: &S, ulid: &str) -> Result<Journal, MapError> {
    let key = journal_key(ulid);
    match store.get(&key) {
        None => Ok(Journal::default()),
        Some(bytes) => decode(&key, &bytes),
    }
}

/// Commits the journal for `ulid` through CAS against what is stored.
///
/// # Errors
/// `MapError::Conflict` when another writer changed the journal first.
pub fn write_journal<S: ShardStore>(
    store: &mut S,
    ulid: &str,
    journal: &Journal,
) -> Result<(), MapError> {
    let key = journal_key(ulid);
    let expected = store.get(&key).map(|b| content_hash(&b));
    store.put_if(&key, expected.as_deref(), encode(journal))
}

/// Journals `entry` durably, then runs `send`; the mutation is never sent unjournaled.
///
/// # Errors
/// `MapError` when the journal cannot be read or committed; `send` is then not called.
pub fn journaled_write<S: ShardStore, R>(
    store: &mut S,
    ulid: &str,
    entry: JournalEntry,
    send: impl FnOnce() -> R,
) -> Result<R, MapError> {
    let mut journal = read_journal(store, ulid)?;
    debug!(issue = %entry.issue.0, field = %entry.field, run = %entry.run_id, "journaling write");
    journal.entries.push(entry);
    write_journal(store, ulid, &journal)?;
    Ok(send())
}

impl Journal {
    /// Attributes a history entry on `issue`: own only for a bot id with a matching write.
    pub fn classify(&self, bot_ids: &[u64], issue: &IssueRef, entry: &HistoryEntry) -> Attribution {
        if !bot_ids.contains(&entry.actor_id) {
            return Attribution::Other;
        }
        let matched = self.entries.iter().any(|j| {
            j.issue == *issue && j.field == entry.field && j.value_digest == entry.value_digest
        });
        if matched {
            Attribution::Own
        } else {
            warn!(issue = %issue.0, field = %entry.field, actor = entry.actor_id,
                "edit by unknown automation");
            Attribution::UnknownAutomation
        }
    }

    /// Re-reads every unconfirmed entry via `read_back` (current value digest of the field)
    /// and confirms or marks each lost; a failed read leaves the entry unconfirmed.
    pub fn recover(
        &mut self,
        mut read_back: impl FnMut(&IssueRef, &str) -> Result<String, AdapterError>,
    ) -> RecoveryReport {
        let mut report = RecoveryReport::default();
        for e in &mut self.entries {
            if e.status != WriteStatus::Unconfirmed {
                continue;
            }
            match read_back(&e.issue, &e.field) {
                Ok(d) if d == e.value_digest => {
                    e.status = WriteStatus::Confirmed;
                    report.confirmed += 1;
                }
                Ok(_) => {
                    e.status = WriteStatus::Lost;
                    report.lost += 1;
                }
                Err(err) => {
                    warn!(issue = %e.issue.0, field = %e.field, error = %err, "journal read-back failed");
                    report.unread += 1;
                }
            }
        }
        info!(
            confirmed = report.confirmed,
            lost = report.lost,
            unread = report.unread,
            "journal recovery done"
        );
        report
    }
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;
    use std::collections::HashMap;
    use std::rc::Rc;

    use super::*;
    use crate::adapter::EventId;

    fn entry(field: &str, value: &str) -> JournalEntry {
        JournalEntry {
            issue: IssueRef("7".into()),
            field: field.into(),
            value_digest: value_digest(value),
            run_id: "r1".into(),
            time: "2026-10-19T00:00:00Z".into(),
            status: WriteStatus::Unconfirmed,
        }
    }

    fn hist(actor: u64, field: &str, value: &str) -> HistoryEntry {
        HistoryEntry {
            event: EventId("e1".into()),
            actor_id: actor,
            field: field.into(),
            value_digest: value_digest(value),
        }
    }

    // frob:tests journaled_write
    // frob:tests read_journal
    #[test]
    fn journal_is_durable_before_the_call_is_made() {
        #[derive(Clone, Default)]
        struct Shared(Rc<RefCell<HashMap<String, Vec<u8>>>>);
        impl ShardStore for Shared {
            fn get(&self, key: &str) -> Option<Vec<u8>> {
                self.0.borrow().get(key).cloned()
            }
            fn put_if(
                &mut self,
                key: &str,
                _: Option<&str>,
                bytes: Vec<u8>,
            ) -> Result<(), MapError> {
                self.0.borrow_mut().insert(key.into(), bytes);
                Ok(())
            }
        }
        let mut store = Shared::default();
        let view = store.clone();
        // At send time the entry must already be readable from the store.
        let at_send = journaled_write(&mut store, "T1", entry("title", "hello"), || {
            read_journal(&view, "T1").unwrap()
        })
        .unwrap();
        assert_eq!(at_send.entries.len(), 1);
        assert_eq!(at_send.entries[0].value_digest, value_digest("hello"));
        assert_eq!(at_send.entries[0].run_id, "r1");
        assert_eq!(at_send.entries[0].issue, IssueRef("7".into()));
        assert_eq!(at_send.entries[0].field, "title");
        assert_eq!(at_send.entries[0].status, WriteStatus::Unconfirmed);
    }

    // frob:tests journaled_write
    #[test]
    fn send_is_not_called_when_the_journal_cannot_be_committed() {
        struct Broken;
        impl ShardStore for Broken {
            fn get(&self, _: &str) -> Option<Vec<u8>> {
                None
            }
            fn put_if(&mut self, key: &str, _: Option<&str>, _: Vec<u8>) -> Result<(), MapError> {
                Err(MapError::Conflict {
                    key: key.into(),
                    expected: None,
                    found: Some("x".into()),
                })
            }
        }
        let mut called = false;
        let r = journaled_write(&mut Broken, "T1", entry("title", "a"), || called = true);
        assert!(r.is_err());
        assert!(!called);
    }

    // frob:tests classify
    #[test]
    fn bot_entry_is_own_only_with_matching_digest() {
        let j = Journal {
            entries: vec![entry("title", "hello")],
        };
        let issue = IssueRef("7".into());
        let bots = [99];
        assert_eq!(
            j.classify(&bots, &issue, &hist(99, "title", "hello")),
            Attribution::Own
        );
        assert_eq!(
            j.classify(&bots, &issue, &hist(99, "title", "other")),
            Attribution::UnknownAutomation
        );
        assert_eq!(
            j.classify(&bots, &issue, &hist(5, "title", "hello")),
            Attribution::Other
        );
    }

    // frob:tests recover
    #[test]
    fn unconfirmed_entries_are_confirmed_or_lost_at_run_start() {
        let mut j = Journal {
            entries: vec![entry("title", "a"), entry("body", "b"), entry("state", "c")],
        };
        let r = j.recover(|_, field| match field {
            "title" => Ok(value_digest("a")),
            "body" => Ok(value_digest("zzz")),
            _ => Err(AdapterError::Other("down".into())),
        });
        assert_eq!(
            r,
            RecoveryReport {
                confirmed: 1,
                lost: 1,
                unread: 1
            }
        );
        assert_eq!(j.entries[0].status, WriteStatus::Confirmed);
        assert_eq!(j.entries[1].status, WriteStatus::Lost);
        assert_eq!(j.entries[2].status, WriteStatus::Unconfirmed);
        // A second pass reads only the still-unconfirmed entry.
        let mut reads = 0;
        j.recover(|_, _| {
            reads += 1;
            Ok(value_digest("c"))
        });
        assert_eq!(reads, 1);
    }
}
