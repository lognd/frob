//! Deterministic fake GitHub for replaying the mirror model (mirror.md 3.7, models/mirror 2).
//!
//! It implements [`TrackerAdapter`] over an append-only event log. Everything that varies is
//! driven either by an explicit script (`lose_next_create`, `crash_at`, ...) or by a seeded
//! [`Chaos`] draw, so a scenario with the same seed replays byte for byte.

// frob:ticket 01M4052WAB3H52W92NYG3AS571

use std::cell::RefCell;
use std::collections::{BTreeMap, BTreeSet};

use frob_mirror::adapter::{
    AdapterError, AdapterResult, Capabilities, CreateOutcome, EventId, HistoryEntry,
    HistoryRetention, Inventory, IssueRef, IssueState, IssueSummary, MarkdownDialect, StateReasons,
    TrackerAdapter,
};
use frob_mirror::projection::{IssueProjection, Outcome, RelationKind};
use tracing::{debug, trace, warn};

/// User id of the mirror bot.
pub const BOT_ID: u64 = 1;
/// User id of the adversarial human.
pub const HUMAN_ID: u64 = 2;

/// Seeded splitmix64 generator; no external dependency, identical on every platform.
#[derive(Debug, Clone)]
pub struct Rng(u64);

impl Rng {
    /// Start a stream from `seed`.
    pub fn new(seed: u64) -> Self {
        Self(seed)
    }

    /// Next 64-bit value.
    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform value in `0..n` (`n` must be non-zero).
    pub fn below(&mut self, n: u64) -> u64 {
        self.next_u64() % n
    }
}

/// Where in a call an injected crash lands.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CrashPoint {
    /// The process dies before the tracker saw the call.
    Before,
    /// The tracker applied the call but the caller never saw the answer.
    After,
}

/// Per-mille probabilities of random network faults, drawn from a seeded stream.
#[derive(Debug, Clone, Copy, Default)]
pub struct Chaos {
    /// A create is silently lost.
    pub lose_create: u64,
    /// A create lands later (1..=5 ticks).
    pub delay_create: u64,
    /// A write is applied twice.
    pub duplicate: u64,
    /// The call crashes (before or after, evenly).
    pub crash: u64,
}

/// One landed event in the global append-only log.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoggedEvent {
    /// Event id (zero padded so string order is arrival order).
    pub event: EventId,
    /// Issue number the event belongs to.
    pub issue: u64,
    /// The history entry itself.
    pub entry: HistoryEntry,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct Issue {
    title: String,
    body: String,
    labels: BTreeSet<String>,
    assignees: BTreeSet<String>,
    closed: bool,
    creator_id: u64,
    created_at: String,
    seq: u64,
    history: Vec<HistoryEntry>,
}

#[derive(Debug, Clone)]
struct PendingCreate {
    due: u64,
    creator_id: u64,
    title: String,
    body: String,
    nonce: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Fault {
    None,
    Lose,
    Delay(u64),
    Duplicate,
    Crash(CrashPoint),
}

/// What the fake currently holds, for equality across replays.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Snapshot {
    /// Every issue as `(number, state)`.
    pub issues: Vec<(u64, IssueState)>,
    /// The whole event log.
    pub log: Vec<LoggedEvent>,
    /// Calls made, refusals included.
    pub calls: u64,
    /// Calls refused as rate-limited.
    pub refused: u64,
}

/// The fake tracker.
#[derive(Debug, Clone)]
pub struct FakeGithub {
    issues: BTreeMap<u64, Issue>,
    log: Vec<LoggedEvent>,
    pending: Vec<PendingCreate>,
    next_number: u64,
    next_event: u64,
    now: u64,
    meter: RefCell<Meter>,
    chaos: Chaos,
    lose_next_create: bool,
    delay_next_create: Option<u64>,
    duplicate_next_write: bool,
}

/// Per-call state that reads must update through `&self`.
#[derive(Debug, Clone)]
struct Meter {
    calls: u64,
    refused: u64,
    budget: Option<u64>,
    rng: Rng,
    crash_at: Option<(u64, CrashPoint)>,
}

fn digest(s: &str) -> String {
    blake3::hash(s.as_bytes()).to_hex().to_string()
}

fn stamp(now: u64) -> String {
    let s = now % 86_400;
    format!(
        "2026-01-01T{:02}:{:02}:{:02}Z",
        s / 3600,
        (s / 60) % 60,
        s % 60
    )
}

fn render_body(p: &IssueProjection) -> String {
    format!("{:?}", p.sections)
}

impl FakeGithub {
    /// A fresh tracker whose random draws come from `seed`.
    pub fn new(seed: u64) -> Self {
        Self {
            issues: BTreeMap::new(),
            log: Vec::new(),
            pending: Vec::new(),
            next_number: 1,
            next_event: 1,
            now: 0,
            meter: RefCell::new(Meter {
                calls: 0,
                refused: 0,
                budget: None,
                rng: Rng::new(seed),
                crash_at: None,
            }),
            chaos: Chaos::default(),
            lose_next_create: false,
            delay_next_create: None,
            duplicate_next_write: false,
        }
    }

    /// Enable seeded random faults.
    pub fn with_chaos(mut self, chaos: Chaos) -> Self {
        self.chaos = chaos;
        self
    }

    /// Allow only `calls` calls; the next one is refused as rate-limited.
    pub fn with_call_budget(mut self, calls: u64) -> Self {
        self.meter.get_mut().budget = Some(calls);
        self
    }

    /// Refill the call budget to `calls` further calls (a new rate-limit window).
    pub fn reset_budget(&mut self, calls: u64) {
        let m = self.meter.get_mut();
        m.budget = Some(m.calls + calls);
    }

    /// Calls made so far, refused ones included.
    pub fn calls(&self) -> u64 {
        self.meter.borrow().calls
    }

    /// Calls refused as rate-limited so far.
    pub fn refused(&self) -> u64 {
        self.meter.borrow().refused
    }

    /// Current fake time in ticks.
    pub fn now(&self) -> u64 {
        self.now
    }

    /// The whole append-only event log.
    pub fn log(&self) -> &[LoggedEvent] {
        &self.log
    }

    /// Creates accepted but not yet landed.
    pub fn pending_creates(&self) -> usize {
        self.pending.len()
    }

    /// Script: the next create is lost (answers `Unknown`, never lands).
    pub fn lose_next_create(&mut self) {
        self.lose_next_create = true;
    }

    /// Script: the next create answers `Unknown` and lands `ticks` later.
    pub fn delay_next_create(&mut self, ticks: u64) {
        self.delay_next_create = Some(ticks);
    }

    /// Script: the next write is applied twice.
    pub fn duplicate_next_write(&mut self) {
        self.duplicate_next_write = true;
    }

    /// Script: the call numbered `call` (1-based, counting every call) crashes at `point`.
    pub fn crash_at(&mut self, call: u64, point: CrashPoint) {
        self.meter.get_mut().crash_at = Some((call, point));
    }

    /// Advance time; delayed creates that fall due land now, in due order.
    pub fn advance(&mut self, ticks: u64) {
        self.now += ticks;
        let now = self.now;
        let (mut due, rest): (Vec<_>, Vec<_>) = self.pending.drain(..).partition(|p| p.due <= now);
        self.pending = rest;
        due.sort_by_key(|p| p.due);
        for p in due {
            let n = self.land_create(&p.title, &p.body, p.creator_id, &p.nonce);
            debug!(issue = n, "delayed create landed");
        }
    }

    /// Adversary: a human replaces the title.
    pub fn human_edit_title(&mut self, issue: &IssueRef, title: &str) {
        if let Some(n) = self.number(issue) {
            self.issues.get_mut(&n).expect("exists").title = title.to_string();
            self.record(n, HUMAN_ID, "title", title);
        }
    }

    /// Adversary: a human replaces the body (a repository-owned field).
    pub fn human_edit_body(&mut self, issue: &IssueRef, body: &str) {
        if let Some(n) = self.number(issue) {
            self.issues.get_mut(&n).expect("exists").body = body.to_string();
            self.record(n, HUMAN_ID, "body", body);
        }
    }

    /// Adversary: a human adds a label (a tracker-owned field).
    pub fn human_add_label(&mut self, issue: &IssueRef, label: &str) {
        if let Some(n) = self.number(issue) {
            self.issues
                .get_mut(&n)
                .expect("exists")
                .labels
                .insert(label.into());
            self.record(n, HUMAN_ID, "labels", &format!("+{label}"));
        }
    }

    /// Adversary: a human removes a label.
    pub fn human_remove_label(&mut self, issue: &IssueRef, label: &str) {
        if let Some(n) = self.number(issue) {
            self.issues
                .get_mut(&n)
                .expect("exists")
                .labels
                .remove(label);
            self.record(n, HUMAN_ID, "labels", &format!("-{label}"));
        }
    }

    /// Adversary: a human closes or reopens the issue.
    pub fn human_set_closed(&mut self, issue: &IssueRef, closed: bool) {
        if let Some(n) = self.number(issue) {
            self.issues.get_mut(&n).expect("exists").closed = closed;
            self.record(n, HUMAN_ID, "state", if closed { "closed" } else { "open" });
        }
    }

    /// Adversary: a human writes a creation-revision `nonce` entry onto an existing issue.
    pub fn human_spoof_marker(&mut self, issue: &IssueRef, nonce: &str) {
        if let Some(n) = self.number(issue) {
            self.record(n, HUMAN_ID, "nonce", nonce);
        }
    }

    /// Adversary: a human creates an issue carrying a marker `nonce` of their own.
    pub fn human_create_marked(&mut self, title: &str, body: &str, nonce: &str) -> IssueRef {
        let n = self.land_create(title, body, HUMAN_ID, nonce);
        IssueRef(n.to_string())
    }

    /// Everything the fake holds, for comparing two runs.
    pub fn snapshot(&self) -> Snapshot {
        Snapshot {
            issues: self
                .issues
                .iter()
                .map(|(n, i)| (*n, Self::state_of(*n, i)))
                .collect(),
            log: self.log.clone(),
            calls: self.calls(),
            refused: self.refused(),
        }
    }

    fn state_of(n: u64, i: &Issue) -> IssueState {
        IssueState {
            issue: IssueRef(n.to_string()),
            title: i.title.clone(),
            body: i.body.clone(),
            labels: i.labels.iter().cloned().collect(),
            assignees: i.assignees.iter().cloned().collect(),
            closed: i.closed,
        }
    }

    fn number(&self, issue: &IssueRef) -> Option<u64> {
        issue.0.parse().ok().filter(|n| self.issues.contains_key(n))
    }

    fn record(&mut self, n: u64, actor_id: u64, field: &str, value: &str) {
        let event = EventId(format!("{:010}", self.next_event));
        self.next_event += 1;
        let entry = HistoryEntry {
            event: event.clone(),
            actor_id,
            field: field.to_string(),
            value_digest: digest(value),
        };
        trace!(issue = n, field, actor_id, "event appended");
        self.issues
            .get_mut(&n)
            .expect("record on existing issue")
            .history
            .push(entry.clone());
        self.log.push(LoggedEvent {
            event,
            issue: n,
            entry,
        });
    }

    fn land_create(&mut self, title: &str, body: &str, creator_id: u64, nonce: &str) -> u64 {
        let n = self.next_number;
        self.next_number += 1;
        self.issues.insert(
            n,
            Issue {
                title: title.into(),
                body: body.into(),
                labels: BTreeSet::new(),
                assignees: BTreeSet::new(),
                closed: false,
                creator_id,
                created_at: stamp(self.now),
                seq: n,
                history: Vec::new(),
            },
        );
        self.record(n, creator_id, "nonce", nonce);
        self.record(n, creator_id, "title", title);
        self.record(n, creator_id, "body", body);
        n
    }

    /// Count the call, enforce the budget, and decide this call's fault.
    fn gate(&self, op: &str) -> AdapterResult<Fault> {
        let mut m = self.meter.borrow_mut();
        m.calls += 1;
        // One draw per call keeps the stream aligned however the call ends.
        let draw = m.rng.below(1000);
        let pick = m.rng.below(10);
        if m.budget.is_some_and(|b| m.calls > b) {
            m.refused += 1;
            warn!(op, calls = m.calls, "call refused as rate-limited");
            return Err(AdapterError::RateLimited);
        }
        if let Some((at, point)) = m.crash_at
            && at == m.calls
        {
            m.crash_at = None;
            return Ok(Fault::Crash(point));
        }
        drop(m);
        let c = self.chaos;
        let mut edge = c.lose_create;
        if op == "create" && draw < edge {
            return Ok(Fault::Lose);
        }
        edge += c.delay_create;
        if op == "create" && draw < edge {
            return Ok(Fault::Delay(1 + pick % 5));
        }
        edge += c.duplicate;
        if draw < edge && !matches!(op, "read" | "list" | "history" | "inventory") {
            return Ok(Fault::Duplicate);
        }
        edge += c.crash;
        if draw < edge {
            let point = if pick.is_multiple_of(2) {
                CrashPoint::Before
            } else {
                CrashPoint::After
            };
            return Ok(Fault::Crash(point));
        }
        Ok(Fault::None)
    }

    /// Gate a call and run `apply` for a write, honouring crash and duplicate faults.
    fn write<F: FnMut(&mut Self) -> AdapterResult<()>>(
        &mut self,
        op: &str,
        mut apply: F,
    ) -> AdapterResult<()> {
        let mut fault = self.gate(op)?;
        if std::mem::take(&mut self.duplicate_next_write) {
            fault = Fault::Duplicate;
        }
        match fault {
            Fault::Crash(CrashPoint::Before) => Err(AdapterError::Other("crash before".into())),
            Fault::Crash(CrashPoint::After) => {
                apply(self)?;
                Err(AdapterError::Other("crash after".into()))
            }
            Fault::Duplicate => {
                apply(self)?;
                apply(self)
            }
            _ => apply(self),
        }
    }

    /// Gate a read; only a crash can fail it.
    fn read_gate(&self, op: &str) -> AdapterResult<()> {
        match self.gate(op)? {
            Fault::Crash(_) => Err(AdapterError::Other("crash".into())),
            _ => Ok(()),
        }
    }

    fn get_mut(&mut self, issue: &IssueRef) -> AdapterResult<&mut Issue> {
        let n = self.number(issue).ok_or(AdapterError::NotFound)?;
        Ok(self.issues.get_mut(&n).expect("checked"))
    }
}

impl FakeGithub {
    /// Count a read call through `&self`, then run it.
    fn counted<T>(&self, op: &str, f: impl FnOnce(&Self) -> AdapterResult<T>) -> AdapterResult<T> {
        self.read_gate(op)?;
        f(self)
    }
}

impl TrackerAdapter for FakeGithub {
    fn capabilities(&self) -> Capabilities {
        Capabilities {
            native_sub_issues: true,
            native_links: true,
            custom_fields: false,
            state_reasons: StateReasons::Native,
            history_retention: HistoryRetention::Forever,
            markdown: MarkdownDialect::Github,
        }
    }

    fn create(&mut self, projection: &IssueProjection, nonce: &str) -> CreateOutcome {
        let fault = match self.gate("create") {
            Ok(f) => f,
            Err(e) => return CreateOutcome::Failed(e.to_string()),
        };
        let fault = if std::mem::take(&mut self.lose_next_create) {
            Fault::Lose
        } else if let Some(t) = self.delay_next_create.take() {
            Fault::Delay(t)
        } else if std::mem::take(&mut self.duplicate_next_write) {
            Fault::Duplicate
        } else {
            fault
        };
        let (title, body) = (projection.title.clone(), render_body(projection));
        match fault {
            Fault::Lose | Fault::Crash(CrashPoint::Before) => CreateOutcome::Unknown,
            Fault::Delay(t) => {
                let due = self.now + t.max(1);
                debug!(due, "create delayed");
                self.pending.push(PendingCreate {
                    due,
                    creator_id: BOT_ID,
                    title,
                    body,
                    nonce: nonce.into(),
                });
                CreateOutcome::Unknown
            }
            Fault::Crash(CrashPoint::After) => {
                self.land_create(&title, &body, BOT_ID, nonce);
                CreateOutcome::Unknown
            }
            Fault::Duplicate => {
                let n = self.land_create(&title, &body, BOT_ID, nonce);
                self.land_create(&title, &body, BOT_ID, nonce);
                CreateOutcome::Created(IssueRef(n.to_string()))
            }
            Fault::None => {
                let n = self.land_create(&title, &body, BOT_ID, nonce);
                CreateOutcome::Created(IssueRef(n.to_string()))
            }
        }
    }

    fn update(&mut self, issue: &IssueRef, p: &IssueProjection) -> AdapterResult<()> {
        let (title, body) = (p.title.clone(), render_body(p));
        let issue = issue.clone();
        self.write("update", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            let i = s.get_mut(&issue)?;
            i.title.clone_from(&title);
            i.body.clone_from(&body);
            s.record(n, BOT_ID, "title", &title);
            s.record(n, BOT_ID, "body", &body);
            Ok(())
        })
    }

    fn close(&mut self, issue: &IssueRef, reason: Outcome) -> AdapterResult<()> {
        let issue = issue.clone();
        self.write("close", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            s.get_mut(&issue)?.closed = true;
            s.record(n, BOT_ID, "state", &format!("closed:{reason:?}"));
            Ok(())
        })
    }

    fn list_by_creator(&self, creator_id: u64) -> AdapterResult<Vec<IssueSummary>> {
        self.counted("list", |s| {
            let mut v: Vec<_> = s
                .issues
                .iter()
                .filter(|(_, i)| i.creator_id == creator_id)
                .collect();
            v.sort_by_key(|(_, i)| std::cmp::Reverse(i.seq));
            Ok(v.into_iter()
                .map(|(n, i)| IssueSummary {
                    issue: IssueRef(n.to_string()),
                    title: i.title.clone(),
                    creator_id: i.creator_id,
                    created_at: i.created_at.clone(),
                })
                .collect())
        })
    }

    fn read(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
        self.counted("read", |s| {
            let n = s.number(issue).ok_or(AdapterError::NotFound)?;
            Ok(Self::state_of(n, &s.issues[&n]))
        })
    }

    fn history_after(
        &self,
        issue: &IssueRef,
        after: Option<&EventId>,
    ) -> AdapterResult<Vec<HistoryEntry>> {
        self.counted("history", |s| {
            let n = s.number(issue).ok_or(AdapterError::NotFound)?;
            Ok(s.issues[&n]
                .history
                .iter()
                .filter(|e| after.is_none_or(|a| e.event > *a))
                .cloned()
                .collect())
        })
    }

    fn add_labels(&mut self, issue: &IssueRef, labels: &[String]) -> AdapterResult<()> {
        let (issue, labels) = (issue.clone(), labels.to_vec());
        self.write("add_labels", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            for l in &labels {
                s.get_mut(&issue)?.labels.insert(l.clone());
                s.record(n, BOT_ID, "labels", &format!("+{l}"));
            }
            Ok(())
        })
    }

    fn remove_labels(&mut self, issue: &IssueRef, labels: &[String]) -> AdapterResult<()> {
        let (issue, labels) = (issue.clone(), labels.to_vec());
        self.write("remove_labels", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            for l in &labels {
                s.get_mut(&issue)?.labels.remove(l);
                s.record(n, BOT_ID, "labels", &format!("-{l}"));
            }
            Ok(())
        })
    }

    fn add_assignees(&mut self, issue: &IssueRef, who: &[String]) -> AdapterResult<()> {
        let (issue, who) = (issue.clone(), who.to_vec());
        self.write("add_assignees", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            for w in &who {
                s.get_mut(&issue)?.assignees.insert(w.clone());
                s.record(n, BOT_ID, "assignees", &format!("+{w}"));
            }
            Ok(())
        })
    }

    fn remove_assignees(&mut self, issue: &IssueRef, who: &[String]) -> AdapterResult<()> {
        let (issue, who) = (issue.clone(), who.to_vec());
        self.write("remove_assignees", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            for w in &who {
                s.get_mut(&issue)?.assignees.remove(w);
                s.record(n, BOT_ID, "assignees", &format!("-{w}"));
            }
            Ok(())
        })
    }

    fn link(
        &mut self,
        issue: &IssueRef,
        kind: RelationKind,
        target: &IssueRef,
    ) -> AdapterResult<()> {
        let (issue, target) = (issue.clone(), target.clone());
        self.write("link", move |s| {
            let n = s.number(&issue).ok_or(AdapterError::NotFound)?;
            s.record(n, BOT_ID, "link", &format!("{kind:?}:{}", target.0));
            Ok(())
        })
    }

    fn inventory(&self) -> AdapterResult<Inventory> {
        self.counted("inventory", |_| Ok(Inventory::default()))
    }
}
