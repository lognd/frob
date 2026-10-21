//! Outbox (mirror.md 3.2 work class 2, 3.4): ledger events become idempotent set-field operations.
//!
//! Each unpublished ledger event is an operation keyed by ticket ULID plus event ULID. An
//! operation sets one field to one value, so a replay or a late duplicate is harmless, and one
//! whose value already equals the tracker's normalized observed value is skipped without a
//! request. Failures retry next run; incremental mode looks only past each shard's `last_event`,
//! full-resync mode diffs every ticket's latest values within the budget, resuming round-robin.

// frob:ticket 01M3ZX841SP0ZXM4CT18A4B8CV

use std::collections::{BTreeMap, BTreeSet};

use thiserror::Error;
use tracing::{debug, info, trace, warn};

use crate::mapfile::{MapError, Shard, ShardStore, read_shard};
use crate::progress::{ProgressWriter, StopReason};

/// One ledger event that sets a projected field to a value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LedgerEvent {
    /// Ticket ULID.
    pub ticket: String,
    /// Event ULID; sorts oldest first.
    pub event: String,
    /// Projected field name.
    pub field: String,
    /// The value the field takes.
    pub value: String,
}

impl LedgerEvent {
    /// The idempotency key: ticket ULID plus event ULID.
    pub fn key(&self) -> String {
        format!("{}:{}", self.ticket, self.event)
    }
}

/// Whether a run looks only at unpublished events or re-diffs everything.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Only events after each shard's `last_event`.
    Incremental,
    /// Every ticket's latest value per field, resuming after the round-robin cursor.
    FullResync,
}

/// Failures a sink reports for one set-field call.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum SinkError {
    /// The tracker throttled; the run stops and commits its progress.
    #[error("rate limited (reset {reset:?})")]
    RateLimited {
        /// Unix time the window resets, when known.
        reset: Option<u64>,
    },
    /// Any other failure; the ticket's remaining operations wait for the next run.
    #[error("tracker error: {0}")]
    Other(String),
}

/// The mutating side of a tracker: set one field of one issue to a value.
pub trait FieldSink {
    /// Set `field` of issue `number` to `value`, returning the tracker's normalized value.
    ///
    /// # Errors
    /// Returns a [`SinkError`] when the tracker call fails.
    fn set_field(&mut self, number: u64, field: &str, value: &str) -> Result<String, SinkError>;
}

/// Errors that abort an outbox run.
#[derive(Debug, Error)]
pub enum OutboxError {
    /// The map store failed.
    #[error(transparent)]
    Map(#[from] MapError),
}

/// What one outbox run did.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct OutboxReport {
    /// Operations sent to the tracker.
    pub applied: u64,
    /// Operations skipped because the tracker already held the value.
    pub skipped: u64,
    /// Operations that failed and will retry next run.
    pub failed: u64,
    /// Operations left because the ticket has no issue yet (the create class owns it).
    pub deferred: u64,
    /// Why the run stopped early, if it did.
    pub stop: Option<StopReason>,
}

/// Load the shards of `tickets` from `store` (absent ones are omitted).
///
/// # Errors
/// Returns a [`MapError`] when a shard is corrupt.
pub fn load_shards<S: ShardStore>(
    store: &S,
    tickets: &BTreeSet<String>,
) -> Result<BTreeMap<String, Shard>, MapError> {
    let mut out = BTreeMap::new();
    for t in tickets {
        if let Some(s) = read_shard(store, t)? {
            out.insert(t.clone(), s);
        }
    }
    Ok(out)
}

/// Choose the operations of a run: oldest first, at most `max_ops`.
///
/// Incremental keeps events past the shard's `last_event`. Full resync keeps the latest event
/// per ticket and field, with tickets rotated to start after `resume_after`.
pub fn plan_ops(
    events: &[LedgerEvent],
    shards: &BTreeMap<String, Shard>,
    mode: Mode,
    resume_after: Option<&str>,
    max_ops: usize,
) -> Vec<LedgerEvent> {
    let mut ops: Vec<LedgerEvent> = match mode {
        Mode::Incremental => events
            .iter()
            .filter(|e| {
                shards
                    .get(&e.ticket)
                    .and_then(|s| s.last_event.as_deref())
                    .is_none_or(|last| e.event.as_str() > last)
            })
            .cloned()
            .collect(),
        Mode::FullResync => {
            let mut latest: BTreeMap<(&str, &str), &LedgerEvent> = BTreeMap::new();
            for e in events {
                let slot = latest.entry((&e.ticket, &e.field)).or_insert(e);
                if e.event > slot.event {
                    *slot = e;
                }
            }
            latest.into_values().cloned().collect()
        }
    };
    match mode {
        Mode::Incremental => ops.sort_by(|a, b| (&a.event, &a.ticket).cmp(&(&b.event, &b.ticket))),
        Mode::FullResync => {
            ops.sort_by(|a, b| (&a.ticket, &a.event).cmp(&(&b.ticket, &b.event)));
            if let Some(after) = resume_after {
                let start = ops
                    .iter()
                    .position(|o| o.ticket.as_str() > after)
                    .unwrap_or(0);
                ops.rotate_left(start);
            }
        }
    }
    ops.truncate(max_ops);
    debug!(?mode, planned = ops.len(), "outbox: operations planned");
    ops
}

/// Execute `ops` through `sink`, recording each ticket's shard as it completes.
///
/// Per op: a ticket without an issue is deferred; a value equal to the shard's observed value
/// is skipped with no request; otherwise the sink is called and the normalized value stored.
/// A sink failure holds back that ticket's later ops; a rate limit stops the run.
///
/// # Errors
/// Returns an [`OutboxError`] when progress cannot be recorded.
pub fn run<S: ShardStore, K: FieldSink>(
    ops: &[LedgerEvent],
    shards: &mut BTreeMap<String, Shard>,
    sink: &mut K,
    writer: &mut ProgressWriter<'_, S>,
) -> Result<OutboxReport, OutboxError> {
    let mut report = OutboxReport::default();
    let mut held: BTreeSet<&str> = BTreeSet::new();
    for op in ops {
        if held.contains(op.ticket.as_str()) {
            trace!(key = %op.key(), "outbox: held behind earlier failure");
            continue;
        }
        let Some(shard) = shards.get_mut(&op.ticket) else {
            report.deferred += 1;
            continue;
        };
        match apply_op(op, shard, sink) {
            OpOutcome::Deferred => report.deferred += 1,
            OpOutcome::Applied => report.applied += 1,
            OpOutcome::Skipped => report.skipped += 1,
            OpOutcome::Failed => {
                report.failed += 1;
                held.insert(&op.ticket);
                continue;
            }
            OpOutcome::RateLimited { reset } => {
                report.stop = Some(StopReason::RateLimited { reset });
                return Ok(report);
            }
        }
        writer.record(shard.clone())?;
    }
    Ok(report)
}

/// What applying one ledger op to its shard did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OpOutcome {
    /// The ticket has no issue yet; nothing was sent and the shard is unchanged.
    Deferred,
    /// The sink wrote the field; the shard holds the normalized value and the new `last_event`.
    Applied,
    /// The shard already observed the value; no request was made, `last_event` advanced.
    Skipped,
    /// The sink failed; the shard is unchanged and the ticket's later ops should wait.
    Failed,
    /// The tracker throttled; the shard is unchanged and the run should stop.
    RateLimited {
        /// Unix time the window resets, when known.
        reset: Option<u64>,
    },
}

// frob:ticket 01M5EA0YFAACDY5BV70R2MH98S
/// Applies one ledger op to `shard` through `sink`, updating observed value and `last_event`.
///
/// The caller records the shard afterwards for `Applied` and `Skipped`.
pub fn apply_op<K: FieldSink>(op: &LedgerEvent, shard: &mut Shard, sink: &mut K) -> OpOutcome {
    let Some(number) = shard.issue_number else {
        debug!(key = %op.key(), "outbox: no issue yet, deferred");
        return OpOutcome::Deferred;
    };
    let outcome = if shard.observed.get(&op.field) == Some(&op.value) {
        trace!(key = %op.key(), "outbox: already at value, skipped");
        OpOutcome::Skipped
    } else {
        match sink.set_field(number, &op.field, &op.value) {
            Ok(normalized) => {
                shard.observed.insert(op.field.clone(), normalized);
                OpOutcome::Applied
            }
            Err(SinkError::RateLimited { reset }) => {
                info!(key = %op.key(), "outbox: rate limited, stopping");
                return OpOutcome::RateLimited { reset };
            }
            Err(e) => {
                warn!(key = %op.key(), error = %e, "outbox: failed, retry next run");
                return OpOutcome::Failed;
            }
        }
    };
    if shard
        .last_event
        .as_deref()
        .is_none_or(|l| op.event.as_str() > l)
    {
        shard.last_event = Some(op.event.clone());
    }
    outcome
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::*;
    use crate::mapfile::content_hash;

    #[derive(Default)]
    struct Mem(HashMap<String, Vec<u8>>);

    impl ShardStore for Mem {
        fn get(&self, key: &str) -> Option<Vec<u8>> {
            self.0.get(key).cloned()
        }
        fn put_if(
            &mut self,
            key: &str,
            expected: Option<&str>,
            bytes: Vec<u8>,
        ) -> Result<(), MapError> {
            let found = self.get(key).map(|b| content_hash(&b));
            if found.as_deref() != expected {
                return Err(MapError::Conflict {
                    key: key.into(),
                    expected: expected.map(String::from),
                    found,
                });
            }
            self.0.insert(key.into(), bytes);
            Ok(())
        }
    }

    /// Records calls; fails with a rate limit once `limit` calls were made.
    struct Sink {
        calls: Vec<String>,
        limit: usize,
    }

    impl FieldSink for Sink {
        fn set_field(&mut self, n: u64, f: &str, v: &str) -> Result<String, SinkError> {
            if self.calls.len() >= self.limit {
                return Err(SinkError::RateLimited { reset: Some(9) });
            }
            self.calls.push(format!("{n}:{f}={v}"));
            Ok(v.to_string())
        }
    }

    fn ev(t: &str, e: &str, f: &str, v: &str) -> LedgerEvent {
        LedgerEvent {
            ticket: t.into(),
            event: e.into(),
            field: f.into(),
            value: v.into(),
        }
    }

    fn seed(store: &mut Mem, tickets: &[&str]) {
        for (i, t) in tickets.iter().enumerate() {
            let mut s = Shard::new(t);
            s.issue_number = Some(i as u64 + 1);
            crate::mapfile::write_shard(store, &s).unwrap();
        }
    }

    fn five() -> Vec<LedgerEvent> {
        (1..=5)
            .map(|i| {
                ev(
                    &format!("T{i}"),
                    &format!("E{i}"),
                    "title",
                    &format!("v{i}"),
                )
            })
            .collect()
    }

    fn pass(
        store: &mut Mem,
        events: &[LedgerEvent],
        mode: Mode,
        limit: usize,
    ) -> (Sink, OutboxReport) {
        let tickets: BTreeSet<String> = events.iter().map(|e| e.ticket.clone()).collect();
        let mut shards = load_shards(store, &tickets).unwrap();
        let mut w = ProgressWriter::new(store, 1).unwrap();
        let ops = plan_ops(events, &shards, mode, w.resume_after(), 100);
        let mut sink = Sink {
            calls: vec![],
            limit,
        };
        let report = run(&ops, &mut shards, &mut sink, &mut w).unwrap();
        w.finish(report.stop.unwrap_or(StopReason::Completed))
            .unwrap();
        (sink, report)
    }

    // frob:tests run
    // frob:tests plan_ops
    #[test]
    fn interrupted_run_resumes_with_only_remaining_ops() {
        let mut store = Mem::default();
        seed(&mut store, &["T1", "T2", "T3", "T4", "T5"]);
        let events = five();
        let (first, r1) = pass(&mut store, &events, Mode::Incremental, 2);
        assert_eq!(first.calls.len(), 2);
        assert!(r1.stop.is_some());
        let (second, r2) = pass(&mut store, &events, Mode::Incremental, 100);
        assert_eq!(second.calls, ["3:title=v3", "4:title=v4", "5:title=v5"]);
        assert_eq!(r2.applied, 3);
    }

    // frob:tests run
    #[test]
    fn no_new_events_makes_no_mutating_request() {
        let mut store = Mem::default();
        seed(&mut store, &["T1", "T2", "T3", "T4", "T5"]);
        let events = five();
        pass(&mut store, &events, Mode::Incremental, 100);
        let (again, r) = pass(&mut store, &events, Mode::Incremental, 100);
        assert!(again.calls.is_empty());
        assert_eq!(r, OutboxReport::default());
    }

    // frob:tests run
    #[test]
    fn value_equal_to_observed_is_skipped() {
        let mut store = Mem::default();
        seed(&mut store, &["T1"]);
        let mut s = read_shard(&store, "T1").unwrap().unwrap();
        s.observed.insert("title".into(), "same".into());
        crate::mapfile::write_shard(&mut store, &s).unwrap();
        let events = vec![ev("T1", "E1", "title", "same")];
        let (sink, r) = pass(&mut store, &events, Mode::Incremental, 100);
        assert!(sink.calls.is_empty());
        assert_eq!(r.skipped, 1);
    }

    // frob:tests plan_ops
    #[test]
    fn full_resync_uses_latest_value_and_resumes_round_robin() {
        let mut store = Mem::default();
        seed(&mut store, &["T1", "T2"]);
        let events = vec![
            ev("T1", "E1", "title", "old"),
            ev("T1", "E3", "title", "new"),
            ev("T2", "E2", "title", "b"),
        ];
        let shards = load_shards(&store, &["T1".to_string(), "T2".to_string()].into()).unwrap();
        let ops = plan_ops(&events, &shards, Mode::FullResync, Some("T1"), 1);
        assert_eq!(ops, [ev("T2", "E2", "title", "b")]);
        let all = plan_ops(&events, &shards, Mode::FullResync, None, 10);
        assert_eq!(all[0], ev("T1", "E3", "title", "new"));
        assert_eq!(all.len(), 2);
    }

    // frob:tests run
    #[test]
    fn ticket_without_issue_is_deferred() {
        let mut store = Mem::default();
        crate::mapfile::write_shard(&mut store, &Shard::new("T1")).unwrap();
        let (sink, r) = pass(
            &mut store,
            &[ev("T1", "E1", "title", "x")],
            Mode::Incremental,
            9,
        );
        assert!(sink.calls.is_empty());
        assert_eq!(r.deferred, 1);
    }
}
