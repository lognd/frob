//! Read-back normalization (mirror.md 3.4, MIR-AUD-20): compare after the tracker's own formatting.
//!
//! After a write the mirror reads the field back once and stores what the tracker holds
//! ([`ReadBack`], kept in the shard). Later runs compare the tracker's current value with that
//! stored read-back, so a body the tracker reformats on write is not rewritten forever. A ledger
//! change makes the stored read-back stale, so the next publish reads it back and stores it again.
//! A write whose read-back still shows the old value is reported as MIR001 `write-not-sticking`.

// frob:ticket 01M4052SKTA49WCV6AXJFCAM9J

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, info, warn};

/// The tracker-independent part of normalization: LF line endings, no trailing blanks.
pub fn normalize(value: &str) -> String {
    let unified = value.replace("\r\n", "\n").replace('\r', "\n");
    let lines: Vec<&str> = unified.split('\n').map(str::trim_end).collect();
    lines.join("\n").trim_end_matches('\n').to_string()
}

/// What to do about one field this run.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    /// The tracker already holds the (normalized) projection; write nothing.
    Skip,
    /// The tracker differs from the projection; write, then read back and record.
    Write,
}

/// Why a read-back could not be recorded.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum NormalizeError {
    /// The tracker still holds the pre-write value after the write.
    #[error("MIR001 write-not-sticking: `{field}` still holds its old value after the write")]
    WriteNotSticking {
        /// The field that did not change.
        field: String,
    },
}

/// What the tracker held after the last write of one field.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct Stored {
    /// Normalized ledger value that was published.
    published: String,
    /// Normalized value read back from the tracker after that write.
    observed: String,
}

/// Per-field read-back record, persisted in the ticket's shard.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReadBack {
    fields: BTreeMap<String, Stored>,
}

impl ReadBack {
    /// An empty record: nothing has been read back yet.
    pub fn new() -> Self {
        Self::default()
    }

    /// Decides whether `field` needs a write given the ledger value and the tracker's current one.
    pub fn plan(&self, field: &str, ledger: &str, tracker_now: &str) -> Action {
        let ledger = normalize(ledger);
        let now = normalize(tracker_now);
        let target = match self.fields.get(field) {
            Some(s) if s.published == ledger => s.observed.as_str(),
            _ => ledger.as_str(),
        };
        if now == target {
            debug!(field, "tracker value matches after normalization; no write");
            Action::Skip
        } else {
            debug!(field, "tracker value differs; write needed");
            Action::Write
        }
    }

    /// Records the one read-back after publishing `ledger`; `before` is the pre-write tracker value.
    ///
    /// # Errors
    /// [`NormalizeError::WriteNotSticking`] when the read-back still shows the pre-write value.
    pub fn record(
        &mut self,
        field: &str,
        ledger: &str,
        before: &str,
        read_back: &str,
    ) -> Result<(), NormalizeError> {
        let ledger = normalize(ledger);
        let observed = normalize(read_back);
        if observed == normalize(before) && observed != ledger {
            warn!(field, "MIR001 write-not-sticking");
            return Err(NormalizeError::WriteNotSticking {
                field: field.to_string(),
            });
        }
        info!(field, reformatted = observed != ledger, "read-back stored");
        self.fields.insert(
            field.to_string(),
            Stored {
                published: ledger,
                observed,
            },
        );
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reformatted_body_is_read_back_once_then_left_alone() {
        let mut rb = ReadBack::new();
        let ledger = "line one  \nline two\n";
        assert_eq!(rb.plan("body", ledger, "old"), Action::Write);
        // The tracker rewrites the body (CRLF, extra footer).
        let stored = "line one\r\nline two\r\n<!-- footer -->";
        rb.record("body", ledger, "old", stored).unwrap();
        assert_eq!(rb.plan("body", ledger, stored), Action::Skip);
        assert_eq!(rb.plan("body", ledger, stored), Action::Skip);
    }

    #[test]
    fn ledger_change_reads_back_again() {
        let mut rb = ReadBack::new();
        rb.record("body", "a", "x", "a!").unwrap();
        assert_eq!(rb.plan("body", "b", "a!"), Action::Write);
        rb.record("body", "b", "a!", "b!").unwrap();
        assert_eq!(rb.plan("body", "b", "b!"), Action::Skip);
        assert_eq!(rb.plan("body", "a", "b!"), Action::Write);
    }

    #[test]
    fn write_that_does_not_stick_is_mir001() {
        let mut rb = ReadBack::new();
        let e = rb.record("body", "new", "old", "old\n").unwrap_err();
        assert!(e.to_string().contains("MIR001 write-not-sticking"));
        assert_eq!(rb.plan("body", "new", "old"), Action::Write);
    }

    #[test]
    fn record_round_trips_through_json() {
        let mut rb = ReadBack::new();
        rb.record("body", "a", "x", "a!").unwrap();
        let back: ReadBack = serde_json::from_str(&serde_json::to_string(&rb).unwrap()).unwrap();
        assert_eq!(back, rb);
    }
}
