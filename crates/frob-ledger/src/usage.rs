//! Session token usage: counts-only records a Claude Code hook appends beside the activity journal.
// frob:ticket 01M48Q2CF72NC7WT89VTY17MK7
//!
//! A `Stop` or `PostToolUse` hook (documented in pm-and-releases.md) totals the token counts of
//! its own session and appends one [`UsageRecord`] line per firing to
//! `<git common dir>/frob/activity/<ticket>.usage.jsonl`. Records are cumulative per session, so
//! [`ticket_tokens`] keeps the latest record of each session and sums across sessions. frob never
//! reads a harness transcript: the record type rejects unknown fields, so message content cannot
//! ride along, and only the four counts, a session id and a timestamp are stored.

use std::fs;
use std::io::Write as _;
use std::path::PathBuf;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::activity::{Journal, JournalError};

/// Cumulative token counts of one session at one instant; counts only, never content.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct UsageRecord {
    /// Opaque session identifier supplied by the hook.
    pub session: String,
    /// Unix seconds the hook fired.
    pub at: i64,
    /// Fresh input tokens so far in the session.
    pub input: u64,
    /// Output tokens so far in the session.
    pub output: u64,
    /// Input tokens served from the prompt cache.
    #[serde(default)]
    pub cache_read: u64,
    /// Input tokens written to the prompt cache.
    #[serde(default)]
    pub cache_create: u64,
}

impl UsageRecord {
    /// Every token counted, saturating.
    #[must_use]
    pub const fn total(&self) -> u64 {
        self.input
            .saturating_add(self.output)
            .saturating_add(self.cache_read)
            .saturating_add(self.cache_create)
    }

    /// Parse one hook-emitted JSON line; fails on any field beyond the counts.
    ///
    /// # Errors
    ///
    /// [`JournalError::Encode`] when the line is not a valid counts-only record.
    pub fn from_json(line: &str) -> Result<Self, JournalError> {
        Ok(serde_json::from_str(line)?)
    }
}

impl Journal {
    fn usage_path(&self, ticket: &str) -> PathBuf {
        self.dir().join(format!("{ticket}.usage.jsonl"))
    }

    /// Append `record` to `ticket`'s usage journal, creating it on first use.
    ///
    /// # Errors
    ///
    /// [`JournalError`] on encoding or I/O failure.
    pub fn record_usage(&self, ticket: &str, record: &UsageRecord) -> Result<(), JournalError> {
        let path = self.usage_path(ticket);
        let io = |source| JournalError::Io {
            path: path.clone(),
            source,
        };
        fs::create_dir_all(self.dir()).map_err(io)?;
        let mut line = serde_json::to_string(record)?;
        line.push('\n');
        let mut f = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&path)
            .map_err(io)?;
        f.write_all(line.as_bytes()).map_err(io)?;
        tracing::debug!(ticket, session = %record.session, total = record.total(), "usage recorded");
        Ok(())
    }

    /// Every usage record for `ticket`, oldest first; unreadable lines are skipped with a warning.
    ///
    /// # Errors
    ///
    /// [`JournalError::Io`] when the file exists but cannot be read; a missing file is empty.
    pub fn read_usage(&self, ticket: &str) -> Result<Vec<UsageRecord>, JournalError> {
        let path = self.usage_path(ticket);
        let text = match fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(source) => return Err(JournalError::Io { path, source }),
        };
        Ok(text
            .lines()
            .filter(|l| !l.trim().is_empty())
            .filter_map(|l| match UsageRecord::from_json(l) {
                Ok(r) => Some(r),
                Err(e) => {
                    tracing::warn!(ticket, error = %e, "skipping unreadable usage journal line");
                    None
                }
            })
            .collect())
    }

    /// Total tokens `ticket` spent per the usage journal; `None` when nothing was recorded.
    ///
    /// # Errors
    ///
    /// [`JournalError`] when the journal cannot be read.
    pub fn usage_tokens(&self, ticket: &str) -> Result<Option<u64>, JournalError> {
        Ok(ticket_tokens(&self.read_usage(ticket)?))
    }
}

/// Total tokens over `records`: the latest record of each session, summed; `None` when empty.
#[must_use]
pub fn ticket_tokens(records: &[UsageRecord]) -> Option<u64> {
    let mut latest: std::collections::BTreeMap<&str, &UsageRecord> =
        std::collections::BTreeMap::new();
    for r in records {
        match latest.get(r.session.as_str()) {
            Some(prev) if prev.at > r.at => {}
            _ => {
                latest.insert(r.session.as_str(), r);
            }
        }
    }
    latest
        .values()
        .map(|r| r.total())
        .reduce(u64::saturating_add)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rec(session: &str, at: i64, input: u64, output: u64) -> UsageRecord {
        UsageRecord {
            session: session.to_owned(),
            at,
            input,
            output,
            cache_read: 0,
            cache_create: 0,
        }
    }

    // frob:tests crates/frob-ledger/src/usage.rs::Journal.record_usage
    // frob:tests crates/frob-ledger/src/usage.rs::Journal.read_usage
    // frob:tests crates/frob-ledger/src/usage.rs::Journal.usage_tokens
    // frob:tests crates/frob-ledger/src/usage.rs::UsageRecord.from_json
    #[test]
    fn hook_lines_land_in_the_journal_as_counts() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let j = Journal::in_common_dir(tmp.path());
        let hook_lines = [
            r#"{"session":"s1","at":10,"input":100,"output":50,"cache_read":1000}"#,
            r#"{"session":"s1","at":20,"input":150,"output":80,"cache_read":1200,"cache_create":5}"#,
            r#"{"session":"s2","at":15,"input":10,"output":5}"#,
        ];
        for l in hook_lines {
            j.record_usage("T1", &UsageRecord::from_json(l).expect("parse"))
                .expect("record");
        }
        let got = j.read_usage("T1").expect("read");
        assert_eq!(got.len(), 3);
        assert_eq!(got[1].cache_create, 5);
        // latest of s1 (150+80+1200+5) plus s2 (15)
        assert_eq!(j.usage_tokens("T1").expect("tokens"), Some(1435 + 15));
        assert_eq!(j.usage_tokens("other").expect("tokens"), None);
    }

    // frob:tests crates/frob-ledger/src/usage.rs::ticket_tokens
    // frob:tests crates/frob-ledger/src/usage.rs::UsageRecord.total
    #[test]
    fn totals_use_latest_per_session_and_none_when_empty() {
        assert_eq!(ticket_tokens(&[]), None);
        let rs = [rec("a", 5, 10, 1), rec("a", 9, 20, 2), rec("a", 7, 99, 99)];
        assert_eq!(ticket_tokens(&rs), Some(22));
        assert_eq!(rec("a", 0, u64::MAX, 5).total(), u64::MAX);
    }

    // frob:tests crates/frob-ledger/src/usage.rs::UsageRecord.from_json
    #[test]
    fn content_bearing_fields_are_rejected() {
        let bad = r#"{"session":"s","at":1,"input":1,"output":1,"text":"secret"}"#;
        assert!(UsageRecord::from_json(bad).is_err());
    }
}
