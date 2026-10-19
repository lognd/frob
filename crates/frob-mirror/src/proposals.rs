//! Recording proposals by reference (mirror.md 3.5, F9): tracker edits become ledger proposals.
//!
//! A proposal stores the tracker item, field, actor id, time, a digest of the full value and a
//! capped, escaped excerpt (origin `tracker`); the full value is fetched at accept time. Each is
//! keyed by the tracker's event id, so reading an edit twice after a crash records it once and a
//! closed proposal never returns. A later edit by the same actor to the same field is recorded as
//! `proposal-superseded`. Caps: one new proposal per (issue, field) per day and `per_run` per run;
//! an edit held back by a cap keeps the cursor before it so a later run records it. Everything a
//! run records goes to the ledger in one [`ProposalSink::commit`] call.

// frob:ticket 01M4052T420AX728KKZ2RDYSTX

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::event::{Event, EventBody, ProposalData};
use frob_ledger::proposal::fold_proposals;
use gob_diagnostics::{TextOrigin, escape_for_origin};
use gob_time::Stamp;
use tracing::{debug, info};

use crate::adapter::EventId;
use crate::cursor::Committed;
use crate::journal::value_digest;

/// Characters of an edited value kept as the excerpt.
pub const EXCERPT_CHARS: usize = 200;

/// Seconds in a UTC day, the unit of the per-(issue, field) cap.
const DAY_SECS: i64 = 86_400;

/// One tracker edit read from history, with its full new value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edit {
    /// The tracker's event id: the proposal's idempotency key.
    pub tracker_event: EventId,
    /// The tracker item (issue) id.
    pub item: String,
    /// The ticket field the edit touches.
    pub field: String,
    /// Tracker user id of the editor (never the login).
    pub actor_id: String,
    /// When the editor made the edit.
    pub time: Stamp,
    /// The full new value; only a digest and an excerpt are recorded.
    pub value: String,
}

/// Where a run's events are written, in one ledger commit.
pub trait ProposalSink {
    /// The sink's failure type.
    type Error;

    /// Commits all of a run's events together.
    ///
    /// # Errors
    /// Returns the sink's error when the commit fails; nothing is then considered recorded.
    fn commit(&mut self, events: Vec<Event>) -> Result<(), Self::Error>;
}

/// What a run recorded and how far the history cursor may move.
#[derive(Debug, Clone)]
pub struct Recorded {
    /// Proposals appended (new and superseding) in the single commit.
    pub appended: usize,
    /// Edits already in the ledger, or older than a recorded proposal, and so skipped.
    pub skipped: usize,
    /// Edits held back by a cap; they stay after the cursor.
    pub deferred: usize,
    /// The last tracker event the cursor may advance to; `None` keeps the stored cursor.
    pub advance_to: Option<EventId>,
    /// Proof the covered proposals are committed (`None` when nothing was committed).
    pub committed: Option<Committed>,
}

/// The capped, escaped excerpt of `value` with origin `tracker`.
pub fn excerpt(value: &str) -> String {
    let capped: String = value.chars().take(EXCERPT_CHARS).collect();
    escape_for_origin(&capped, &TextOrigin::Tracker).into_owned()
}

/// A prior proposal for one (item, field) as the caps and supersede need it.
struct Prior {
    key: String,
    actor_id: String,
    edit_secs: i64,
    recorded_day: i64,
}

fn day_of(secs: i64) -> i64 {
    secs.div_euclid(DAY_SECS)
}

/// Prior proposals by (item, field) and every key ever recorded, from the ledger events.
fn index(events: &[Event]) -> (BTreeSet<String>, BTreeMap<(String, String), Prior>) {
    let keys = fold_proposals(events)
        .into_iter()
        .map(|p| p.data.tracker_event)
        .collect();
    let mut prior: BTreeMap<(String, String), Prior> = BTreeMap::new();
    let mut ordered: Vec<&Event> = events.iter().collect();
    ordered.sort_by_key(|e| e.order_key());
    for ev in ordered {
        if let EventBody::Proposal(d) | EventBody::ProposalSuperseded(d) = &ev.body {
            prior.insert(
                (d.item.clone(), d.field.clone()),
                Prior {
                    key: d.tracker_event.clone(),
                    actor_id: d.actor_id.clone(),
                    edit_secs: d.time.unix(),
                    recorded_day: day_of(ev.at.unix()),
                },
            );
        }
    }
    (keys, prior)
}

/// Records `edits` (oldest first) as proposals, committing all of them in one sink call.
///
/// `existing` is the ticket's ledger events; `now` stamps the events and sets the day for the
/// per-(issue, field) cap; `per_run` is P. Several edits of one field in a run collapse to the
/// latest. A cap-held edit stops `advance_to` before it; the read-time value is never lost.
///
/// # Errors
/// Returns the sink's error when the single commit fails.
pub fn record<S: ProposalSink>(
    sink: &mut S,
    existing: &[Event],
    edits: &[Edit],
    actor: &str,
    now: Stamp,
    per_run: usize,
) -> Result<Recorded, S::Error> {
    let (mut keys, mut prior) = index(existing);
    let today = day_of(now.unix());
    let mut last_of: BTreeMap<(&str, &str), usize> = BTreeMap::new();
    for (i, e) in edits.iter().enumerate() {
        last_of.insert((e.item.as_str(), e.field.as_str()), i);
    }
    let mut events: Vec<Event> = Vec::new();
    let (mut skipped, mut deferred) = (0usize, 0usize);
    let mut first_deferred: Option<usize> = None;
    let mut capped_fields: BTreeSet<(&str, &str)> = BTreeSet::new();
    for (i, e) in edits.iter().enumerate() {
        let field_key = (e.item.as_str(), e.field.as_str());
        let owned = (e.item.clone(), e.field.clone());
        if keys.contains(&e.tracker_event.0) {
            debug!(key = %e.tracker_event.0, "proposal: already recorded, skipped");
            skipped += 1;
            continue;
        }
        if prior
            .get(&owned)
            .is_some_and(|p| e.time.unix() <= p.edit_secs)
        {
            debug!(key = %e.tracker_event.0, "proposal: older than a recorded one, skipped");
            skipped += 1;
            continue;
        }
        if last_of.get(&field_key) != Some(&i) {
            debug!(key = %e.tracker_event.0, "proposal: collapsed into the latest edit of the field");
            continue;
        }
        let held = events.len() >= per_run
            || capped_fields.contains(&field_key)
            || prior.get(&owned).is_some_and(|p| p.recorded_day == today);
        if held {
            info!(key = %e.tracker_event.0, "proposal: held back by a cap");
            deferred += 1;
            first_deferred.get_or_insert(i);
            continue;
        }
        let supersedes = prior
            .get(&owned)
            .filter(|p| p.actor_id == e.actor_id)
            .map(|p| p.key.clone());
        let data = ProposalData {
            tracker_event: e.tracker_event.0.clone(),
            item: e.item.clone(),
            field: e.field.clone(),
            actor_id: e.actor_id.clone(),
            time: e.time,
            digest: value_digest(&e.value),
            excerpt: excerpt(&e.value),
            origin: "tracker".to_owned(),
            supersedes: supersedes.clone(),
        };
        let body = if supersedes.is_some() {
            EventBody::ProposalSuperseded(data)
        } else {
            EventBody::Proposal(data)
        };
        info!(key = %e.tracker_event.0, field = %e.field, superseding = supersedes.is_some(), "proposal: recording");
        events.push(Event::new(now, actor, body));
        keys.insert(e.tracker_event.0.clone());
        capped_fields.insert(field_key);
        prior.insert(
            owned,
            Prior {
                key: e.tracker_event.0.clone(),
                actor_id: e.actor_id.clone(),
                edit_secs: e.time.unix(),
                recorded_day: today,
            },
        );
    }
    let appended = events.len();
    let committed = if events.is_empty() {
        None
    } else {
        sink.commit(events)?;
        info!(appended, "proposal: one ledger commit");
        Some(Committed::confirm())
    };
    let advance_to = match first_deferred {
        Some(0) => None,
        Some(i) => Some(edits[i - 1].tracker_event.clone()),
        None => edits.last().map(|e| e.tracker_event.clone()),
    };
    Ok(Recorded {
        appended,
        skipped,
        deferred,
        advance_to,
        committed,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::convert::Infallible;

    #[derive(Default)]
    struct Mem {
        commits: Vec<Vec<Event>>,
    }

    impl ProposalSink for Mem {
        type Error = Infallible;
        fn commit(&mut self, events: Vec<Event>) -> Result<(), Infallible> {
            self.commits.push(events);
            Ok(())
        }
    }

    impl Mem {
        fn all(&self) -> Vec<Event> {
            self.commits.iter().flatten().cloned().collect()
        }
    }

    const DAY1: i64 = 1_800_000_000;

    fn edit(key: &str, field: &str, actor: &str, secs: i64, value: &str) -> Edit {
        Edit {
            tracker_event: EventId(key.into()),
            item: "I_1".into(),
            field: field.into(),
            actor_id: actor.into(),
            time: Stamp::from_unix(secs),
            value: value.into(),
        }
    }

    fn run(sink: &mut Mem, edits: &[Edit], now: i64, p: usize) -> Recorded {
        let existing = sink.all();
        record(sink, &existing, edits, "mirror", Stamp::from_unix(now), p).unwrap()
    }

    // frob:tests crates/frob-mirror/src/proposals.rs::record
    #[test]
    fn an_edit_read_twice_is_recorded_once_and_a_closed_one_never_returns() {
        let mut sink = Mem::default();
        let e = [edit("t1", "title", "42", DAY1, "new")];
        let first = run(&mut sink, &e, DAY1 + 10, 10);
        assert_eq!((first.appended, first.skipped), (1, 0));
        let again = run(&mut sink, &e, DAY1 + 20, 10);
        assert_eq!((again.appended, again.skipped), (0, 1));
        assert!(again.committed.is_none());
        assert_eq!(sink.commits.len(), 1);
        // Declined, then read again: still not back.
        let close = frob_ledger::event::ProposalCloseData {
            tracker_event: "t1".into(),
            reason: None,
        };
        sink.commits.push(vec![Event::new(
            Stamp::from_unix(DAY1 + 30),
            "a",
            EventBody::ProposalDeclined(close),
        )]);
        let third = run(&mut sink, &e, DAY1 + 40, 10);
        assert_eq!(third.appended, 0);
        assert!(frob_ledger::proposal::pending(&sink.all()).is_empty());
    }

    // frob:tests crates/frob-mirror/src/proposals.rs::excerpt
    #[test]
    fn a_long_value_keeps_a_200_char_escaped_excerpt_and_a_full_digest() {
        let value = "a".repeat(5000);
        let mut sink = Mem::default();
        run(
            &mut sink,
            &[edit("t1", "body", "42", DAY1, &value)],
            DAY1,
            10,
        );
        let EventBody::Proposal(d) = &sink.all()[0].body else {
            panic!("expected a proposal");
        };
        assert_eq!(d.excerpt.chars().count(), 200);
        assert_eq!(d.origin, "tracker");
        assert_eq!(d.digest, value_digest(&value));
        assert_ne!(d.digest, value_digest(&value[..200]));
        assert_eq!(excerpt("a\u{202e}b\nc"), "a\\u{202e}b\nc");
    }

    // frob:tests crates/frob-mirror/src/proposals.rs::record
    #[test]
    fn a_second_edit_by_the_same_actor_appends_a_superseding_event() {
        let mut sink = Mem::default();
        run(
            &mut sink,
            &[edit("t1", "title", "42", DAY1, "one")],
            DAY1,
            10,
        );
        let next_day = DAY1 + DAY_SECS;
        let out = run(
            &mut sink,
            &[edit("t2", "title", "42", next_day, "two")],
            next_day,
            10,
        );
        assert_eq!(out.appended, 1);
        let EventBody::ProposalSuperseded(d) = &sink.all()[1].body else {
            panic!("expected a superseding event");
        };
        assert_eq!(d.supersedes.as_deref(), Some("t1"));
        let pending = frob_ledger::proposal::pending(&sink.all());
        assert_eq!(pending.len(), 1);
        assert_eq!(pending[0].data.tracker_event, "t2");
    }

    // frob:tests crates/frob-mirror/src/proposals.rs::record
    #[test]
    fn edits_beyond_the_run_cap_stay_after_the_cursor_and_share_one_commit() {
        let mut sink = Mem::default();
        let edits: Vec<Edit> = (0..5)
            .map(|i| edit(&format!("t{i}"), &format!("f{i}"), "42", DAY1 + i, "v"))
            .collect();
        let first = run(&mut sink, &edits, DAY1 + 100, 2);
        assert_eq!((first.appended, first.deferred), (2, 3));
        assert_eq!(first.advance_to, Some(EventId("t1".into())));
        assert_eq!(sink.commits.len(), 1);
        assert_eq!(sink.commits[0].len(), 2);
        // The next run re-reads from the cursor: the rest, plus nothing duplicated.
        let rest = run(&mut sink, &edits[2..], DAY1 + 200, 10);
        assert_eq!((rest.appended, rest.deferred), (3, 0));
        assert_eq!(rest.advance_to, Some(EventId("t4".into())));
        assert_eq!(sink.all().len(), 5);
    }

    // frob:tests crates/frob-mirror/src/proposals.rs::record
    #[test]
    fn the_daily_cap_defers_to_the_next_day_as_one_latest_value() {
        let mut sink = Mem::default();
        run(
            &mut sink,
            &[edit("t1", "title", "42", DAY1, "one")],
            DAY1,
            10,
        );
        let more = [
            edit("t2", "title", "42", DAY1 + 5, "two"),
            edit("t3", "title", "42", DAY1 + 6, "three"),
        ];
        let held = run(&mut sink, &more, DAY1 + 10, 10);
        assert_eq!((held.appended, held.deferred), (0, 1));
        assert_eq!(held.advance_to, Some(EventId("t2".into())));
        let tomorrow = DAY1 + DAY_SECS;
        let out = run(&mut sink, &more, tomorrow, 10);
        assert_eq!(out.appended, 1);
        let pending = frob_ledger::proposal::pending(&sink.all());
        assert_eq!(pending[0].data.tracker_event, "t3");
    }
}
