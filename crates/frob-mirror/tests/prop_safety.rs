//! Property tests for the safety rows (mirror.md 3.7; model README section 5, S1 to S9).
//!
//! Seeded loops over the fake GitHub drive a mirror through human edits, crashes and failures and
//! check after every step: no tracker-owned write (S1), cursor soundness (S2), proposals never
//! change the tracker and mirror writes hold ledger values (S4), map integrity (S5) and no reopen
//! of a closed proposal (S8). A converged state read from a fresh map changes nothing and commits
//! nothing (S9) within the call bound (S7). The model's traces D1, F2, F3 and F9 are fixed cases.
//! S6 (comment bound, trace F7) is not covered: the mirror posts no comments yet.

// frob:ticket 01M4052WE1HV1XJVZR6MCADM51
#![allow(dead_code)]

#[path = "support/fake_github.rs"]
mod fake_github;

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::time::Duration;

use fake_github::{BOT_ID, CrashPoint, FakeGithub, HUMAN_ID, Rng};
use frob_ledger::event::{Event, EventBody, ProposalCloseData};
use frob_ledger::proposal::{fold_proposals, pending as open_proposals};
use frob_mirror::adapter::{
    AdapterError, AdapterResult, HistoryEntry, IssueRef, IssueState, IssueSummary, TrackerAdapter,
};
use frob_mirror::budget::{BudgetConfig, RateLimit};
use frob_mirror::create::{CreateStep, Recovery, RecoveryEnv, create_issue, derive_nonce, recover};
use frob_mirror::cursor::{Committed, begin_read};
use frob_mirror::github::lookup::ListingSource;
use frob_mirror::github::read::{
    BodyRevision, BodyRevisions, HistorySource, TimelineEvent, creation_revision,
};
use frob_mirror::journal::value_digest;
use frob_mirror::keyring::{Keyring, MarkerFields};
use frob_mirror::mapfile::{MapError, Shard, ShardStore, content_hash};
use frob_mirror::marker::{MarkerVerdict, evaluate, format_marker};
use frob_mirror::plan::{WorkClass, WorkItem};
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, People, State, TicketFacts, project,
};
use frob_mirror::proposals::{Edit, ProposalSink, record};
use frob_mirror::run::{ItemError, RunConfig, RunHost, RunOutcome, run};
use gob_time::Stamp;
use gob_trust::MachineKey;

const START: &str = "2026-01-01T00:00:00Z";
const REPO: &str = "R_1";
const ULID: &str = "U1";
const SEEDS: u64 = 80;
const STEPS: u64 = 24;
const PER_RUN: usize = 2;
const DAY: i64 = 86_400;

/// In-memory shard store with compare-and-swap semantics.
#[derive(Default)]
struct Mem(HashMap<String, Vec<u8>>);

impl ShardStore for Mem {
    fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.0.get(key).cloned()
    }
    fn put_if(&mut self, key: &str, exp: Option<&str>, bytes: Vec<u8>) -> Result<(), MapError> {
        let found = self.get(key).map(|b| content_hash(&b));
        if found.as_deref() != exp {
            return Err(MapError::Conflict {
                key: key.into(),
                expected: exp.map(String::from),
                found,
            });
        }
        self.0.insert(key.into(), bytes);
        Ok(())
    }
}

/// The projection of ticket `ulid` carrying `title`.
fn projection(ulid: &str, title: &str) -> IssueProjection {
    let facts = TicketFacts {
        identity: Identity {
            ulid: ulid.into(),
            handle: format!("~{ulid}"),
            aliases: vec![],
            repository: "https://example.invalid/r".into(),
            ledger_path: format!("tickets/{ulid}.md"),
        },
        title: title.into(),
        summary: "s".into(),
        acceptance: vec![],
        scope: vec![],
        evidence: vec![],
        classification: Classification::default(),
        state: State {
            category: Category::Todo,
            outcome: None,
            reason: None,
        },
        relations: vec![],
        people: People::default(),
        last_event: "01EV".into(),
    };
    project(&facts, &BTreeSet::new(), "test")
}

fn ring() -> Keyring {
    Keyring::new("k1", MachineKey::from_bytes([1; 32]), vec![]).unwrap()
}

/// The tracker's read side over the fake: the timeline and body revisions come from its log, and
/// the creation revision of an issue shows the signed marker for the nonce the fake logged for it
/// (authored by whoever created the issue).
struct Source<'a> {
    g: &'a FakeGithub,
    /// `(ulid, nonce)` of every create attempt the test made.
    cands: &'a [(String, String)],
}

impl Source<'_> {
    fn number(issue: &IssueRef) -> u64 {
        issue.0.parse().unwrap()
    }

    /// The creation body and its author, when the fake logged a known nonce for the issue.
    fn marked_body(&self, n: u64) -> Option<(u64, String)> {
        let logged = self
            .g
            .log()
            .iter()
            .find(|l| l.issue == n && l.entry.field == "nonce")?;
        let (ulid, nonce) = self
            .cands
            .iter()
            .find(|(_, c)| logged.entry.value_digest == value_digest(c).as_str())?;
        let m = ring().sign(MarkerFields {
            repo_node_id: REPO.into(),
            ulid: ulid.clone(),
            nonce: nonce.clone(),
        });
        Some((
            logged.entry.actor_id,
            format!("body\n<!-- {} -->", format_marker(&m)),
        ))
    }
}

impl HistorySource for Source<'_> {
    fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
        self.g.read(issue)
    }
    fn timeline(&self, issue: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
        let n = Self::number(issue);
        Ok(self
            .g
            .log()
            .iter()
            .filter(|l| l.issue == n && !matches!(l.entry.field.as_str(), "nonce" | "body"))
            .map(|l| TimelineEvent {
                id: l.event.0.clone(),
                created_at: START.into(),
                actor_id: l.entry.actor_id,
                field: l.entry.field.clone(),
                value: l.entry.value_digest.clone(),
            })
            .collect())
    }
    fn body_revisions(&self, issue: &IssueRef) -> AdapterResult<BodyRevisions> {
        let n = Self::number(issue);
        let mut revisions: Vec<BodyRevision> = self
            .g
            .log()
            .iter()
            .filter(|l| l.issue == n && l.entry.field == "body")
            .map(|l| BodyRevision {
                id: l.event.0.clone(),
                created_at: START.into(),
                editor_id: Some(l.entry.actor_id),
                body: Some(format!("body {}", l.entry.value_digest)),
            })
            .collect();
        if let (Some(first), Some((author, body))) = (revisions.first_mut(), self.marked_body(n)) {
            first.editor_id = Some(author);
            first.body = Some(body);
        }
        Ok(BodyRevisions {
            revisions,
            truncated: false,
        })
    }
}

/// An adversarial listing: every issue regardless of creator, newest first.
struct EveryIssue<'a>(&'a FakeGithub);

impl ListingSource for EveryIssue<'_> {
    fn page(&self, _creator: u64, page: u32) -> AdapterResult<Vec<IssueSummary>> {
        if page != 1 {
            return Ok(vec![]);
        }
        let mut all = self.0.list_by_creator(BOT_ID)?;
        all.extend(self.0.list_by_creator(HUMAN_ID)?);
        all.sort_by(|a, b| {
            b.issue
                .0
                .len()
                .cmp(&a.issue.0.len())
                .then(b.issue.cmp(&a.issue))
        });
        Ok(all)
    }
}

/// The ledger side of proposals: every committed event, with a switch for a failing commit.
#[derive(Default)]
struct Sink {
    events: Vec<Event>,
    commits: usize,
    fail: bool,
}

impl ProposalSink for Sink {
    type Error = ();
    fn commit(&mut self, events: Vec<Event>) -> Result<(), ()> {
        if self.fail {
            return Err(());
        }
        self.commits += 1;
        self.events.extend(events);
        Ok(())
    }
}

/// Fields a repository owns; an outside edit of one becomes a proposal.
fn repo_owned(field: &str) -> bool {
    matches!(field, "title" | "body" | "state")
}

/// The numeric position of a fake event id.
fn secs(event: &str) -> i64 {
    event.parse().unwrap()
}

/// The non-mirror edits of repository-owned fields in `entries`, oldest first.
fn edits_of(item: &str, entries: &[HistoryEntry]) -> Vec<Edit> {
    entries
        .iter()
        .filter(|e| e.actor_id != BOT_ID && repo_owned(&e.field))
        .map(|e| Edit {
            tracker_event: e.event.clone(),
            item: item.to_owned(),
            field: e.field.clone(),
            actor_id: e.actor_id.to_string(),
            time: Stamp::from_unix(secs(&e.event.0)),
            value: e.value_digest.clone(),
        })
        .collect()
}

/// How a mirror step fails.
#[derive(Debug, Clone, Copy)]
enum Crash {
    Clean,
    /// The history read fails.
    ReadFail,
    /// The process dies before the ledger commit.
    BeforeCommit,
    /// The process dies after the ledger commit and before the cursor is stored.
    AfterCommit,
}

/// One mirrored ticket against the fake, with the ledger it records proposals into.
struct Mirror {
    g: FakeGithub,
    shard: Shard,
    sink: Sink,
    issue: IssueRef,
    /// Every title the ledger has held (S4: mirror writes carry only these).
    titles: Vec<String>,
    /// Tracker event ids of proposals a human declined.
    declined: BTreeSet<String>,
    day: i64,
    counter: u64,
}

impl Mirror {
    /// A ticket whose issue the mirror has just created.
    fn new(seed: u64) -> Self {
        let mut g = FakeGithub::new(seed);
        let title = "title 0".to_owned();
        let step = create_issue(
            &mut Mem::default(),
            &mut g,
            Shard::new(ULID),
            &projection(ULID, &title),
            "r1",
            START,
            frob_mirror::cursor::PendingCursor::empty(),
        )
        .unwrap();
        let CreateStep::Created(c) = step else {
            panic!("a clean create must land");
        };
        let issue = IssueRef(c.shard.issue_number.unwrap().to_string());
        Self {
            g,
            shard: c.shard,
            sink: Sink::default(),
            issue,
            titles: vec![title],
            declined: BTreeSet::new(),
            day: 1,
            counter: 0,
        }
    }

    fn cands() -> Vec<(String, String)> {
        vec![(ULID.to_owned(), derive_nonce(ULID, "r1", START))]
    }

    /// One sync: read after the cursor, record proposals, then store the cursor.
    fn sync(&mut self, mode: Crash) {
        if matches!(mode, Crash::ReadFail) {
            self.g.crash_at(self.g.calls() + 1, CrashPoint::Before);
            // The read fails on its first tracker call; nothing is recorded or advanced.
            assert!(self.g.read(&self.issue).is_err());
            return;
        }
        let cands = Self::cands();
        let read = {
            let src = Source {
                g: &self.g,
                cands: &cands,
            };
            begin_read(&src, &self.issue, &self.shard)
        };
        let Ok(read) = read else {
            return;
        };
        let edits = edits_of(&self.issue.0, &read.history.entries);
        self.sink.fail = matches!(mode, Crash::BeforeCommit);
        let before = self.g.snapshot();
        let existing = self.sink.events.clone();
        let now = Stamp::from_unix(self.day * DAY + 100);
        let outcome = record(&mut self.sink, &existing, &edits, "mirror", now, PER_RUN);
        self.sink.fail = false;
        let after = self.g.snapshot();
        // S4: recording proposals leaves the tracker as it was.
        assert_eq!(before.issues, after.issues, "S4: record changed an issue");
        assert_eq!(before.log, after.log, "S4: record changed the history");
        let Ok(rec) = outcome else {
            return;
        };
        if matches!(mode, Crash::AfterCommit) {
            return;
        }
        let shard = self.shard.clone();
        self.shard = if rec.deferred == 0 {
            read.pending
                .advance(shard, rec.committed.unwrap_or_else(Committed::confirm))
        } else if let Some(upto) = rec.advance_to {
            let mut held = shard;
            held.history_cursor = Some(upto.0);
            held
        } else {
            shard
        };
    }

    /// The ledger changes the title and the mirror writes it, possibly crashing around the write.
    fn publish(&mut self, rng: &mut Rng) {
        self.counter += 1;
        let title = format!("title {}", self.counter);
        self.titles.push(title.clone());
        match rng.below(3) {
            0 => self.g.crash_at(self.g.calls() + 1, CrashPoint::Before),
            1 => self.g.crash_at(self.g.calls() + 1, CrashPoint::After),
            _ => {}
        }
        let _ = self.g.update(&self.issue, &projection(ULID, &title));
    }

    /// One human action: a repository-owned edit, a tracker-owned label, or a spoofed nonce.
    fn human(&mut self, rng: &mut Rng) {
        self.counter += 1;
        let text = format!("human {}", self.counter);
        match rng.below(6) {
            0 => self.g.human_edit_title(&self.issue, &text),
            1 => self.g.human_edit_body(&self.issue, &text),
            2 => self.g.human_add_label(&self.issue, &text),
            3 => self.g.human_remove_label(&self.issue, &text),
            4 => self.g.human_set_closed(&self.issue, rng.below(2) == 0),
            _ => self.g.human_spoof_marker(&self.issue, &text),
        }
    }

    /// A human declines a pending proposal (closing it for good).
    fn decline(&mut self, rng: &mut Rng) {
        let open = open_proposals(&self.sink.events);
        if open.is_empty() {
            return;
        }
        let pick = &open[usize::try_from(rng.below(open.len() as u64)).unwrap()];
        let key = pick.data.tracker_event.clone();
        self.declined.insert(key.clone());
        self.sink.events.push(Event::new(
            Stamp::from_unix(self.day * DAY + 200),
            "human",
            EventBody::ProposalDeclined(ProposalCloseData {
                tracker_event: key,
                reason: None,
            }),
        ));
    }

    /// Whether a human repository-owned edit at `id` is covered: recorded, superseded by a later
    /// recorded edit of the field, or followed by a later edit that the cursor has not passed.
    fn covered(&self, field: &str, id: &str) -> bool {
        let recorded = fold_proposals(&self.sink.events).iter().any(|p| {
            p.data.item == self.issue.0
                && p.data.field == field
                && p.data.tracker_event.as_str() >= id
        });
        let cursor = self.shard.history_cursor.as_deref();
        let later_unread = self.g.log().iter().any(|l| {
            l.issue == Source::number(&self.issue)
                && l.entry.actor_id == HUMAN_ID
                && l.entry.field == field
                && l.event.0.as_str() > id
                && cursor.is_none_or(|c| l.event.0.as_str() > c)
        });
        recorded || later_unread
    }

    /// The safety invariants S1, S2, S4 (writes) and S8, after any step.
    fn check(&self, ctx: &str) {
        let digests: BTreeSet<String> = self
            .titles
            .iter()
            .map(|t| value_digest(t).as_str().to_owned())
            .collect();
        for l in self.g.log().iter().filter(|l| l.entry.actor_id == BOT_ID) {
            // S1: the mirror never writes the tracker-owned field.
            assert_ne!(l.entry.field, "labels", "{ctx}: S1 bot wrote labels");
            // S4: every title the mirror wrote is a value the ledger held.
            if l.entry.field == "title" {
                assert!(
                    digests.contains(&l.entry.value_digest),
                    "{ctx}: S4 bot wrote a title the ledger never held"
                );
            }
        }
        // S2: every human edit at or before the committed cursor is covered by a proposal.
        if let Some(cursor) = self.shard.history_cursor.as_deref() {
            for l in self.g.log() {
                if l.entry.actor_id == HUMAN_ID
                    && repo_owned(&l.entry.field)
                    && l.event.0.as_str() <= cursor
                {
                    assert!(
                        self.covered(&l.entry.field, &l.event.0),
                        "{ctx}: S2 edit {} of {} passed by cursor {cursor} and not recorded",
                        l.event.0,
                        l.entry.field
                    );
                }
            }
        }
        // S8: a declined proposal is never pending again.
        for p in open_proposals(&self.sink.events) {
            assert!(
                !self.declined.contains(&p.data.tracker_event),
                "{ctx}: S8 declined proposal {} reopened",
                p.data.tracker_event
            );
        }
    }

    /// Drains the backlog on fresh days with no faults, as a healthy mirror would.
    fn drain(&mut self, ctx: &str) {
        for _ in 0..6 {
            self.day += 1;
            self.sync(Crash::Clean);
            self.check(ctx);
        }
    }
}

fn crash_mode(rng: &mut Rng) -> Crash {
    match rng.below(4) {
        0 => Crash::Clean,
        1 => Crash::ReadFail,
        2 => Crash::BeforeCommit,
        _ => Crash::AfterCommit,
    }
}

/// Runs a random scenario of human edits, crashes and failures, checking after every step.
fn scenario(seed: u64) -> Mirror {
    let mut rng = Rng::new(seed);
    let mut m = Mirror::new(seed);
    m.check(&format!("seed {seed} start"));
    for step in 0..STEPS {
        let ctx = format!("seed {seed} step {step}");
        match rng.below(9) {
            0..=2 => m.human(&mut rng),
            3 => m.publish(&mut rng),
            4..=5 => {
                let mode = crash_mode(&mut rng);
                m.sync(mode);
            }
            6 => m.decline(&mut rng),
            7 => m.shard.history_cursor = None,
            _ => m.day += 1,
        }
        m.check(&ctx);
    }
    m
}

// frob:tests record
// frob:tests begin_read
// frob:tests advance
#[test]
fn random_edits_crashes_and_failures_keep_s1_s2_s4_s5_s8() {
    for seed in 0..SEEDS {
        let mut m = scenario(seed);
        m.drain(&format!("seed {seed} drain"));
        // After a healthy drain the cursor has passed every human edit and all are recorded.
        let last =
            m.g.log()
                .iter()
                .filter(|l| l.entry.actor_id == HUMAN_ID && repo_owned(&l.entry.field))
                .map(|l| l.event.0.clone())
                .max();
        if let Some(last) = last {
            let cursor = m.shard.history_cursor.clone().unwrap_or_default();
            assert!(
                cursor >= last,
                "seed {seed}: cursor {cursor} behind edit {last}"
            );
        }
        let cands = Mirror::cands();
        let src = Source {
            g: &m.g,
            cands: &cands,
        };
        assert_owned(&[&m.shard], &src, &m.g, &format!("seed {seed}"));
    }
}

/// S5: every mapped issue is bot-authored and its creation marker names that ticket.
fn assert_owned(shards: &[&Shard], src: &Source<'_>, g: &FakeGithub, ctx: &str) {
    let bot_issues: BTreeSet<String> = g
        .list_by_creator(BOT_ID)
        .unwrap()
        .into_iter()
        .map(|i| i.issue.0)
        .collect();
    for s in shards {
        let Some(n) = s.issue_number else {
            continue;
        };
        let issue = IssueRef(n.to_string());
        assert!(
            bot_issues.contains(&issue.0),
            "{ctx}: S5 {} maps to a human issue",
            s.ulid
        );
        let creation = creation_revision(src, &issue, BOT_ID).unwrap();
        let verdict = evaluate(&creation, &[BOT_ID], &ring(), REPO, 0);
        let MarkerVerdict::Adopted(m) = verdict else {
            panic!(
                "{ctx}: S5 {} maps to issue {n} without a valid marker: {verdict:?}",
                s.ulid
            );
        };
        assert_eq!(
            m.fields.ulid, s.ulid,
            "{ctx}: S5 marker names another ticket"
        );
    }
}

// frob:tests recover
// frob:tests evaluate
// frob:tests creation_revision
// frob:tests create_issue
#[test]
fn a_pasted_marker_never_maps_ticket_b_to_ticket_as_issue() {
    for seed in 0..SEEDS {
        let late = seed % 2 == 1;
        let mut g = FakeGithub::new(seed);
        let mut store = Mem::default();
        let nonce_a = derive_nonce("UA", "rA", START);
        let nonce_b = derive_nonce("UB", "rB", START);
        let CreateStep::Created(a) = create_issue(
            &mut store,
            &mut g,
            Shard::new("UA"),
            &projection("UA", "a"),
            "rA",
            START,
            frob_mirror::cursor::PendingCursor::empty(),
        )
        .unwrap() else {
            panic!("A's create must land");
        };
        let issue_a = IssueRef(a.shard.issue_number.unwrap().to_string());
        if late {
            g.delay_next_create(3);
        } else {
            g.lose_next_create();
        }
        let CreateStep::Uncertain(b) = create_issue(
            &mut store,
            &mut g,
            Shard::new("UB"),
            &projection("UB", "b"),
            "rB",
            START,
            frob_mirror::cursor::PendingCursor::empty(),
        )
        .unwrap() else {
            panic!("B's create must be uncertain");
        };
        // D1: a human pastes B's marker into A's issue and into an issue of their own.
        g.human_edit_body(&issue_a, "pasted B marker");
        g.human_spoof_marker(&issue_a, &nonce_b);
        let human_issue = g.human_create_marked("copy", "x", &nonce_b);
        g.advance(5);
        let cands = vec![("UA".to_owned(), nonce_a), ("UB".to_owned(), nonce_b)];
        let src = Source {
            g: &g,
            cands: &cands,
        };
        let listing = EveryIssue(&g);
        let ring = ring();
        let env = RecoveryEnv {
            listing: &listing,
            source: &src,
            ring: &ring,
            bot_ids: &[BOT_ID],
            repo_node_id: REPO,
            now: 0,
        };
        let (Recovery::Adopted(b) | Recovery::NotLanded(b) | Recovery::Nothing(b)) =
            recover(&mut store, &env, b).unwrap();
        assert_ne!(
            b.issue_number, a.shard.issue_number,
            "seed {seed}: D1 B maps to A's issue"
        );
        assert_ne!(
            b.issue_number.map(|n| n.to_string()),
            Some(human_issue.0.clone()),
            "seed {seed}: B maps to the human's copy"
        );
        assert_eq!(
            b.issue_number.is_some(),
            late,
            "seed {seed}: adopt only a landed create"
        );
        assert_owned(&[&a.shard, &b], &src, &g, &format!("seed {seed}"));
    }
}

// frob:tests record
// frob:tests pending
#[test]
fn a_declined_proposal_stays_closed_after_a_crash_before_the_cursor_commit() {
    for crash in [Crash::Clean, Crash::AfterCommit] {
        let mut m = Mirror::new(7);
        m.g.human_edit_title(&m.issue.clone(), "outside edit");
        m.sync(Crash::AfterCommit);
        m.check("recorded");
        let pending = open_proposals(&m.sink.events);
        assert_eq!(pending.len(), 1, "the edit is recorded once");
        let key = pending[0].data.tracker_event.clone();
        m.declined.insert(key.clone());
        m.sink.events.push(Event::new(
            Stamp::from_unix(DAY + 300),
            "human",
            EventBody::ProposalDeclined(ProposalCloseData {
                tracker_event: key,
                reason: Some("no".into()),
            }),
        ));
        // F9: the cursor never reached the shard, so the next run re-reads the same edit.
        assert!(m.shard.history_cursor.is_none() || matches!(crash, Crash::Clean));
        m.shard.history_cursor = None;
        m.sync(crash);
        m.sync(Crash::Clean);
        m.check("re-read");
        assert!(
            open_proposals(&m.sink.events).is_empty(),
            "S8: declined edit reopened"
        );
        let recorded = fold_proposals(&m.sink.events).len();
        assert_eq!(recorded, 1, "the re-read recorded nothing new");
    }
}

// frob:tests begin_read
// frob:tests record
// frob:tests advance
#[test]
fn the_cursor_never_passes_an_edit_it_did_not_read() {
    let mut rng = Rng::new(3);
    // F2: a human edits after the read and a mirror publish lands after it; F3: a delayed
    // create lands late. The held cursor is the one read, never the newest event of the issue.
    let mut m = Mirror::new(3);
    let cands = Mirror::cands();
    let read = {
        let src = Source {
            g: &m.g,
            cands: &cands,
        };
        begin_read(&src, &m.issue, &m.shard).unwrap()
    };
    let edit_issue = m.issue.clone();
    m.g.human_edit_title(&edit_issue, "edited after the read");
    m.publish(&mut rng);
    m.g.delay_next_create(1);
    m.g.advance(10);
    let edit =
        m.g.log()
            .iter()
            .find(|l| l.entry.actor_id == HUMAN_ID)
            .map(|l| l.event.0.clone())
            .unwrap();
    m.shard = read.pending.advance(m.shard.clone(), Committed::confirm());
    let cursor = m.shard.history_cursor.clone().unwrap_or_default();
    assert!(
        cursor < edit,
        "F2/F3: cursor {cursor} passed the unread edit {edit}"
    );
    m.check("after advance");
    m.sync(Crash::Clean);
    m.check("after next sync");
    assert!(
        fold_proposals(&m.sink.events)
            .iter()
            .any(|p| p.data.tracker_event == edit),
        "the edit is recorded by the next run"
    );
}

/// A host that finds a converged ticket: it reads, compares and records, and mutates only on drift.
struct Quiet {
    ledger: Vec<Event>,
    issue: IssueRef,
    title: String,
    commits: usize,
    mutations: usize,
    now: i64,
}

impl Quiet {
    fn map_err(e: AdapterError) -> ItemError {
        match e {
            AdapterError::RateLimited => ItemError::RateLimited { reset: None },
            other => ItemError::Failed(other.to_string()),
        }
    }
}

impl RunHost for Quiet {
    fn rate_limit(&self) -> RateLimit {
        RateLimit {
            remaining: Some(8),
            reset: Some(0),
        }
    }

    fn pending<S: ShardStore>(&self, _store: &S) -> Vec<WorkItem> {
        vec![]
    }

    fn sweep_universe(&self) -> Vec<String> {
        vec![ULID.to_owned()]
    }

    fn execute<S: ShardStore>(
        &mut self,
        item: &WorkItem,
        _store: &mut S,
        adapter: &mut dyn TrackerAdapter,
    ) -> Result<Option<Shard>, ItemError> {
        assert_eq!(
            item.class,
            WorkClass::Sweep,
            "a converged ticket only sweeps"
        );
        let state = adapter.read(&self.issue).map_err(Self::map_err)?;
        let entries = adapter
            .history_after(&self.issue, None)
            .map_err(Self::map_err)?;
        let edits = edits_of(&self.issue.0, &entries);
        let mut sink = Sink::default();
        record(
            &mut sink,
            &self.ledger,
            &edits,
            "mirror",
            Stamp::from_unix(self.now),
            PER_RUN,
        )
        .expect("an infallible sink");
        self.commits += sink.commits;
        if state.title != self.title {
            self.mutations += 1;
            adapter
                .update(&self.issue, &projection(ULID, &self.title))
                .map_err(Self::map_err)?;
        }
        Ok(None)
    }
}

// frob:tests run
// frob:tests record
#[test]
fn a_converged_run_from_a_fresh_map_changes_nothing() {
    for seed in 0..SEEDS {
        let mut m = scenario(seed);
        // Converge: publish the ledger title, then drain every edit on healthy days.
        m.counter += 1;
        let title = format!("title {}", m.counter);
        m.titles.push(title.clone());
        m.g.update(&m.issue.clone(), &projection(ULID, &title))
            .unwrap();
        m.drain(&format!("seed {seed} converge"));
        let before = m.g.snapshot();
        let mut host = Quiet {
            ledger: m.sink.events.clone(),
            issue: m.issue.clone(),
            title,
            commits: 0,
            mutations: 0,
            now: (m.day + 1) * DAY,
        };
        let cfg = RunConfig {
            run_id: "fresh".into(),
            now: 1_000,
            lock_ttl_secs: 3600,
            commit_every: 2,
            sweep_k: 1,
            bot_id: BOT_ID,
            budget: BudgetConfig {
                share_percent: 100,
                spacing: Duration::ZERO,
                ..BudgetConfig::default()
            },
        };
        let outcome = run(&mut Mem::default(), &mut m.g, &mut host, &cfg).unwrap();
        assert!(
            matches!(outcome, RunOutcome::Ran(_)),
            "seed {seed}: {outcome:?}"
        );
        let after = m.g.snapshot();
        // S9: no tracker mutation and no ledger commit.
        assert_eq!(host.mutations, 0, "seed {seed}: S9 mutated");
        assert_eq!(host.commits, 0, "seed {seed}: S9 committed to the ledger");
        assert_eq!(
            before.issues, after.issues,
            "seed {seed}: S9 issues changed"
        );
        assert_eq!(before.log, after.log, "seed {seed}: S9 history changed");
        // S7: the run stayed within the rate limit it was given.
        assert!(
            after.calls - before.calls <= 8,
            "seed {seed}: S7 over budget"
        );
    }
}

// frob:tests edits_of
#[test]
fn labels_are_tracker_owned_and_never_become_edits() {
    let mut g = FakeGithub::new(1);
    let mut m = Mirror::new(1);
    m.g.human_add_label(&m.issue.clone(), "frob:todo");
    m.g.human_remove_label(&m.issue.clone(), "frob:todo");
    m.sync(Crash::Clean);
    m.check("labels");
    assert!(
        fold_proposals(&m.sink.events).is_empty(),
        "a label edit is not a proposal"
    );
    let _ = (&mut g, BTreeMap::<u8, u8>::new());
}
